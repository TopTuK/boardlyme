<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useBoardStore } from '../stores/board'
import { memberName } from '../lib/format'
import { COMPLEXITY_LEVELS, DEFAULT_COMPLEXITY, complexityLabel } from '../lib/complexity'

defineProps({
  members: { type: Array, default: () => [] },
})

const emit = defineEmits(['close'])

const board = useBoardStore()
const auth = useAuthStore()
const { t } = useI18n()

const form = reactive({
  title: '',
  description: '',
  deadline: '',
  assignee_id: '',
  complexity: DEFAULT_COMPLEXITY,
})
const saving = ref(false)
const titleEl = ref(null)
const dialogEl = ref(null)
let previousFocus = null

function focusable() {
  if (!dialogEl.value) return []
  return [...dialogEl.value.querySelectorAll('a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])')].filter(
    (el) => !el.disabled && el.tabIndex !== -1
  )
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    emit('close')
    return
  }
  if (e.key !== 'Tab') return
  const items = focusable()
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  const active = document.activeElement
  if (e.shiftKey && (active === first || !dialogEl.value.contains(active))) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && (active === last || !dialogEl.value.contains(active))) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(async () => {
  previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
  window.addEventListener('keydown', onKeydown)
  await nextTick()
  titleEl.value?.focus()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  previousFocus?.focus()
})

function assignMe() {
  form.assignee_id = auth.user?.id || ''
}

async function submit() {
  const title = form.title.trim()
  const backlog = board.stages.find((s) => s.is_backlog)
  if (!title || saving.value || !backlog) return
  saving.value = true
  const ok = await board.createTask(backlog.id, {
    title,
    description: form.description.trim(),
    deadline: form.deadline || null,
    assignee_id: form.assignee_id || null,
    complexity: form.complexity,
  })
  saving.value = false
  if (ok) emit('close')
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 sm:items-center sm:p-4">
    <form
      ref="dialogEl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-task-title"
      class="max-h-[92vh] w-full max-w-xl overflow-y-auto border-2 border-ink bg-paper shadow-offset"
      @submit.prevent="submit"
    >
      <header class="flex items-center justify-between border-b-2 border-ink px-4 py-3">
        <div class="flex items-center gap-2">
          <span id="create-task-title" class="bg-ink px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-paper">{{ t('task.new') }}</span>
          <span class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('stages.backlog') }}</span>
        </div>
        <button type="button" class="text-steel hover:text-ink" :aria-label="t('common.close')" @click="emit('close')">
          <SvgIcon name="x" :size="14" />
        </button>
      </header>

      <div class="space-y-4 p-4">
        <label class="block">
          <span class="mb-1 block font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('task.title') }}</span>
          <input
            ref="titleEl"
            v-model="form.title"
            maxlength="500"
            :placeholder="t('task.titlePh')"
            class="w-full border-2 border-ink bg-white px-3 py-2 text-sm font-semibold outline-none focus:border-signal"
          />
        </label>

        <label class="block">
          <span class="mb-1 block font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('task.description') }}</span>
          <textarea
            v-model="form.description"
            rows="4"
            maxlength="10000"
            :placeholder="t('task.descriptionPh')"
            class="w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-ink"
          ></textarea>
        </label>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block">
            <span class="mb-1 block font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('task.deadline') }}</span>
            <input
              v-model="form.deadline"
              type="date"
              class="w-full border border-line bg-white px-3 py-2 font-mono text-xs outline-none focus:border-ink"
            />
          </label>

          <label class="block">
            <span class="mb-1 block font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('task.assignee') }}</span>
            <select
              v-model="form.assignee_id"
              class="w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-ink"
            >
              <option value="">{{ t('task.unassigned') }}</option>
              <option v-for="m in members" :key="m.user_id" :value="m.user_id">{{ memberName(m) }}</option>
            </select>
            <button
              type="button"
              class="mt-1 font-mono text-[10px] uppercase tracking-widest text-signal hover:underline"
              @click="assignMe"
            >
              {{ t('task.assignMe') }}
            </button>
          </label>
        </div>

        <label class="block">
          <span class="mb-1 block font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('task.complexity') }}</span>
          <select
            v-model="form.complexity"
            class="w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-ink sm:w-1/2"
          >
            <option v-for="level in COMPLEXITY_LEVELS" :key="level" :value="level">{{ complexityLabel(level) }}</option>
          </select>
        </label>
      </div>

      <footer class="flex items-center justify-end gap-2 border-t-2 border-ink px-4 py-3">
        <Btn variant="ghost" type="button" @click="emit('close')">{{ t('common.cancel') }}</Btn>
        <Btn type="submit" :disabled="saving || !form.title.trim()">{{ t('common.create') }}</Btn>
      </footer>
    </form>
  </div>
</template>
