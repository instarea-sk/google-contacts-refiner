import type { LinkedInSignalsResponse } from '../utils/types'
import { getLinkedInSignals } from '../utils/gcs'
import { isDemoMode, maskLinkedInSignal } from '../utils/demo'

export default defineEventHandler(async (event): Promise<LinkedInSignalsResponse> => {
  const demo = await isDemoMode(event)
  const { signals, generated } = await getLinkedInSignals()

  const jobChanges = signals.filter(s => s.signal_type === 'job_change').length
  const active = signals.filter(s => s.signal_type === 'active').length
  const profiles = signals.filter(s => s.signal_type === 'profile').length

  return {
    signals: demo ? signals.map(maskLinkedInSignal) : signals,
    stats: {
      total: signals.length,
      jobChanges,
      active,
      profiles,
      generated,
    },
  }
})
