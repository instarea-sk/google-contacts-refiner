import { getAllReviewSessions, getLatestExport } from '../../utils/gcs'

export default defineEventHandler(async () => {
  const [sessions, lastExport] = await Promise.all([
    getAllReviewSessions(),
    getLatestExport(),
  ])

  return {
    sessions: sessions.map(s => ({
      id: s.id,
      createdAt: s.createdAt,
      stats: s.stats,
    })),
    lastExport,
  }
})
