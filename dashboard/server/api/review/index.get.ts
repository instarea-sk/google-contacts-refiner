import type { ReviewChange, ReviewSession } from '../../utils/types'
import { getLatestReviewFile, getSessionForReviewFile } from '../../utils/gcs'
import { parseReviewFile } from '../../utils/review-helpers'
import { isDemoMode, maskReviewChange } from '../../utils/demo'

interface ReviewResponse {
  changes: ReviewChange[]
  session: ReviewSession | null
  reviewFilePath: string | null
  stats: {
    total: number
    byField: Record<string, number>
    byCategory: Record<string, number>
    confidenceRange: { min: number; max: number }
  }
}

export default defineEventHandler(async (event): Promise<ReviewResponse> => {
  const demo = await isDemoMode(event)
  const reviewFile = await getLatestReviewFile()
  if (!reviewFile) {
    return {
      changes: [],
      session: null,
      reviewFilePath: null,
      stats: { total: 0, byField: {}, byCategory: {}, confidenceRange: { min: 0, max: 0 } },
    }
  }

  const changes = parseReviewFile(reviewFile.data)

  // Build stats
  const byField: Record<string, number> = {}
  const byCategory: Record<string, number> = {}
  let min = 1
  let max = 0
  for (const c of changes) {
    const fieldBase = c.field.replace(/\[\d+\].*$/, '').replace(/\.\d+\..*$/, '')
    byField[fieldBase] = (byField[fieldBase] || 0) + 1
    byCategory[c.ruleCategory] = (byCategory[c.ruleCategory] || 0) + 1
    if (c.confidence < min) min = c.confidence
    if (c.confidence > max) max = c.confidence
  }

  // Find existing session that matches this specific review file
  const activeSession = await getSessionForReviewFile(reviewFile.path)

  return {
    changes: demo ? changes.map(maskReviewChange) : changes,
    session: demo ? null : activeSession, // Hide session data in demo
    reviewFilePath: reviewFile.path,
    stats: {
      total: changes.length,
      byField,
      byCategory,
      confidenceRange: { min, max },
    },
  }
})
