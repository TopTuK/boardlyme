<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBoardStore } from '../stores/board'
import { stageName } from '../lib/messages'

const props = defineProps({
  task: { type: Object, required: true },
})

const emit = defineEmits(['close'])
const { t } = useI18n()
const store = useBoardStore()

const destinations = computed(() =>
  store.visibleStages.filter((s) => s.id !== props.task.stage_id || s.is_split),
)

async function moveTo(stage, lane = false) {
  const alreadyThere = stage.id === props.task.stage_id && !!props.task.stage_done === lane
  if (alreadyThere) {
    emit('close')
    return
  }
  await store.moveTask(props.task.id, stage.id, 0, lane)
  emit('close')
}
</script>

<template>
  <div class="sheet-overlay" @click.self="emit('close')">
    <div class="sheet-panel max-w-lg" role="dialog" aria-modal="true" :aria-label="t('task.moveTitle')">
      <header class="flex items-center justify-between border-b-2 border-ink px-4 py-3">
        <div>
          <p class="font-mono text-[9px] uppercase tracking-widest text-steel">{{ t('task.moveTitle') }}</p>
          <p class="mt-0.5 truncate text-sm font-semibold">{{ task.title }}</p>
        </div>
        <button type="button" class="flex min-h-11 min-w-11 items-center justify-center text-steel hover:text-ink" :aria-label="t('common.close')" @click="emit('close')">
          <SvgIcon name="x" :size="14" />
        </button>
      </header>
      <ul>
        <li v-for="stage in destinations" :key="stage.id" class="border-b border-line last:border-b-0">
          <template v-if="stage.is_split">
            <button type="button" class="menu-item" @click="moveTo(stage, false)">
              {{ stageName(stage) }} · {{ t('stage.active') }}
            </button>
            <button type="button" class="menu-item border-t border-line" @click="moveTo(stage, true)">
              {{ stageName(stage) }} · {{ t('stage.done') }}
            </button>
          </template>
          <button v-else type="button" class="menu-item" @click="moveTo(stage, false)">
            {{ stageName(stage) }}
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
