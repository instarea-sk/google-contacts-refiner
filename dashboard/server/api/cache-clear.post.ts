import { clearCache } from '../utils/gcs'
import { isDemoMode } from '../utils/demo'

export default defineEventHandler(async (event) => {
  if (await isDemoMode(event)) {
    throw createError({ statusCode: 403, message: 'Read-only demo mode' })
  }

  clearCache()
  return { cleared: true }
})
