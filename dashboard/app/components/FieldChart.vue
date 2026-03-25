<script setup lang="ts">
import type { FieldDrillDown } from '~/server/utils/types'

const props = defineProps<{
  data: Record<string, number>
  detail?: Record<string, FieldDrillDown>
}>()

const selectedField = ref<string | null>(null)

function toggle(label: string) {
  if (!props.detail?.[label]) return
  selectedField.value = selectedField.value === label ? null : label
}

const sorted = computed(() => {
  return Object.entries(props.data)
    .sort(([, a], [, b]) => b - a)
})

const max = computed(() => {
  const values = sorted.value.map(([, v]) => v)
  return Math.max(...values, 1)
})

const colors: Record<string, string> = {
  names: 'bg-primary-500',
  phones: 'bg-cyan-500',
  emails: 'bg-amber-500',
  addresses: 'bg-violet-500',
  organizations: 'bg-rose-500',
  urls: 'bg-blue-500',
  dates: 'bg-orange-500',
  other: 'bg-neutral-500',
}

const hoverColors: Record<string, string> = {
  names: 'bg-primary-500/20',
  phones: 'bg-cyan-500/20',
  emails: 'bg-amber-500/20',
  addresses: 'bg-violet-500/20',
  organizations: 'bg-rose-500/20',
  urls: 'bg-blue-500/20',
  dates: 'bg-orange-500/20',
  other: 'bg-neutral-500/20',
}
</script>

<template>
  <div class="space-y-1">
    <template v-for="[label, count] in sorted" :key="label">
      <div
        class="space-y-1 rounded-lg px-2 py-1.5 -mx-2 transition-colors"
        :class="[
          detail?.[label] ? 'cursor-pointer hover:bg-neutral-800/50' : '',
          selectedField === label ? 'bg-neutral-800/60' : '',
        ]"
        @click="toggle(label)"
      >
        <div class="flex items-center justify-between text-xs">
          <span class="text-neutral-400 capitalize">{{ label }}</span>
          <div class="flex items-center gap-2">
            <span class="text-neutral-500 tabular-nums">{{ count }}</span>
            <UIcon
              v-if="detail?.[label]"
              :name="selectedField === label ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
              class="size-3 text-neutral-600"
            />
          </div>
        </div>
        <div class="h-2 bg-neutral-800 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-700"
            :class="colors[label] || 'bg-neutral-500'"
            :style="{ width: `${(count / max) * 100}%` }"
          />
        </div>
      </div>

      <!-- Drill-down: reasons breakdown -->
      <div
        v-if="selectedField === label && detail?.[label]"
        class="ml-4 pl-3 border-l border-neutral-700/50 space-y-1.5 pb-2"
      >
        <div
          v-for="reason in detail[label].reasons"
          :key="reason.text"
          class="space-y-0.5"
        >
          <div class="flex justify-between text-[11px]">
            <span class="text-neutral-500 truncate mr-3">{{ reason.text }}</span>
            <span class="text-neutral-600 tabular-nums shrink-0">{{ reason.count }}</span>
          </div>
          <div class="h-1 bg-neutral-800/50 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="hoverColors[label] || 'bg-neutral-500/20'"
              :style="{ width: `${(reason.count / count) * 100}%` }"
            />
          </div>
        </div>
      </div>
    </template>
    <p v-if="sorted.length === 0" class="text-xs text-neutral-600 text-center py-4">
      No data
    </p>
  </div>
</template>
