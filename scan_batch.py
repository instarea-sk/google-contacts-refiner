#!/usr/bin/env python3
"""Helper script for batch LinkedIn scanning. Called by Claude Code browser automation."""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent / "data"
SIGNALS_FILE = DATA_DIR / "linkedin_signals.json"
CACHE_FILE = DATA_DIR / "linkedin_scan_cache.json"
TARGETS_FILE = DATA_DIR / "linkedin_scan_targets.json"


def load_signals():
    if SIGNALS_FILE.exists():
        return json.loads(SIGNALS_FILE.read_text(encoding="utf-8"))
    return {"generated": "", "count": 0, "signals": {}}


def load_targets():
    if TARGETS_FILE.exists():
        data = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
        return data.get("targets", [])
    return []


def get_pending_targets():
    """Get targets with URLs that haven't been scanned yet."""
    signals = load_signals()
    scanned = set(signals["signals"].keys())
    targets = load_targets()
    pending = [
        t for t in targets
        if t.get("linkedin_url")
        and t["resourceName"] not in scanned
        and "%C4%" not in t["linkedin_url"]
        and "%C5%" not in t["linkedin_url"]
        and "%C3%" not in t["linkedin_url"]
        and "/pub/" not in t["linkedin_url"]
    ]
    return pending


def record(resource_name, name, headline, company, location, activity_text, linkedin_url, known_org):
    """Record a scanned profile result."""
    signals = load_signals()
    cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}

    now = datetime.now(timezone.utc).isoformat()

    # Detect job change
    job_change = ""
    if known_org and company:
        # Normalize for comparison
        old = known_org.lower().strip().rstrip(".")
        new = company.lower().strip().rstrip(".")
        if old and new and old not in new and new not in old:
            job_change = f"{known_org} → {company}"

    # Classify signal
    if job_change:
        signal_type = "job_change"
        signal_text = job_change
    elif activity_text and "no recent posts" not in activity_text.lower().replace("_", " "):
        signal_type = "active"
        signal_text = activity_text
    elif headline:
        signal_type = "profile"
        signal_text = headline
    else:
        signal_type = "no_activity"
        signal_text = "No recent public activity"

    signal = {
        "resourceName": resource_name,
        "name": name,
        "linkedin_url": linkedin_url,
        "scanned_at": now,
        "headline": headline,
        "current_role": headline,
        "recent_activity": [],
        "signal_type": signal_type,
        "signal_text": signal_text,
    }

    signals["signals"][resource_name] = signal
    signals["generated"] = now
    signals["count"] = len(signals["signals"])

    cache[resource_name] = {"scanned_at": now, "signal_type": signal_type}

    SIGNALS_FILE.write_text(json.dumps(signals, ensure_ascii=False, indent=2), encoding="utf-8")
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    icon = {"job_change": "🟢", "active": "🟡", "profile": "⚪", "no_activity": "⬜"}.get(signal_type, "?")
    print(f"{icon} {name}: {signal_type} — {signal_text}")
    return signal


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pending"

    if cmd == "pending":
        pending = get_pending_targets()
        print(f"Pending: {len(pending)} targets with clean URLs")
        for i, t in enumerate(pending[:10], 1):
            print(f"  {i}. {t['name']:30s} {t['linkedin_url']}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")

    elif cmd == "record":
        # record <rn> <name> <headline> <company> <location> <activity> <url> <known_org>
        record(*sys.argv[2:10])

    elif cmd == "stats":
        signals = load_signals()
        total = len(signals["signals"])
        by_type = {}
        for s in signals["signals"].values():
            t = s.get("signal_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        print(f"Total signals: {total}")
        for t, c in sorted(by_type.items()):
            print(f"  {t}: {c}")

    elif cmd == "upload":
        from linkedin_scanner import _upload_signals_to_gcs
        _upload_signals_to_gcs()
