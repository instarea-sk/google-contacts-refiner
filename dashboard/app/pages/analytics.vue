<script setup lang="ts">
useHead({
  title: 'Analytics — Contact Refiner',
  meta: [
    { name: 'description', content: 'Contact cleanup analytics: changes by field type, confidence distribution, success rates, daily trends, and top modified contacts.' },
  ],
})

import type { AnalyticsResponse } from '~/server/utils/types'

const { data, status, refresh } = useFetch<AnalyticsResponse>('/api/analytics')

const isRefreshing = ref(false)
async function forceRefresh() {
  isRefreshing.value = true
  try {
    await $fetch('/api/cache-clear', { method: 'POST' })
    await refresh()
  } finally {
    isRefreshing.value = false
  }
}

// Compute max value for daily run bars to normalize widths
const maxDailyChanges = computed(() => {
  if (!data.value?.dailyRuns?.length) return 1
  return Math.max(...data.value.dailyRuns.map(r => r.changes + r.failed), 1)
})

function contactUrl(resourceName: string): string {
  return `https://contacts.google.com/person/${resourceName.replace('people/', '')}`
}

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-neutral-100">
        Analytics
      </h1>
      <UButton
        icon="i-lucide-refresh-cw"
        label="Refresh"
        size="xs"
        variant="ghost"
        color="neutral"
        :loading="isRefreshing"
        @click="forceRefresh"
      />
    </div>

    <!-- Loading -->
    <div v-if="status === 'pending'" class="text-center py-16">
      <UIcon name="i-lucide-loader" class="size-8 text-neutral-500 mx-auto mb-3 animate-spin" />
      <p class="text-neutral-500">Loading analytics...</p>
    </div>

    <!-- Error -->
    <div v-else-if="status === 'error'" class="text-center py-16">
      <UIcon name="i-lucide-alert-triangle" class="size-8 text-red-500 mx-auto mb-3" />
      <p class="text-red-400">Failed to load data</p>
      <UButton label="Retry" size="sm" variant="soft" class="mt-3" @click="refresh()" />
    </div>

    <!-- Top Stats -->
    <div v-if="status !== 'pending'" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatsCard
        label="Total Applied"
        :value="data?.totalChanges ?? 0"
        icon="i-lucide-check-circle"
        color="green"
      />
      <StatsCard
        label="Total Failed"
        :value="data?.totalFailed ?? 0"
        icon="i-lucide-x-circle"
        color="red"
      />
      <StatsCard
        label="Success Rate"
        :value="`${data?.successRate ?? 0}%`"
        icon="i-lucide-trending-up"
        color="cyan"
      />
      <StatsCard
        label="AI Cost"
        :value="(data?.estimatedCost ?? 0) > 0 ? `$${data?.estimatedCost}` : '--'"
        icon="i-lucide-dollar-sign"
        color="amber"
      />
    </div>

    <div v-if="status !== 'pending'" class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Changes by Field -->
      <div class="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
        <p class="text-xs uppercase tracking-wider text-neutral-500 mb-4">
          Changes by Field
        </p>
        <FieldChart :data="data?.byField ?? {}" :detail="data?.byFieldDetail" />
      </div>

      <!-- Confidence Distribution -->
      <div class="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
        <p class="text-xs uppercase tracking-wider text-neutral-500 mb-4">
          Confidence Distribution
        </p>
        <div class="space-y-4">
          <div v-for="(count, label) in data?.byConfidence" :key="label" class="space-y-1">
            <div class="flex justify-between text-xs">
              <span class="uppercase" :class="{
                'text-primary-400': label === 'high',
                'text-amber-400': label === 'medium',
                'text-red-400': label === 'low',
              }">
                {{ label }}
              </span>
              <span class="text-neutral-500 tabular-nums">{{ count }}</span>
            </div>
            <div class="h-2 bg-neutral-800 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-700"
                :class="{
                  'bg-primary-500': label === 'high',
                  'bg-amber-500': label === 'medium',
                  'bg-red-500': label === 'low',
                }"
                :style="{ width: `${(data?.byConfidence ? count / Math.max(data.byConfidence.high, data.byConfidence.medium, data.byConfidence.low, 1) * 100 : 0)}%` }"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Daily Runs Timeline -->
    <div v-if="status !== 'pending'" class="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
      <p class="text-xs uppercase tracking-wider text-neutral-500 mb-4">
        Daily Run History
      </p>
      <div v-if="data?.dailyRuns?.length" class="space-y-2">
        <div
          v-for="run in data.dailyRuns"
          :key="run.date"
          class="flex items-center gap-3 text-xs"
        >
          <span class="text-neutral-500 w-20 shrink-0 tabular-nums">{{ run.date }}</span>
          <div class="flex-1 flex gap-1 h-4 min-w-0 overflow-hidden">
            <div
              class="bg-primary-500/80 rounded-sm h-full"
              :style="{ width: `${(run.changes / maxDailyChanges) * 100}%`, minWidth: run.changes > 0 ? '2px' : '0' }"
              :title="`${run.changes} applied`"
            />
            <div
              v-if="run.failed > 0"
              class="bg-red-500/80 rounded-sm h-full"
              :style="{ width: `${(run.failed / maxDailyChanges) * 100}%`, minWidth: '2px' }"
              :title="`${run.failed} failed`"
            />
          </div>
          <span class="text-neutral-400 tabular-nums w-16 text-right shrink-0">{{ run.changes }} ok</span>
          <span class="text-red-400/60 tabular-nums w-16 text-right shrink-0">{{ run.failed }} fail</span>
        </div>
      </div>
      <p v-else class="text-xs text-neutral-600 text-center py-4">
        No run history
      </p>
    </div>

    <div v-if="status !== 'pending'" class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Top Changed Contacts -->
      <div class="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
        <p class="text-xs uppercase tracking-wider text-neutral-500 mb-4">
          Top Changed Contacts
        </p>
        <div v-if="data?.topContacts?.length" class="space-y-2">
          <div
            v-for="(contact, i) in data.topContacts"
            :key="contact.resourceName || contact.name"
            class="flex items-center gap-3 text-xs"
          >
            <span class="text-neutral-600 w-5 text-right tabular-nums shrink-0">{{ i + 1 }}.</span>
            <span class="text-neutral-300 flex-1 truncate">{{ contact.name }}</span>
            <span class="text-neutral-500 tabular-nums shrink-0">{{ contact.changes }}</span>
            <a
              v-if="contact.resourceName && contact.resourceName !== '***'"
              :href="contactUrl(contact.resourceName)"
              target="_blank"
              rel="noopener"
              class="text-neutral-600 hover:text-neutral-400 shrink-0"
              title="View in Google Contacts"
            >
              <UIcon name="i-lucide-external-link" class="size-3.5" />
            </a>
          </div>
        </div>
        <p v-else class="text-xs text-neutral-600 text-center py-4">
          No data
        </p>
      </div>

      <!-- Recently Changed Contacts -->
      <div class="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
        <p class="text-xs uppercase tracking-wider text-neutral-500 mb-4">
          Recently Changed Contacts
        </p>
        <div v-if="data?.recentlyChanged?.length" class="space-y-2">
          <div
            v-for="contact in data.recentlyChanged"
            :key="contact.resourceName || contact.name"
            class="flex items-center gap-3 text-xs"
          >
            <span class="text-neutral-300 flex-1 truncate">{{ contact.name }}</span>
            <span class="text-neutral-600 tabular-nums shrink-0">{{ formatDate(contact.lastChanged) }}</span>
            <span class="text-neutral-500 tabular-nums shrink-0">{{ contact.changes }} changes</span>
            <a
              v-if="contact.resourceName && contact.resourceName !== '***'"
              :href="contactUrl(contact.resourceName)"
              target="_blank"
              rel="noopener"
              class="text-neutral-600 hover:text-neutral-400 shrink-0"
              title="View in Google Contacts"
            >
              <UIcon name="i-lucide-external-link" class="size-3.5" />
            </a>
          </div>
        </div>
        <p v-else class="text-xs text-neutral-600 text-center py-4">
          No data
        </p>
      </div>
    </div>
  </div>
</template>
