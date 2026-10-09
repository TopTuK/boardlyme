<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import TaskCard from './TaskCard.vue'
import { stageName } from '../lib/messages'

const props = defineProps({
  stage: { type: Object, required: true },
  tasks: { type: Array, required: true },
  doneTasks: { type: Array, default: () => [] },
})

const emit = defineEmits(['open-task', 'complete', 'update-task', 'move-task', 'prev', 'next'])
const { t } = useI18n()

const WORK_ACCENTS = ['#3C5A73', '#E8590C', '#A67C42', '#5E4B8A', '#8C4A3A']
const accent = computed(() => {
  if (props.stage.is_backlog) return '#2C2C2A'
  if (props.stage.is_done) return '#3E6B52'
  const index = Math.max(0, props.stage.position - 1)
  return WORK_ACCENTS[index % WORK_ACCENTS.length]
})

const wipFull = computed(
  () => props.stage.wip_limit != null && props.tasks.length >= props.stage.wip_limit,
)

const SWIPE = 56
let startX = 0
let startY = 0
let tracking = false
let didSwipe = false

function onPointerDown(e) {
  if (e.pointerType === 'mouse' && e.button !== 0) return
  tracking = true
  didSwipe = false
  startX = e.clientX
  startY = e.clientY
}

function onPointerUp(e) {
  if (!tracking) return
  tracking = false
  const dx = e.clientX - startX
  const dy = e.clientY - startY
  if (Math.abs(dx) < SWIPE || Math.abs(dx) <= Math.abs(dy) * 1.2) return
  didSwipe = true
  if (dx < 0) emit('next')
  else emit('prev')
}

function onPointerCancel() {
  tracking = false
}

function onClickCapture(e) {
  if (!didSwipe) return
  e.preventDefault()
  e.stopPropagation()
  didSwipe = false
}
</script>

<template>
  <section
    class="stage flex min-h-0 flex-1 flex-col overflow-hidden"
    :style="{ '--stage': accent }"
    @pointerdown="onPointerDown"
    @pointerup="onPointerUp"
    @pointercancel="onPointerCancel"
    @click.capture="onClickCapture"
  >
    <div class="h-[3px] shrink-0 bg-[var(--stage)]" />
    <header class="stage-head flex items-center justify-between gap-2 border-b border-line px-3 py-2">
      <h2 class="flex min-w-0 items-center gap-2 text-sm font-semibold tracking-tight">
        <SvgIcon v-if="stage.is_done" name="check" :size="13" class="text-[var(--stage)]" />
        <span v-else class="h-1.5 w-1.5 shrink-0 bg-[var(--stage)]" />
        <span class="truncate">{{ stageName(stage) }}</span>
      </h2>
      <span
        class="shrink-0 font-mono text-[11px] font-medium tabular-nums"
        :class="wipFull ? 'text-[#C92A2A]' : 'text-[var(--stage)]'"
      >
        {{ stage.wip_limit != null ? `${tasks.length}/${stage.wip_limit}` : String(tasks.length + doneTasks.length).padStart(2, '0') }}
      </span>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain p-3">
      <template v-if="stage.is_split">
        <div class="mb-2 flex items-center justify-between">
          <span class="font-sans text-[11px] font-semibold tracking-tight text-[var(--stage)]">{{ t('stage.active') }}</span>
        </div>
        <p v-if="!tasks.length" class="mb-4 text-center text-[13px] text-steel">{{ t('stage.empty') }}</p>
        <div v-else class="space-y-2">
          <TaskCard
            v-for="task in tasks"
            :key="task.id"
            :task="task"
            compact
            @open="emit('open-task', task)"
            @complete="emit('complete', task)"
            @update="(patch) => emit('update-task', task, patch)"
            @move="emit('move-task', task)"
          />
        </div>

        <div class="mb-2 mt-5 flex items-center justify-between border-t border-line pt-3">
          <span class="flex items-center gap-1.5 font-sans text-[11px] font-semibold tracking-tight text-[#3E6B52]">
            <SvgIcon name="check" :size="11" /> {{ t('stage.done') }}
          </span>
          <span class="font-mono text-[10px] font-medium tabular-nums text-[#3E6B52]">{{ String(doneTasks.length).padStart(2, '0') }}</span>
        </div>
        <p v-if="!doneTasks.length" class="text-center text-[13px] text-steel">{{ t('stage.empty') }}</p>
        <div v-else class="space-y-2">
          <TaskCard
            v-for="task in doneTasks"
            :key="task.id"
            :task="task"
            compact
            @open="emit('open-task', task)"
            @complete="emit('complete', task)"
            @update="(patch) => emit('update-task', task, patch)"
            @move="emit('move-task', task)"
          />
        </div>
      </template>

      <template v-else>
        <p v-if="!tasks.length" class="pt-8 text-center text-[13px] text-steel">{{ t('stage.empty') }}</p>
        <div v-else class="space-y-2">
          <TaskCard
            v-for="task in tasks"
            :key="task.id"
            :task="task"
            compact
            @open="emit('open-task', task)"
            @complete="emit('complete', task)"
            @update="(patch) => emit('update-task', task, patch)"
            @move="emit('move-task', task)"
          />
        </div>
      </template>
    </div>
  </section>
</template>
