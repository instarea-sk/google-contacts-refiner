<script setup lang="ts">
useHead({
  title: 'Configuration — Contact Refiner',
  meta: [
    { name: 'description', content: 'Pipeline configuration: environment settings, batch size, confidence thresholds, AI model, and rule categories.' },
  ],
})

import type { ConfigResponse } from '~/server/utils/types'

const { data, status, refresh } = useFetch<ConfigResponse>('/api/config')

const rows = computed(() => {
  if (!data.value) return []
  return [
    { key: 'Environment', value: data.value.environment },
    { key: 'Batch Size', value: data.value.batchSize },
    { key: 'Confidence HIGH', value: `>= ${data.value.confidenceHigh}` },
    { key: 'Confidence MEDIUM', value: `>= ${data.value.confidenceMedium}` },
    { key: 'AI Model', value: data.value.aiModel },
    { key: 'AI Cost Limit', value: `$${data.value.aiCostLimit}/session` },
    { key: 'Auto Threshold', value: `>= ${data.value.autoThreshold}` },
    { key: 'Auto Max Changes', value: data.value.autoMaxChanges },
    { key: 'Scheduler', value: data.value.schedulerStatus },
  ]
})
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-xl font-bold text-neutral-100">
      Config
    </h1>

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
                :color="row.value === 'active' ? 'success' : 'warning'"
                variant="subtle"
                size="xs"
              />
              <span v-else>{{ row.value }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="status !== 'pending' && status !== 'error'" class="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <p class="text-xs uppercase tracking-wider text-neutral-500 mb-3">
        Pipeline Info
      </p>
      <div class="text-xs text-neutral-400 space-y-1">
        <p>Two-phase pipeline: Phase 1 (rule-based analyze + fix HIGH), Phase 2 (AI review MEDIUM + fix promoted)</p>
        <p>Cloud Run Job: europe-west1, 60min timeout, 512Mi, daily 9:00 Europe/Bratislava</p>
        <p>GCS bucket: contacts-refiner-data</p>
      </div>
    </div>
  </div>
</template>
