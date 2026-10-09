<script setup>
import { nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { stageName } from '../lib/messages'

const props = defineProps({
  stages: { type: Array, required: true },
  activeId: { type: String, default: null },
  counts: { type: Object, default: () => ({}) },
  canAdd: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'add'])
const { t } = useI18n()

watch(
  () => props.activeId,
  async (id) => {
    await nextTick()
    const el = document.getElementById(`station-tab-${id}`)
    el?.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' })
  },
)
</script>

<template>
  <div class="flex items-stretch border-b-2 border-ink bg-paper">
    <div class="flex min-w-0 flex-1 overflow-x-auto">
      <button
        v-for="stage in stages"
        :id="`station-tab-${stage.id}`"
        :key="stage.id"
        type="button"
        class="flex min-h-11 shrink-0 items-center gap-2 border-r border-ink px-3 font-mono text-[10px] uppercase tracking-widest"
        :class="stage.id === activeId ? 'bg-ink text-paper' : 'bg-paper text-steel hover:text-ink'"
        :aria-pressed="stage.id === activeId"
        @click="emit('select', stage.id)"
      >
        <span class="max-w-[9rem] truncate">{{ stageName(stage) }}</span>
        <span class="tabular-nums opacity-70">{{ String(counts[stage.id] ?? 0).padStart(2, '0') }}</span>
      </button>
    </div>
    <button
      v-if="canAdd"
      type="button"
      class="flex min-h-11 min-w-11 shrink-0 items-center justify-center border-l-2 border-ink bg-paper text-steel hover:text-ink"
      :title="t('board.addStage')"
      :aria-label="t('board.addStage')"
      @click="emit('add')"
    >
      <SvgIcon name="plus" :size="14" />
    </button>
  </div>
</template>
