import { isDemoMode } from '../../utils/demo'

export default defineEventHandler(async (event) => {
  if (await isDemoMode(event)) {
    throw createError({ statusCode: 403, message: 'Read-only demo mode' })
  }

  // Write a pause flag to GCS that the pipeline checks before running
  const { Storage } = await import('@google-cloud/storage')
  const config = useRuntimeConfig()
  const bucket = new Storage().bucket(String(config.gcsBucket))

  await bucket.file('data/pipeline_paused.json').save(
    JSON.stringify({
      paused: true,
      pausedAt: new Date().toISOString(),
      reason: 'Emergency stop from dashboard',
    }),
    { contentType: 'application/json', resumable: false },
  )

  return { paused: true }
})
