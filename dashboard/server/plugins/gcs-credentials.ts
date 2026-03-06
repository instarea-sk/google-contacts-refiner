import { writeFileSync, existsSync } from 'node:fs'

const KEY_PATH = '/tmp/gcs-sa-key.json'

export default defineNitroPlugin(() => {
  // If GOOGLE_APPLICATION_CREDENTIALS is already set and file exists, skip
  if (process.env.GOOGLE_APPLICATION_CREDENTIALS && existsSync(process.env.GOOGLE_APPLICATION_CREDENTIALS)) {
    console.log('[GCS] Using existing GOOGLE_APPLICATION_CREDENTIALS:', process.env.GOOGLE_APPLICATION_CREDENTIALS)
    return
  }

  const config = useRuntimeConfig()
  const saKey = config.gcsServiceAccount as string

  if (!saKey) {
    console.warn('[GCS] No GCS_SERVICE_ACCOUNT env var set')
    return
  }

  try {
    // Validate it's parseable JSON
    const parsed = JSON.parse(saKey)
    // Write to temp file
    writeFileSync(KEY_PATH, JSON.stringify(parsed), { mode: 0o600 })
    process.env.GOOGLE_APPLICATION_CREDENTIALS = KEY_PATH
    console.log('[GCS] Wrote SA key to', KEY_PATH, '- project:', parsed.project_id)
  } catch (err) {
    console.error('[GCS] Failed to parse GCS_SERVICE_ACCOUNT:', (err as Error).message)
    // Try writing raw string in case it's already valid JSON but parse failed due to escaping
    try {
      writeFileSync(KEY_PATH, saKey, { mode: 0o600 })
      process.env.GOOGLE_APPLICATION_CREDENTIALS = KEY_PATH
      console.log('[GCS] Wrote raw SA key to', KEY_PATH)
    } catch (writeErr) {
      console.error('[GCS] Failed to write SA key file:', (writeErr as Error).message)
    }
  }
})
