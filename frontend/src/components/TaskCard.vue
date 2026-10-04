<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { deadlineState, displayName, fmtDeadline, initials } from '../lib/format'

const props = defineProps({
  task: { type: Object, required: true },
})

defineEmits(['open', 'complete'])

const { t } = useI18n()

const done = computed(() => !!props.task.completed_at)
const stageDone = computed(() => !!props.task.stage_done && !done.value)
const dlState = computed(() => deadlineState(props.task.deadline))
const assigneeInitials = computed(() => (props.task.assignee ? initials(props.task.assignee) : ''))
const assigneeTitle = computed(() => (props.task.assignee ? displayName(props.task.assignee) : ''))
</script>

<template>
  <article
    class="group cursor-grab border border-line bg-white px-2.5 py-2 transition-colors hover:border-ink active:cursor-grabbing"
    :class="done ? 'opacity-60' : ''"
    @click="$emit('open')"
  >
    <div class="flex items-start justify-between gap-2">
      <h3 class="text-[13px] font-semibold leading-snug" :class="done ? 'line-through decoration-1' : ''">
        {{ task.title }}
      </h3>
      <button
        v-if="!done"
        class="text-steel transition-opacity hover:text-signal"
        :class="dlState === 'overdue' || stageDone ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'"
        :title="t('task.completeTitle')"
        @click.stop="$emit('complete')"
      >
        <SvgIcon name="check" :size="13" />
      </button>
      <SvgIcon v-if="done" name="check" :size="13" class="text-signal" />
      <SvgIcon v-else-if="stageDone" name="check" :size="13" class="text-steel" />
    </div>

    <div class="mt-1.5 flex items-center gap-2">
      <span
        v-if="task.deadline"
        class="flex items-center gap-1 font-mono text-[10px] uppercase"
        :class="{
          'bg-[#C92A2A] px-1 text-white': dlState === 'overdue',
          'text-signal': dlState === 'today' || dlState === 'soon',
          'text-steel': dlState === 'later',
        }"
      >
        <SvgIcon name="calendar" :size="10" />
        {{ fmtDeadline(task.deadline) }}
      </span>
      <span v-if="task.description" class="text-steel" :title="t('task.hasDescription')">
        <SvgIcon name="lines" :size="11" />
      </span>
      <span
        v-if="task.assignee"
        class="ml-auto flex h-5 w-5 items-center justify-center bg-ink font-mono text-[9px] font-bold text-paper"
        :title="assigneeTitle"
      >
        {{ assigneeInitials }}
      </span>
    </div>
  </article>
</template>
