<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useBoardStore } from '../stores/board'
import { deadlineState, memberName } from '../lib/format'
import { stageName } from '../lib/messages'

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
})
const saving = ref(false)
const confirmDelete = ref(false)

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
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 sm:items-center sm:p-4">
    <div class="max-h-[92vh] w-full max-w-xl overflow-y-auto border-2 border-ink bg-paper shadow-offset">
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
          <Btn v-if="!done" @click="complete"><SvgIcon name="check" :size="11" /> {{ t('task.complete') }}</Btn>
          <Btn v-else variant="ghost" @click="reopen">{{ t('task.reopen') }}</Btn>
          <Btn variant="ghost" @click="emit('close')">{{ t('common.cancel') }}</Btn>
          <Btn :disabled="saving || !form.title.trim()" @click="save">{{ t('common.save') }}</Btn>
        </div>
      </footer>
    </div>
  </div>
</template>
