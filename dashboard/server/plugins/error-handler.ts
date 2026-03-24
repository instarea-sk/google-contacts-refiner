/**
 * Mask internal error details from API responses.
 * GCS errors, auth failures etc. should not leak to clients.
 */
export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('error', (error, { event }) => {
    if (!event) return

    const path = getRequestURL(event).pathname
    if (!path.startsWith('/api/')) return

    // Log the full error server-side
    console.error(`[API Error] ${event.method} ${path}:`, (error as Error).message)

    // Mask the error message for the client
    if (error && typeof error === 'object' && 'statusMessage' in error) {
      const statusCode = (error as { statusCode?: number }).statusCode || 500
      // Keep 4xx messages (client errors), mask 5xx (server errors)
      if (statusCode >= 500) {
        (error as { statusMessage: string }).statusMessage = 'Internal server error'
        if ('message' in error) {
          (error as { message: string }).message = 'Internal server error'
        }
        // Remove stack trace from response
        if ('stack' in error) {
          delete (error as Record<string, unknown>).stack
        }
      }
    }
  })
})
