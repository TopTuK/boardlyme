<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { deadlineState, displayName, fmtDeadline, initials } from '../lib/format'

const props = defineProps({
  task: { type: Object, default: null },
  composing: { type: Boolean, default: false },
})

const emit = defineEmits(['open', 'complete', 'update', 'create'])

const { t } = useI18n()

const draft = reactive({
  title: props.task?.title || '',
  description: props.task?.description || '',
})
const focused = ref(false)
const titleEl = ref(null)
const descEl = ref(null)

const done = computed(() => !!props.task?.completed_at)
const stageDone = computed(() => !!props.task?.stage_done && !done.value)
const dlState = computed(() => (props.task ? deadlineState(props.task.deadline) : null))
const assigneeInitials = computed(() => (props.task?.assignee ? initials(props.task.assignee) : ''))
const assigneeTitle = computed(() => (props.task?.assignee ? displayName(props.task.assignee) : ''))

watch(
  () => [props.task?.title, props.task?.description],
  () => {
    if (props.composing || !props.task || focused.value) return
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
  if (props.composing) return
  // Blur can run before Vue has flushed the field value. Save on the next turn,
  // and skip if focus is still inside this card.
  const card = e.currentTarget
  setTimeout(() => {
    if (card.contains(document.activeElement)) return
    commit()
  }, 0)
}

function onFieldChange() {
  if (!props.composing) commit()
}

function commit() {
  if (!props.task) return
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

function submit() {
  const title = draft.title.trim()
  if (!title) return
  emit('create', { title, description: draft.description.trim() })
  draft.title = ''
  draft.description = ''
  nextTick(fitDesc)
  titleEl.value?.focus()
}

function onTitleEnter() {
  if (props.composing && !draft.description.trim()) submit()
  else descEl.value?.focus()
}

function finish() {
  if (props.composing) submit()
  else if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
}
</script>

<template>
  <article
    class="group flex border transition-colors"
    :class="
      composing
        ? 'task-compose border-dashed border-ink/25 hover:border-ink/50 focus-within:border-solid focus-within:border-signal'
        : ['border-line bg-white hover:border-ink focus-within:border-ink', done ? 'opacity-60' : '']
    "
    @focusin="onFocusIn"
    @focusout="onFocusOut"
  >
    <div
      v-if="!composing"
      class="card-grip w-2 shrink-0 cursor-grab border-r border-line active:cursor-grabbing"
      :title="t('task.drag')"
    />
    <div class="min-w-0 flex-1">
    <div class="flex h-8 items-center gap-2 px-2.5">
      <input
        ref="titleEl"
        v-model="draft.title"
        maxlength="500"
        :placeholder="t('task.titlePh')"
        class="h-5 min-w-0 flex-1 bg-transparent py-0 text-[13px] font-semibold leading-5 text-ink outline-none placeholder:font-medium placeholder:text-steel/60"
        :class="done ? 'line-through decoration-1' : ''"
        @click.stop
        @change="onFieldChange"
        @keydown.enter.exact.prevent="onTitleEnter"
        @keydown.esc="titleEl?.blur()"
      />
      <button
        v-if="!composing && !done"
        type="button"
        class="flex h-5 w-5 items-center justify-center text-steel transition-opacity hover:text-signal"
        :class="dlState === 'overdue' || stageDone ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 focus:opacity-100'"
        :title="t('task.completeTitle')"
        @click.stop="$emit('complete')"
      >
        <SvgIcon name="check" :size="13" />
      </button>
      <span v-if="!composing && done" class="flex h-5 w-5 items-center justify-center text-signal">
        <SvgIcon name="check" :size="13" />
      </span>
      <span v-else-if="!composing && stageDone" class="flex h-5 w-5 items-center justify-center text-steel">
        <SvgIcon name="check" :size="13" />
      </span>
      <button
        v-if="!composing"
        type="button"
        class="flex h-5 w-5 items-center justify-center text-steel hover:text-ink"
        :title="t('task.open')"
        @click.stop="$emit('open')"
      >
        <SvgIcon name="lines" :size="11" />
      </button>
    </div>

    <div
      class="flex items-center gap-2 px-2.5"
      :class="composing || !(task && (task.deadline || task.assignee)) ? 'pb-2' : 'pb-0.5'"
    >
      <textarea
        ref="descEl"
        v-model="draft.description"
        maxlength="10000"
        rows="1"
        :placeholder="t('task.description')"
        class="min-h-5 min-w-0 flex-1 resize-none overflow-y-auto bg-transparent py-0 text-[11px] leading-5 text-steel outline-none placeholder:text-steel/50"
        @click.stop
        @change="onFieldChange"
        @input="fitDesc"
        @keydown.ctrl.enter.prevent="finish"
        @keydown.meta.enter.prevent="finish"
        @keydown.esc="descEl?.blur()"
      />
      <button
        v-if="composing"
        type="button"
        class="flex h-5 shrink-0 items-center border border-ink bg-ink px-2 font-mono text-[9px] uppercase tracking-widest text-paper hover:border-signal hover:bg-signal disabled:border-ink/15 disabled:bg-transparent disabled:text-steel/50"
        :disabled="!draft.title.trim()"
        @click="submit"
      >
        {{ t('common.add') }}
      </button>
    </div>

    <div
      v-if="!composing && (task.deadline || task.assignee)"
      class="card-grip flex h-7 cursor-grab items-center gap-2 px-2.5 active:cursor-grabbing"
      @click="$emit('open')"
    >
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
      <span
        v-if="task.assignee"
        class="ml-auto flex h-5 w-5 items-center justify-center bg-ink font-mono text-[9px] font-bold text-paper"
        :title="assigneeTitle"
      >
        {{ assigneeInitials }}
      </span>
    </div>
    </div>
  </article>
</template>
