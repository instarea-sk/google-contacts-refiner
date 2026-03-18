<script setup lang="ts">
useHead({
  title: 'Pipeline Runs — Contact Refiner',
  meta: [
    { name: 'description', content: 'History of automated pipeline executions. View duration, phases completed, queue sizes, and errors for each daily run.' },
  ],
})

interface PipelineRun {
  date: string
  duration_seconds: number
  phases_completed: string[]
  queue_size: number
  errors: string[]
}

const { data, status, refresh } = useFetch<PipelineRun[]>('/api/pipeline-runs')

// Auto-refresh every 60s
const interval = setInterval(refresh, 60_000)
onUnmounted(() => clearInterval(interval))

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
            <th class="text-left px-4 py-3">Date</th>
            <th class="text-left px-4 py-3">Duration</th>
            <th class="text-left px-4 py-3">Phases</th>
            <th class="text-right px-4 py-3">Queue</th>
            <th class="text-left px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(run, i) in data"
            :key="i"
            class="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors"
          >
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
        </tbody>
      </table>
    </div>

    <p v-else class="text-sm text-neutral-600 text-center py-12">
      No pipeline runs recorded yet. Runs are tracked automatically after each daily pipeline execution.
    </p>
  </div>
</template>
