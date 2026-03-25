<script setup lang="ts">
useHead({
  title: 'Pipeline Runs — Contact Refiner',
  meta: [
    { name: 'description', content: 'History of automated pipeline executions. View duration, phases completed, queue sizes, and errors for each daily run.' },
  ],
})

interface PhaseDetail {
  elapsed_s: number
  changes_applied?: number
  changes_failed?: number
  changes_skipped?: number
  promoted?: number
  demoted?: number
  ai_cost_usd?: number
  ai_tokens?: number
  backup_elapsed_s?: number
  analyze_elapsed_s?: number
  fix_elapsed_s?: number
  fix_changes_applied?: number
}

interface PipelineRun {
  date: string
  duration_seconds: number
  phases_completed: string[]
  queue_size: number
  errors: string[]
  changes_applied?: number
  changes_failed?: number
  phases?: Record<string, PhaseDetail>
}

const { data, status, refresh } = useFetch<PipelineRun[]>('/api/pipeline-runs')

// Auto-refresh every 60s (browser only)
let interval: ReturnType<typeof setInterval> | undefined
onMounted(() => { interval = setInterval(refresh, 60_000) })
onUnmounted(() => { if (interval) clearInterval(interval) })

const expandedRows = ref<Set<number>>(new Set())
function toggleRow(i: number) {
  const s = new Set(expandedRows.value)
  s.has(i) ? s.delete(i) : s.add(i)
  expandedRows.value = s
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })
    + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

const phaseLabels: Record<string, string> = {
  phase0: 'Review Feedback',
  phase1: 'Analyze + Auto-fix',
  phase2: 'AI Review',
  phase3: 'Activity Tagging',
  phase4: 'FollowUp Scoring',
}

function phaseStats(phase: string, detail: PhaseDetail): string {
  const parts: string[] = []
  if (detail.changes_applied !== undefined) parts.push(`${detail.changes_applied} applied`)
  if (detail.changes_failed) parts.push(`${detail.changes_failed} failed`)
  if (detail.changes_skipped) parts.push(`${detail.changes_skipped} skipped`)
  if (detail.promoted) parts.push(`${detail.promoted} promoted`)
  if (detail.demoted) parts.push(`${detail.demoted} demoted`)
  if (detail.ai_cost_usd) parts.push(`$${detail.ai_cost_usd.toFixed(3)}`)
  if (detail.fix_changes_applied) parts.push(`${detail.fix_changes_applied} fixes applied`)
  return parts.join(' · ') || '—'
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-xl font-bold text-neutral-100">
      Pipeline Runs
    </h1>

    <!-- Loading -->
    <div v-if="status === 'pending'" class="text-center py-16">
      <UIcon name="i-lucide-loader" class="size-8 text-neutral-500 mx-auto mb-3 animate-spin" />
      <p class="text-neutral-500">Loading pipeline runs...</p>
    </div>

    <!-- Error -->
    <div v-else-if="status === 'error'" class="text-center py-16">
      <UIcon name="i-lucide-alert-triangle" class="size-8 text-red-500 mx-auto mb-3" />
      <p class="text-red-400">Failed to load data</p>
      <UButton label="Retry" size="sm" variant="soft" class="mt-3" @click="refresh()" />
    </div>

    <div v-else-if="data?.length" class="rounded-xl border border-neutral-800 bg-neutral-900/50 overflow-hidden">
      <table class="w-full text-xs">
        <thead>
          <tr class="border-b border-neutral-800 text-neutral-500 uppercase tracking-wider">
            <th class="text-left px-4 py-3 w-6"></th>
            <th class="text-left px-4 py-3">Date</th>
            <th class="text-left px-4 py-3">Duration</th>
            <th class="text-left px-4 py-3">Phases</th>
            <th class="text-right px-4 py-3">Queue</th>
            <th class="text-left px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(run, i) in data" :key="i">
            <tr
              class="border-b border-neutral-800/50 transition-colors"
              :class="run.phases ? 'cursor-pointer hover:bg-neutral-800/30' : 'hover:bg-neutral-800/30'"
              @click="run.phases && toggleRow(i)"
            >
              <td class="px-4 py-2.5 text-neutral-600">
                <UIcon
                  v-if="run.phases"
                  :name="expandedRows.has(i) ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
                  class="size-3.5"
                />
              </td>
              <td class="px-4 py-2.5 text-neutral-300 tabular-nums font-mono">
                {{ formatDate(run.date) }}
              </td>
              <td class="px-4 py-2.5 text-neutral-400 tabular-nums">
                {{ formatDuration(run.duration_seconds) }}
              </td>
              <td class="px-4 py-2.5">
                <div class="flex gap-1">
                  <span
                    v-for="phase in run.phases_completed"
                    :key="phase"
                    class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary-500/15 text-primary-400"
                  >
                    {{ phase }}
                  </span>
                </div>
              </td>
              <td class="px-4 py-2.5 text-right text-neutral-400 tabular-nums">
                {{ run.queue_size }}
              </td>
              <td class="px-4 py-2.5">
                <span
                  v-if="run.errors.length === 0"
                  class="inline-flex items-center gap-1 text-green-400"
                >
                  <UIcon name="i-lucide-check-circle" class="size-3" />
                  OK
                </span>
                <span
                  v-else
                  class="inline-flex items-center gap-1 text-red-400 cursor-help"
                  :title="run.errors.join('\n')"
                >
                  <UIcon name="i-lucide-alert-circle" class="size-3" />
                  {{ run.errors.length }} error{{ run.errors.length > 1 ? 's' : '' }}
                </span>
              </td>
            </tr>

            <!-- Expanded phase details -->
            <tr v-if="expandedRows.has(i) && run.phases">
              <td colspan="6" class="px-4 pb-3 pt-0 bg-neutral-900/30">
                <div class="ml-6 border-l border-neutral-700/50 pl-4 py-2 space-y-2">
                  <div
                    v-for="phase in run.phases_completed"
                    :key="phase"
                    class="flex items-baseline gap-4 text-[11px]"
                  >
                    <span class="text-neutral-400 w-32 shrink-0">
                      {{ phaseLabels[phase] || phase }}
                    </span>
                    <span class="text-neutral-500 tabular-nums w-16 shrink-0">
                      {{ run.phases[phase] ? formatDuration(run.phases[phase].elapsed_s) : '—' }}
                    </span>
                    <span class="text-neutral-600">
                      {{ run.phases[phase] ? phaseStats(phase, run.phases[phase]) : 'No details' }}
                    </span>
                  </div>
                  <div v-if="run.changes_applied !== undefined" class="flex gap-4 pt-1 border-t border-neutral-800/50 text-[11px]">
                    <span class="text-neutral-500">Total: {{ run.changes_applied }} applied</span>
                    <span v-if="run.changes_failed" class="text-red-400/60">{{ run.changes_failed }} failed</span>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <p v-else class="text-sm text-neutral-600 text-center py-12">
      No pipeline runs recorded yet. Runs are tracked automatically after each daily pipeline execution.
    </p>
  </div>
</template>
