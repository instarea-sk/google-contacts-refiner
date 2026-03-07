<script setup lang="ts">
import type { ReviewChange, ReviewDecision } from '~/server/utils/types'

const props = defineProps<{
  group: { displayName: string; resourceName: string; changes: ReviewChange[] }
  focused: boolean
  decisions: Record<string, ReviewDecision>
}>()

const emit = defineEmits<{
  decide: [changeId: string, decision: ReviewDecision['decision'], editedValue?: string]
  decideAll: [resourceName: string, decision: 'approved' | 'rejected']
  undoDecision: [changeId: string]
  focus: []
}>()

const editingId = ref<string | null>(null)
const editValue = ref('')

function formatField(field: string): string {
  return field
    .replace('phoneNumbers', 'phones')
    .replace('emailAddresses', 'emails')
    .replace('.value', '')
    .replace('.givenName', '.given')
    .replace('.familyName', '.family')
    .replace('.formattedValue', '')
}

function decisionColor(decision?: string) {
  switch (decision) {
    case 'approved': return 'success'
    case 'rejected': return 'error'
    case 'edited': return 'warning'
    case 'skipped': return 'neutral'
    default: return undefined
  }
}

function startEdit(change: ReviewChange) {
  editingId.value = change.id
  editValue.value = change.new
  nextTick(() => {
    const el = document.getElementById(`edit-${change.id}`)
    el?.focus()
  })
}

function submitEdit(changeId: string) {
  emit('decide', changeId, 'edited', editValue.value)
  editingId.value = null
}
</script>

<template>
  <div
    class="rounded-xl border transition-colors"
    :class="focused
      ? 'border-primary-500/50 bg-neutral-900/80'
      : 'border-neutral-800 bg-neutral-900/30'"
    @click="emit('focus')"
  >
    <!-- Contact header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-800/50">
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium text-neutral-200">{{ group.displayName }}</span>
        <span class="text-[10px] text-neutral-600 font-mono">{{ group.resourceName.replace('people/', '') }}</span>
        <UBadge :label="`${group.changes.length} changes`" variant="subtle" size="xs" color="neutral" />
      </div>
      <div class="flex gap-1">
        <UButton size="xs" variant="ghost" color="success" label="All" icon="i-lucide-check" @click.stop="emit('decideAll', group.resourceName, 'approved')" />
        <UButton size="xs" variant="ghost" color="error" label="All" icon="i-lucide-x" @click.stop="emit('decideAll', group.resourceName, 'rejected')" />
      </div>
    </div>

    <!-- Changes -->
    <div class="divide-y divide-neutral-800/30">
      <div
        v-for="change in group.changes"
        :key="change.id"
        class="px-4 py-2.5 flex items-center gap-3"
        :class="{ 'opacity-40': decisions[change.id] }"
      >
        <!-- Field -->
        <span class="text-xs font-mono text-neutral-500 w-32 shrink-0 truncate">
          {{ formatField(change.field) }}
        </span>

        <!-- Diff -->
        <div class="flex-1 min-w-0">
          <DiffDisplay :old-value="change.old" :new-value="change.new" />
          <!-- Edit input -->
          <div v-if="editingId === change.id" class="mt-1.5 flex gap-2">
            <input
              :id="`edit-${change.id}`"
              v-model="editValue"
              class="flex-1 px-2 py-1 text-xs bg-neutral-800 border border-neutral-700 rounded text-neutral-200 focus:outline-none focus:border-primary-500"
              @keydown.enter="submitEdit(change.id)"
              @keydown.escape="editingId = null"
            />
            <UButton size="xs" color="primary" label="Save" @click="submitEdit(change.id)" />
            <UButton size="xs" variant="ghost" label="Cancel" @click="editingId = null" />
          </div>
        </div>

        <!-- Confidence -->
        <span class="text-[10px] text-neutral-600 tabular-nums w-10 text-right shrink-0">
          {{ (change.confidence * 100).toFixed(0) }}%
        </span>

        <!-- Rule category -->
        <span class="text-[10px] text-neutral-600 w-24 shrink-0 truncate" :title="change.reason">
          {{ change.ruleCategory }}
        </span>

        <!-- Decision badge or action buttons -->
        <div class="flex items-center gap-1 shrink-0 w-36 justify-end">
          <template v-if="decisions[change.id]">
            <UBadge
              :label="decisions[change.id].decision"
              :color="decisionColor(decisions[change.id].decision)"
              variant="subtle"
              size="xs"
            />
            <UButton
              size="xs"
              variant="ghost"
              icon="i-lucide-undo-2"
              color="neutral"
              @click.stop="emit('undoDecision', change.id)"
            />
          </template>
          <template v-else>
            <UButton size="xs" variant="ghost" color="success" icon="i-lucide-check" title="Approve (a)" @click.stop="emit('decide', change.id, 'approved')" />
            <UButton size="xs" variant="ghost" color="error" icon="i-lucide-x" title="Reject (r)" @click.stop="emit('decide', change.id, 'rejected')" />
            <UButton size="xs" variant="ghost" color="warning" icon="i-lucide-pencil" title="Edit (e)" @click.stop="startEdit(change)" />
            <UButton size="xs" variant="ghost" color="neutral" icon="i-lucide-skip-forward" title="Skip (s)" @click.stop="emit('decide', change.id, 'skipped')" />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
