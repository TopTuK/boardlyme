<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useBoardStore } from '../stores/board'
import { deadlineState, memberName } from '../lib/format'
import { stageName } from '../lib/messages'
import { COMPLEXITY_LEVELS, DEFAULT_COMPLEXITY, complexityLabel } from '../lib/complexity'

const props = defineProps({
  task: { type: Object, required: true },
  members: { type: Array, default: () => [] },
})

const emit = defineEmits(['close'])

const board = useBoardStore()
const auth = useAuthStore()
const { t } = useI18n()

const stage = computed(() => board.stages.find((s) => s.id === props.task.stage_id))
const done = computed(() => !!props.task.completed_at)
const stageSplit = computed(() => !!stage.value?.is_split)
const inStageDone = computed(() => !!props.task.stage_done)

const form = reactive({
  title: props.task.title,
  description: props.task.description || '',
  deadline: props.task.deadline || '',
  assignee_id: props.task.assignee_id || '',
  complexity: props.task.complexity || DEFAULT_COMPLEXITY,
})
const saving = ref(false)
const confirmDelete = ref(false)
const newItem = ref('')

const checklist = computed(() => props.task.checklist || [])
const checklistDone = computed(() => checklist.value.filter((i) => i.is_done).length)
const checklistOpen = computed(
  () => checklist.value.length > 0 && checklistDone.value === checklist.value.length
)

async function addItem() {
  const content = newItem.value.trim()
  if (!content) return
  if (await board.addChecklistItem(props.task.id, content)) newItem.value = ''
}

function toggleItem(item) {
  board.updateChecklistItem(props.task.id, item.id, { is_done: !item.is_done })
}

function removeItem(item) {
  board.removeChecklistItem(props.task.id, item.id)
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

async function save() {
  if (!form.title.trim() || saving.value) return
  saving.value = true
  const ok = await board.updateTask(props.task.id, {
    title: form.title.trim(),
    description: form.description.trim() || null,
    deadline: form.deadline || null,
    assignee_id: form.assignee_id || null,
    complexity: form.complexity,
  })
  saving.value = false
  if (ok) emit('close')
}

async function complete() {
  if (await board.completeTask(props.task.id)) emit('close')
}

async function markStageDone() {
  if (await board.sendToStageDone(props.task.id)) emit('close')
}

async function backToStageActive() {
  if (await board.returnToStageActive(props.task.id)) emit('close')
}

async function reopen() {
  if (await board.reopenTask(props.task.id)) emit('close')
}

async function remove() {
  if (await board.deleteTask(props.task.id)) emit('close')
}

function assignMe() {
  form.assignee_id = auth.user?.id || ''
}
</script>

<template>
  <div class="sheet-overlay">
    <div class="sheet-panel max-w-xl">
      <header class="flex items-center justify-between border-b-2 border-ink px-4 py-3">
        <div class="flex items-center gap-2">
          <span class="bg-ink px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-paper">{{ t('task.badge') }}</span>
          <span class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ stageName(stage) }}</span>
          <span
            v-if="done"
            class="bg-signal px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-white"
          >
            {{ t('task.done') }}
          </span>
          <span
            v-else-if="inStageDone"
            class="border border-steel px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-steel"
          >
            {{ t('task.stageDone') }}
          </span>
        </div>
        <button class="text-steel hover:text-ink" @click="emit('close')">
          <SvgIcon name="x" :size="14" />
        </button>
      </header>

      <div class="space-y-4 p-4">
        <label class="block">
          <span class="mb-1 block font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('task.title') }}</span>
          <input
            v-model="form.title"
            maxlength="500"
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

        <div>
          <div class="mb-1 flex items-center justify-between">
            <span class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('task.checklist') }}</span>
            <span
              v-if="checklist.length"
              class="font-mono text-[10px] font-bold uppercase tabular-nums"
              :class="checklistOpen ? 'text-signal' : 'text-steel'"
            >
              {{ checklistDone }}/{{ checklist.length }}
            </span>
          </div>

          <ul v-if="checklist.length" class="border border-line bg-white">
            <li
              v-for="item in checklist"
              :key="item.id"
              class="group/item flex items-center gap-2.5 border-b border-line px-2.5 py-1.5 last:border-b-0"
            >
              <button
                type="button"
                class="flex h-4 w-4 shrink-0 items-center justify-center border-2 transition-colors"
                :class="item.is_done ? 'border-ink bg-ink text-paper' : 'border-ink/40 bg-white hover:border-signal'"
                :title="item.is_done ? t('task.uncheckItem') : t('task.checkItem')"
                @click="toggleItem(item)"
              >
                <SvgIcon v-if="item.is_done" name="check" :size="9" />
              </button>
              <span
                class="min-w-0 flex-1 break-words text-[13px] leading-5"
                :class="item.is_done ? 'text-steel line-through decoration-1' : 'text-ink'"
              >{{ item.content }}</span>
              <button
                type="button"
                class="flex h-5 w-5 shrink-0 items-center justify-center text-steel opacity-100 transition-opacity hover:text-[#C92A2A] focus-visible:opacity-100 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover/item:opacity-100 [@media(hover:hover)]:focus-visible:opacity-100"
                :title="t('common.delete')"
                @click="removeItem(item)"
              >
                <SvgIcon name="trash" :size="11" />
              </button>
            </li>
          </ul>

          <input
            v-model="newItem"
            maxlength="500"
            :placeholder="t('task.addChecklistItem')"
            class="mt-1 w-full border border-dashed border-ink/25 bg-white px-3 py-1.5 text-[13px] outline-none placeholder:text-steel/50 focus:border-solid focus:border-ink"
            @keydown.enter.prevent="addItem"
          />
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block">
            <span class="mb-1 block font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('task.deadline') }}</span>
            <input
              v-model="form.deadline"
              type="date"
              class="w-full border border-line bg-white px-3 py-2 font-mono text-xs outline-none focus:border-ink"
            />
            <span
              v-if="form.deadline && deadlineState(form.deadline) === 'overdue'"
              class="mt-1 block font-mono text-[10px] uppercase text-[#C92A2A]"
            >
              {{ t('task.overdue') }}
            </span>
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

      <footer class="flex flex-wrap items-center justify-between gap-2 border-t-2 border-ink px-4 py-3">
        <div class="flex items-center gap-2">
          <template v-if="confirmDelete">
            <span class="font-mono text-[10px] uppercase text-[#C92A2A]">{{ t('common.deleteQ') }}</span>
            <Btn variant="danger" @click="remove">{{ t('common.yesDelete') }}</Btn>
            <Btn variant="ghost" @click="confirmDelete = false">{{ t('common.no') }}</Btn>
          </template>
          <Btn v-else variant="danger" @click="confirmDelete = true">
            <SvgIcon name="trash" :size="11" /> {{ t('common.delete') }}
          </Btn>
        </div>
        <div class="ml-auto flex flex-wrap items-center gap-2">
          <Btn
            v-if="stageSplit && !done && !inStageDone"
            variant="ghost"
            :title="t('task.stageDoneTitle')"
            @click="markStageDone"
          >
            <SvgIcon name="check" :size="11" /> {{ t('task.stageDone') }}
          </Btn>
          <Btn v-if="inStageDone && !done" variant="ghost" @click="backToStageActive">{{ t('task.backActive') }}</Btn>
          <Btn
            v-if="!done"
            :disabled="checklist.length > 0 && !checklistOpen"
            :title="checklist.length > 0 && !checklistOpen ? t('task.checklistBlockedTitle') : t('task.completeTitle')"
            @click="complete"
          >
            <SvgIcon name="check" :size="11" /> {{ t('task.complete') }}
          </Btn>
          <Btn v-else variant="ghost" @click="reopen">{{ t('task.reopen') }}</Btn>
          <Btn variant="ghost" @click="emit('close')">{{ t('common.cancel') }}</Btn>
          <Btn :disabled="saving || !form.title.trim()" @click="save">{{ t('common.save') }}</Btn>
        </div>
      </footer>
    </div>
  </div>
</template>
