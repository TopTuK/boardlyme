<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { deadlineState, displayName, fmtDeadline } from '../lib/format'
import MemberAvatar from './MemberAvatar.vue'
import { COMPLEXITY_LEVELS, DEFAULT_COMPLEXITY, complexityLabel } from '../lib/complexity'

const props = defineProps({
  task: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['open', 'complete', 'update', 'move'])

const { t } = useI18n()

const draft = reactive({
  title: props.task.title,
  description: props.task.description || '',
})
const focused = ref(false)
const titleEl = ref(null)
const descEl = ref(null)

const done = computed(() => !!props.task.completed_at)
const stageDone = computed(() => !!props.task.stage_done && !done.value)
const dlState = computed(() => deadlineState(props.task.deadline))
const assigneeTitle = computed(() => (props.task.assignee ? displayName(props.task.assignee) : ''))
const checklist = computed(() => props.task.checklist || [])
const checklistDone = computed(() => checklist.value.filter((i) => i.is_done).length)
const checklistAllDone = computed(
  () => checklist.value.length > 0 && checklistDone.value === checklist.value.length
)
// "Normal" is the default — only call out tasks that deviate from it.
const complexity = computed(() =>
  props.task.complexity && props.task.complexity !== DEFAULT_COMPLEXITY ? props.task.complexity : ''
)
const complexityHeavy = computed(
  () => COMPLEXITY_LEVELS.indexOf(complexity.value) > COMPLEXITY_LEVELS.indexOf('difficult')
)
const hasMeta = computed(
  () => !!(props.task.deadline || props.task.assignee || checklist.value.length || complexity.value)
)

watch(
  () => [props.task.title, props.task.description],
  () => {
    if (focused.value) return
    draft.title = props.task.title
    draft.description = props.task.description || ''
    nextTick(fitDesc)
  },
)

function fitDesc() {
  const el = descEl.value
  if (!el) return
  el.style.height = '0px'
  el.style.height = `${Math.min(el.scrollHeight, 88)}px`
}

onMounted(() => nextTick(fitDesc))

function onFocusIn() {
  focused.value = true
  nextTick(fitDesc)
}

function onFocusOut(e) {
  const next = e.relatedTarget
  if (next && e.currentTarget.contains(next)) return
  focused.value = false
  // Blur can run before Vue has flushed the field value. Save on the next turn,
  // and skip if focus is still inside this card.
  const card = e.currentTarget
  setTimeout(() => {
    if (card.contains(document.activeElement)) return
    commit()
  }, 0)
}

function commit() {
  const title = draft.title.trim()
  if (!title) {
    draft.title = props.task.title
    draft.description = props.task.description || ''
    return
  }
  const description = draft.description.trim()
  const patch = {}
  if (title !== props.task.title) patch.title = title
  if (description !== (props.task.description || '')) patch.description = description || null
  if (Object.keys(patch).length) emit('update', patch)
}

function finish() {
  if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
}
</script>

<template>
  <article
    class="group flex border border-line bg-white transition-colors hover:border-ink focus-within:border-ink"
    :class="done ? 'opacity-60' : ''"
    @click="compact && $emit('open')"
    @focusin="onFocusIn"
    @focusout="onFocusOut"
  >
    <div
      v-if="!compact"
      class="card-grip w-2 shrink-0 cursor-grab border-r border-line active:cursor-grabbing"
      :title="t('task.drag')"
    />
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2 px-2.5" :class="compact ? 'min-h-11' : 'h-8'">
        <h3
          v-if="compact"
          class="min-w-0 flex-1 text-[13px] font-semibold leading-5 text-ink"
          :class="done ? 'line-through decoration-1' : ''"
        >
          {{ task.title }}
        </h3>
        <input
          v-else
          ref="titleEl"
          v-model="draft.title"
          maxlength="500"
          :placeholder="t('task.titlePh')"
          class="h-5 min-w-0 flex-1 bg-transparent py-0 text-[13px] font-semibold leading-5 text-ink outline-none placeholder:font-medium placeholder:text-steel/60"
          :class="done ? 'line-through decoration-1' : ''"
          @click.stop
          @change="commit"
          @keydown.enter.exact.prevent="descEl?.focus()"
          @keydown.esc="titleEl?.blur()"
        />
        <button
          v-if="compact && !done"
          type="button"
          class="flex h-9 min-w-9 items-center justify-center text-steel hover:text-ink"
          :title="t('task.moveTitle')"
          @click.stop="$emit('move')"
        >
          <SvgIcon name="right" :size="13" />
        </button>
        <button
          v-if="!done"
          type="button"
          class="flex items-center justify-center text-steel transition-opacity hover:text-signal"
          :class="compact
            ? 'h-9 w-9 opacity-100'
            : dlState === 'overdue' || stageDone
              ? 'h-5 w-5 opacity-100'
              : 'h-5 w-5 opacity-0 group-hover:opacity-100 focus:opacity-100'"
          :title="t('task.completeTitle')"
          @click.stop="$emit('complete')"
        >
          <SvgIcon name="check" :size="13" />
        </button>
        <span v-if="done" class="flex items-center justify-center text-signal" :class="compact ? 'h-9 w-9' : 'h-5 w-5'">
          <SvgIcon name="check" :size="13" />
        </span>
        <span v-else-if="stageDone && !compact" class="flex h-5 w-5 items-center justify-center text-steel">
          <SvgIcon name="check" :size="13" />
        </span>
        <button
          v-if="!compact"
          type="button"
          class="flex h-5 w-5 items-center justify-center text-steel hover:text-ink"
          :title="t('task.open')"
          @click.stop="$emit('open')"
        >
          <SvgIcon name="lines" :size="11" />
        </button>
      </div>

      <p
        v-if="compact && task.description"
        class="line-clamp-2 px-2.5 pb-2 text-[11px] leading-5 text-steel"
      >
        {{ task.description }}
      </p>
      <div v-else-if="!compact" class="flex items-center gap-2 px-2.5" :class="hasMeta ? 'pb-0.5' : 'pb-2'">
        <textarea
          ref="descEl"
          v-model="draft.description"
          maxlength="10000"
          rows="1"
          :placeholder="t('task.description')"
          class="min-h-5 min-w-0 flex-1 resize-none overflow-y-auto bg-transparent py-0 text-[11px] leading-5 text-steel outline-none placeholder:text-steel/50"
          @click.stop
          @change="commit"
          @input="fitDesc"
          @keydown.ctrl.enter.prevent="finish"
          @keydown.meta.enter.prevent="finish"
          @keydown.esc="descEl?.blur()"
        />
      </div>

      <div
        v-if="hasMeta"
        class="flex items-center gap-2 px-2.5"
        :class="compact ? 'h-8 cursor-default' : 'card-grip h-7 cursor-grab active:cursor-grabbing'"
        @click="!compact && $emit('open')"
      >
        <span
          v-if="complexity"
          class="border px-1 font-mono text-[9px] uppercase leading-4 tracking-wide"
          :class="complexityHeavy ? 'border-ink font-bold text-ink' : 'border-line text-steel'"
          :title="t('task.complexity')"
        >
          {{ complexityLabel(complexity) }}
        </span>
        <span
          v-if="checklist.length"
          class="flex items-center gap-1 font-mono text-[10px] font-medium uppercase tabular-nums"
          :class="checklistAllDone ? 'text-signal' : 'text-steel'"
          :title="t('task.checklist')"
        >
          <SvgIcon name="square" :size="9" :class="checklistAllDone ? 'text-signal' : 'text-steel'" />
          {{ checklistDone }}/{{ checklist.length }}
        </span>
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
        <MemberAvatar
          v-if="task.assignee"
          class="ml-auto"
          :user="task.assignee"
          :size="20"
          :title="assigneeTitle"
        />
      </div>
    </div>
  </article>
</template>
