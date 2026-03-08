"""
Contact Activity Tagging — scan Gmail and Calendar to determine last interaction per contact.

Scans both personal and work accounts, caches results, and assigns year-based labels
(Y2025, Y2024, ..., "Never in touch") to contacts via People API contact groups.
"""
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from api_client import PeopleAPIClient, RateLimiter
from config import (
    ACTIVITY_ACCOUNTS,
    ACTIVITY_LABEL_PREFIX,
    CALENDAR_EVENTS_SINCE,
    GMAIL_RATE_LIMIT,
    INTERACTIONS_CACHE,
    NEVER_IN_TOUCH_LABEL,
    RESCAN_INTERVAL_DAYS,
)

logger = logging.getLogger("contacts-refiner.activity")


class InteractionScanner:
    """
    Scans Gmail and Calendar to find the most recent interaction date per contact.

    Workflow:
    1. Build email→resourceName index from contacts
    2. Scan Gmail (per unique email: query from/to, get latest date)
    3. Scan Calendar (fetch all events, build attendee index)
    4. Merge results: last_interaction = max(last_email, last_meeting)
    5. Assign year-based labels via People API
    """

    def __init__(self, contacts: list[dict]):
        """
        Args:
            contacts: List of People API person resources.
        """
        self.contacts = contacts
        self._email_to_contacts: dict[str, set[str]] = defaultdict(set)
        self._contact_emails: dict[str, set[str]] = {}
        self._interactions: dict[str, str] = {}  # email → ISO date string
        self._gmail_limiter = RateLimiter(GMAIL_RATE_LIMIT)
        self._cache_loaded = False

        self._build_email_index()
        self._load_cache()

    def _build_email_index(self):
        """Build mapping of email addresses to contact resourceNames."""
        for contact in self.contacts:
            rn = contact.get("resourceName", "")
            if not rn:
                continue

            emails = set()
            for email_entry in contact.get("emailAddresses", []):
                email = email_entry.get("value", "").strip().lower()
                if email:
                    emails.add(email)
                    self._email_to_contacts[email].add(rn)

            if emails:
                self._contact_emails[rn] = emails

        total_emails = len(self._email_to_contacts)
        total_contacts_with_email = len(self._contact_emails)
        logger.info(
            f"Email index: {total_emails} unique emails "
            f"from {total_contacts_with_email} contacts"
        )

    def _load_cache(self):
        """Load cached interaction data from disk."""
        if INTERACTIONS_CACHE.exists():
            try:
                data = json.loads(INTERACTIONS_CACHE.read_text(encoding="utf-8"))
                self._interactions = data.get("interactions", {})
                self._cache_loaded = True
                logger.info(f"Cache loaded: {len(self._interactions)} email interactions")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load cache: {e}")
                self._interactions = {}

    def save_cache(self):
        """Persist interaction data to disk."""
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "interactions": self._interactions,
        }
        INTERACTIONS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        INTERACTIONS_CACHE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"Cache saved: {len(self._interactions)} interactions")

    def _should_rescan(self, email: str) -> bool:
        """Check if an email needs rescanning based on cache age."""
        if email not in self._interactions:
            return True

        # Check cache metadata for scan timestamp
        # For simplicity, we always rescan if cache is older than RESCAN_INTERVAL_DAYS
        # The cache file's mtime serves as the global freshness indicator
        if not INTERACTIONS_CACHE.exists():
            return True

        mtime = datetime.fromtimestamp(INTERACTIONS_CACHE.stat().st_mtime, tz=timezone.utc)
        age = datetime.now(timezone.utc) - mtime
        return age > timedelta(days=RESCAN_INTERVAL_DAYS)

    # ── Gmail Scanning ──────────────────────────────────────────────────

    def scan_gmail(self, credentials: Credentials, account_email: str):
        """
        Scan Gmail for the latest email interaction per contact email address.

        For each unique email in the contact index:
        - Query: "from:{email}" and "to:{email}" to find sent/received messages
        - Get the latest message date
        - Cache the result

        Args:
            credentials: OAuth2 credentials with gmail.readonly scope.
            account_email: The Gmail account being scanned (for logging).
        """
        service = build("gmail", "v1", credentials=credentials)

        emails_to_scan = [
            email for email in self._email_to_contacts
            if self._should_rescan(email)
        ]

        if not emails_to_scan:
            logger.info(f"Gmail ({account_email}): All emails cached, nothing to scan")
            return

        logger.info(
            f"Gmail ({account_email}): Scanning {len(emails_to_scan)} emails "
            f"(skipping {len(self._email_to_contacts) - len(emails_to_scan)} cached)"
        )

        scanned = 0
        found = 0
        errors = 0

        for i, email in enumerate(emails_to_scan):
            try:
                latest_date = self._get_latest_gmail_date(service, email)
                if latest_date:
                    # Keep the most recent date across accounts
                    existing = self._interactions.get(email)
                    if not existing or latest_date > existing:
                        self._interactions[email] = latest_date
                    found += 1
                scanned += 1

            except Exception as e:
                logger.debug(f"Gmail error for {email}: {e}")
                errors += 1
                scanned += 1

            # Progress + incremental save every 200 emails
            if (i + 1) % 200 == 0:
                logger.info(
                    f"Gmail ({account_email}): {i + 1}/{len(emails_to_scan)} "
                    f"({found} found, {errors} errors)"
                )
                self.save_cache()

        self.save_cache()
        logger.info(
            f"Gmail ({account_email}): Done — {scanned} scanned, "
            f"{found} with interactions, {errors} errors"
        )

    def _get_latest_gmail_date(self, service, email: str) -> Optional[str]:
        """
        Get the date of the most recent email to/from a given address.

        Returns ISO date string (YYYY-MM-DD) or None.
        """
        # Search for messages involving this email address
        query = f"from:{email} OR to:{email}"

        self._gmail_limiter.wait()
        result = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=1,
        ).execute()

        messages = result.get("messages", [])
        if not messages:
            return None

        # Get the message details for the date
        msg_id = messages[0]["id"]
        self._gmail_limiter.wait()
        msg = service.users().messages().get(
            userId="me",
            id=msg_id,
            format="minimal",
        ).execute()

        # internalDate is milliseconds since epoch
        internal_date = msg.get("internalDate")
        if not internal_date:
            return None

        dt = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")

    # ── Calendar Scanning ───────────────────────────────────────────────

    def scan_calendar(self, credentials: Credentials, account_email: str):
        """
        Scan Google Calendar to find latest meeting per attendee email.

        Fetches all events since CALENDAR_EVENTS_SINCE and builds an
        attendee→latest_event_date index.

        Args:
            credentials: OAuth2 credentials with calendar.readonly scope.
            account_email: The calendar account being scanned (for logging).
        """
        service = build("calendar", "v3", credentials=credentials)

        logger.info(f"Calendar ({account_email}): Fetching events since {CALENDAR_EVENTS_SINCE}")

        events_processed = 0
        attendees_found = 0
        page_token = None

        while True:
            kwargs = {
                "calendarId": "primary",
                "timeMin": CALENDAR_EVENTS_SINCE,
                "maxResults": 2500,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if page_token:
                kwargs["pageToken"] = page_token

            try:
                result = service.events().list(**kwargs).execute()
            except Exception as e:
                logger.error(f"Calendar ({account_email}): API error: {e}")
                break

            events = result.get("items", [])

            for event in events:
                event_date = self._get_event_date(event)
                if not event_date:
                    continue

                attendees = event.get("attendees", [])
                for attendee in attendees:
                    email = attendee.get("email", "").strip().lower()
                    if not email or email == account_email.lower():
                        continue

                    # Only track emails we have in contacts
                    if email in self._email_to_contacts:
                        existing = self._interactions.get(email)
                        if not existing or event_date > existing:
                            self._interactions[email] = event_date
                            attendees_found += 1

                events_processed += 1

            page_token = result.get("nextPageToken")
            if not page_token:
                break

            logger.info(
                f"Calendar ({account_email}): {events_processed} events processed..."
            )

        self.save_cache()
        logger.info(
            f"Calendar ({account_email}): Done — {events_processed} events, "
            f"{attendees_found} attendee interactions updated"
        )

    def _get_event_date(self, event: dict) -> Optional[str]:
        """Extract date from a calendar event."""
        start = event.get("start", {})
        # dateTime for timed events, date for all-day events
        date_str = start.get("dateTime") or start.get("date")
        if not date_str:
            return None

        # Parse various formats
        try:
            if "T" in date_str:
                # dateTime format: 2025-03-01T10:00:00+01:00
                dt = datetime.fromisoformat(date_str)
                return dt.strftime("%Y-%m-%d")
            else:
                # date format: 2025-03-01
                return date_str
        except (ValueError, TypeError):
            return None

    # ── Contact Activity Resolution ─────────────────────────────────────

    def get_contact_activity(self) -> dict[str, Optional[str]]:
        """
        Resolve the latest interaction date for each contact.

        Returns:
            Dict mapping resourceName → latest interaction date (YYYY-MM-DD)
            or None if no interaction found.
        """
        result: dict[str, Optional[str]] = {}

        for rn, emails in self._contact_emails.items():
            latest = None
            for email in emails:
                date = self._interactions.get(email)
                if date and (not latest or date > latest):
                    latest = date
            result[rn] = latest

        # Contacts without email addresses → None
        for contact in self.contacts:
            rn = contact.get("resourceName", "")
            if rn and rn not in result:
                result[rn] = None

        return result

    # ── Year-Label Assignment ────────────────────────────────────────────

    def assign_labels(
        self,
        client: PeopleAPIClient,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """
        Assign year-based labels to contacts based on interaction data.

        Labels: Y2025, Y2024, Y2023, ..., "Never in touch"
        Additive only — never removes contacts from groups.

        Args:
            client: PeopleAPIClient for People API calls.
            dry_run: If True, compute assignments but don't apply.

        Returns:
            Dict mapping label name → count of contacts assigned.
        """
        activity = self.get_contact_activity()

        # Group contacts by target label
        label_assignments: dict[str, list[str]] = defaultdict(list)

        current_year = str(datetime.now(timezone.utc).year)

        for rn, last_date in activity.items():
            if last_date:
                year = last_date[:4]  # "2025" from "2025-03-01"
                if year > current_year:
                    year = current_year  # Cap future dates (recurring events)
                label = f"{ACTIVITY_LABEL_PREFIX}{year}"
            else:
                label = NEVER_IN_TOUCH_LABEL
            label_assignments[label].append(rn)

        # Log summary
        logger.info("Activity label assignments:")
        for label in sorted(label_assignments.keys()):
            count = len(label_assignments[label])
            logger.info(f"  {label}: {count} contacts")

        if dry_run:
            logger.info("DRY RUN — no labels applied")
            return {k: len(v) for k, v in label_assignments.items()}

        # Get existing groups
        existing_groups = client.get_all_contact_groups()
        group_map: dict[str, str] = {}  # name → resourceName
        for g in existing_groups:
            name = g.get("name", "")
            grn = g.get("resourceName", "")
            if name and grn:
                group_map[name] = grn

        # Get existing members for each group to avoid duplicates
        existing_members: dict[str, set[str]] = {}

        # Create missing groups and assign contacts
        stats: dict[str, int] = {}

        for label, contact_rns in label_assignments.items():
            # Ensure group exists
            if label not in group_map:
                logger.info(f"Creating group: {label}")
                try:
                    group = client.create_contact_group(label)
                    group_map[label] = group["resourceName"]
                except Exception as e:
                    logger.error(f"Failed to create group '{label}': {e}")
                    continue

            group_rn = group_map[label]

            # Get existing members to avoid re-adding
            if group_rn not in existing_members:
                try:
                    members = client.get_contact_group_members(group_rn)
                    existing_members[group_rn] = set(members)
                except Exception as e:
                    logger.warning(f"Failed to get members for {label}: {e}")
                    existing_members[group_rn] = set()

            # Filter out contacts already in the group
            new_contacts = [
                rn for rn in contact_rns
                if rn not in existing_members[group_rn]
            ]

            if not new_contacts:
                logger.info(f"{label}: All {len(contact_rns)} contacts already in group")
                stats[label] = 0
                continue

            # Add in batches of 500 (1000 can cause 409 aborted)
            added = 0
            for batch_start in range(0, len(new_contacts), 500):
                batch = new_contacts[batch_start:batch_start + 500]
                try:
                    client.add_contact_to_group(group_rn, batch)
                    added += len(batch)
                except Exception as e:
                    logger.error(f"Failed to add {len(batch)} contacts to {label}: {e}")

            stats[label] = added
            logger.info(f"{label}: Added {added} contacts (skipped {len(contact_rns) - len(new_contacts)} existing)")

        return stats

    # ── Full Scan Pipeline ──────────────────────────────────────────────

    def run_full_scan(
        self,
        account_credentials: list[tuple[str, Credentials]],
        client: PeopleAPIClient,
        skip_scan: bool = False,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """
        Run the complete activity tagging pipeline.

        Args:
            account_credentials: List of (email, credentials) tuples.
            client: PeopleAPIClient for label operations.
            skip_scan: Skip Gmail/Calendar scan, use cached data only.
            dry_run: Compute assignments but don't apply labels.

        Returns:
            Dict mapping label name → count of contacts assigned.
        """
        if not skip_scan:
            for account_email, creds in account_credentials:
                logger.info(f"Scanning {account_email}...")
                self.scan_gmail(creds, account_email)
                self.scan_calendar(creds, account_email)

        # Resolve and assign
        return self.assign_labels(client, dry_run=dry_run)
