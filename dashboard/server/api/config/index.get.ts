import type { ConfigResponse } from '../../utils/types'
import { isDemoMode } from '../../utils/demo'
import { getPipelineConfig } from '../../utils/gcs'

export default defineEventHandler(async (event): Promise<ConfigResponse> => {
  const demo = await isDemoMode(event)
  const gcsConfig = await getPipelineConfig()

  return {
    batchSize: gcsConfig?.batchSize ?? 50,
    confidenceHigh: gcsConfig?.confidenceHigh ?? 0.90,
    confidenceMedium: gcsConfig?.confidenceMedium ?? 0.60,
    aiModel: demo ? 'claude-haiku' : 'claude-haiku-4-5-20251001',
    aiCostLimit: gcsConfig?.aiCostLimit ?? 3.00,
    autoMaxChanges: gcsConfig?.autoMaxChanges ?? 200,
    autoThreshold: gcsConfig?.autoThreshold ?? 0.90,
    environment: 'cloud',
    schedulerStatus: 'enabled',
  }
})
