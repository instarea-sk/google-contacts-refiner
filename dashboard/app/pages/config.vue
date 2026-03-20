<script setup lang="ts">
useHead({
  title: 'Configuration — Contact Refiner',
  meta: [
    { name: 'description', content: 'Pipeline configuration: environment settings, batch size, confidence thresholds, AI model, and rule categories.' },
  ],
})

import type { ConfigResponse } from '~/server/utils/types'

const { loggedIn } = useUserSession()
const isDemo = computed(() => !loggedIn.value)

const { data, status, refresh } = useFetch<ConfigResponse>('/api/config')

const isPausing = ref(false)
const pauseStatus = ref<'idle' | 'paused' | 'error'>('idle')

async function emergencyPause() {
  if (isDemo.value) return
  isPausing.value = true
  try {
    await $fetch('/api/config/pause', { method: 'POST' })
    pauseStatus.value = 'paused'
    await refresh()
  } catch {
    pauseStatus.value = 'error'
  } finally {
    isPausing.value = false
  }
}

const rows = computed(() => {
  if (!data.value) return []
  return [
    {
      key: 'Environment',
      value: data.value.environment,
      desc: 'Where the pipeline runs: "cloud" (Cloud Run Job) or "local" (Mac)',
    },
    {
      key: 'Batch Size',
      value: data.value.batchSize,
      desc: 'Number of contacts processed per batch in each pipeline run',
    },
    {
      key: 'Confidence HIGH',
      value: `>= ${data.value.confidenceHigh}`,
      desc: 'Changes at or above this threshold are auto-applied without review',
    },
    {
      key: 'Confidence MEDIUM',
      value: `>= ${data.value.confidenceMedium}`,
      desc: 'Changes in this range go to AI review, then to the review queue',
    },
    {
      key: 'AI Model',
      value: data.value.aiModel,
      desc: 'Claude model used for AI review of MEDIUM confidence changes',
    },
    {
      key: 'AI Cost Limit',
      value: `$${data.value.aiCostLimit}/session`,
      desc: 'Maximum Claude API spend per pipeline run (safety cap)',
    },
    {
      key: 'Auto Threshold',
      value: `>= ${data.value.autoThreshold}`,
      desc: 'Minimum confidence for auto-fix without human review',
    },
    {
      key: 'Auto Max Changes',
      value: data.value.autoMaxChanges,
      desc: 'Maximum changes auto-applied per run (prevents runaway fixes)',
    },
    {
      key: 'Scheduler',
      value: data.value.schedulerStatus,
      desc: 'Cloud Scheduler status — daily 9:00 Europe/Bratislava',
    },
  ]
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-neutral-100">
        Config
      </h1>
      <UButton
        v-if="!isDemo"
        icon="i-lucide-octagon"
        label="Emergency Stop"
        size="sm"
        variant="soft"
        color="error"
        :loading="isPausing"
        @click="emergencyPause"
      />
    </div>

    <!-- Emergency Stop Feedback -->
    <div v-if="pauseStatus === 'paused'" class="rounded-lg border border-red-800 bg-red-900/30 px-4 py-3 text-sm text-red-300">
      Pipeline paused. The scheduler has been disabled and no new runs will start.
      To resume, re-enable the Cloud Scheduler in GCP Console.
    </div>
    <div v-if="pauseStatus === 'error'" class="rounded-lg border border-amber-800 bg-amber-900/30 px-4 py-3 text-sm text-amber-300">
      Failed to pause pipeline. Check the server logs or disable the scheduler manually in GCP Console.
    </div>

    <!-- Loading -->
    <div v-if="status === 'pending'" class="text-center py-16">
      <UIcon name="i-lucide-loader" class="size-8 text-neutral-500 mx-auto mb-3 animate-spin" />
      <p class="text-neutral-500">Loading config...</p>
    </div>

    <!-- Error -->
    <div v-else-if="status === 'error'" class="text-center py-16">
      <UIcon name="i-lucide-alert-triangle" class="size-8 text-red-500 mx-auto mb-3" />
      <p class="text-red-400">Failed to load data</p>
      <UButton label="Retry" size="sm" variant="soft" class="mt-3" @click="refresh()" />
    </div>

    <div v-if="status !== 'pending' && status !== 'error'" class="rounded-xl border border-neutral-800 bg-neutral-900/50 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-neutral-900/80">
          <tr class="text-left text-neutral-500 uppercase tracking-wider text-xs">
            <th class="px-5 py-3 font-medium">Parameter</th>
            <th class="px-5 py-3 font-medium">Value</th>
            <th class="px-5 py-3 font-medium">Description</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-800/50">
          <tr
            v-for="row in rows"
            :key="row.key"
            class="hover:bg-neutral-800/30 transition-colors"
          >
            <td class="px-5 py-3 text-neutral-400">{{ row.key }}</td>
            <td class="px-5 py-3 text-neutral-200 font-mono">
              <UBadge
                v-if="row.key === 'Scheduler'"
                :label="String(row.value).toUpperCase()"
                :color="row.value === 'active' || row.value === 'enabled' ? 'success' : 'warning'"
                variant="subtle"
                size="xs"
              />
              <span v-else>{{ row.value }}</span>
            </td>
            <td class="px-5 py-3 text-xs text-neutral-600">{{ row.desc }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="status !== 'pending' && status !== 'error'" class="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <p class="text-xs uppercase tracking-wider text-neutral-500 mb-3">
        Pipeline Info
      </p>
      <div class="text-xs text-neutral-400 space-y-2">
        <div>
          <span class="text-neutral-500 font-medium">Phase 0 — Review Feedback:</span>
          Process user review decisions, learn from feedback, apply approved changes to Google Contacts
        </div>
        <div>
          <span class="text-neutral-500 font-medium">Phase 1 — Analyze + Auto-fix:</span>
          Backup contacts, run 26 normalization rules (diacritics, phones, addresses, URLs, etc.), auto-apply HIGH confidence changes
        </div>
        <div>
          <span class="text-neutral-500 font-medium">Phase 2 — AI Review:</span>
          Send MEDIUM confidence changes to Claude Haiku for review, promote/demote based on AI assessment, apply promoted changes
        </div>
        <div>
          <span class="text-neutral-500 font-medium">Phase 3 — Post-run:</span>
          Send email digest via Resend (includes LinkedIn signal stats), record run to pipeline_runs.json, upload queue stats
        </div>
        <div class="pt-2 border-t border-neutral-800 text-neutral-500">
          <p>Cloud Run Job: europe-west1, 60min timeout, 512Mi, daily 9:00 Europe/Bratislava</p>
          <p>GCS bucket: contacts-refiner-data</p>
          <p>26 normalization rules across 8 field types, memory-based confidence learning</p>
        </div>
      </div>
    </div>
  </div>
</template>
