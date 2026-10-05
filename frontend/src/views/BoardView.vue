<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useBoardStore } from '../stores/board'
import { initials, memberName } from '../lib/format'
import { displayError, stageName } from '../lib/messages'
import StageColumn from '../components/StageColumn.vue'
import TaskModal from '../components/TaskModal.vue'
import ShareModal from '../components/ShareModal.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const store = useBoardStore()
const auth = useAuthStore()
const { t } = useI18n()

const activeTaskId = ref(null)
const shareOpen = ref(false)
const confirmState = ref(null)
const renaming = ref(false)
const renameValue = ref('')
const addingStage = ref(false)
const newStageName = ref('')

const isOwner = computed(() => !!(store.project && auth.user && store.project.owner_id === auth.user.id))
const activeTask = computed(() => store.tasks.find((t) => t.id === activeTaskId.value) || null)
const doneStage = computed(() => store.doneStage)
const showDone = computed({
  get: () => (doneStage.value ? !doneStage.value.is_hidden : false),
  set: (value) => {
    if (doneStage.value) store.updateStage(doneStage.value.id, { is_hidden: !value })
  },
})

function load() {
  const id = route.params.id
  store
    .fetchBoard(id)
    .then(() => store.connectWS(id))
    .catch(() => router.replace('/boards'))
}

onMounted(load)
onBeforeUnmount(() => store.disconnectWS())
watch(
  () => route.params.id,
  () => {
    if (route.name === 'board') load()
  },
)

function openTask(task) {
  activeTaskId.value = task.id
}

function askDeleteStage(stage) {
  confirmState.value = {
    title: t('board.deleteStageTitle', { name: stageName(stage).toUpperCase() }),
    message: t('board.deleteStageMessage', { name: stageName(stage) }),
    confirmLabel: t('common.delete'),
    onConfirm: () => store.deleteStage(stage.id),
  }
}

function askLeave() {
  confirmState.value = {
    title: t('board.leaveTitle'),
    message: t('board.leaveMessage'),
    confirmLabel: t('board.leave'),
    onConfirm: async () => {
      if (await store.leaveProject()) router.replace('/boards')
    },
  }
}

async function runConfirm() {
  const state = confirmState.value
  if (!state) return
  confirmState.value = null
  await state.onConfirm()
}

function startRename() {
  renameValue.value = store.project.name
  renaming.value = true
}

async function saveRename() {
  renaming.value = false
  const value = renameValue.value.trim()
  if (value && value !== store.project.name) await store.renameProject(value)
}

async function createStage() {
  if (!addingStage.value) return // esc already closed the form; skip the blur call
  const value = newStageName.value.trim()
  addingStage.value = false
  newStageName.value = ''
  if (value) await store.addStage(value)
}

async function addStageKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    await createStage()
  } else if (e.key === 'Escape') {
    addingStage.value = false
    newStageName.value = ''
  }
}

async function openAddStage() {
  addingStage.value = true
  await nextTick()
  document.getElementById('new-stage-input')?.focus()
}
</script>

<template>
  <!-- loading -->
  <main v-if="store.loading && !store.project" class="flex h-[calc(100vh-3.5rem)] items-center justify-center">
    <span class="font-mono text-xs uppercase tracking-widest text-steel">{{ t('board.loading') }}</span>
  </main>

  <div v-else-if="store.project" class="flex h-[calc(100vh-3.5rem)] flex-col">
    <!-- topbar -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line bg-paper px-4 py-2.5">
      <RouterLink
        to="/boards"
        class="flex items-center gap-1 font-mono text-[11px] uppercase tracking-widest text-steel hover:text-ink"
      >
        <SvgIcon name="back" :size="12" /> {{ t('board.boards') }}
      </RouterLink>
      <span class="hidden h-4 w-px bg-line sm:block"></span>

      <input
        v-if="renaming"
        v-model="renameValue"
        maxlength="200"
        class="border-2 border-ink bg-white px-2 py-1 text-sm font-bold uppercase outline-none"
        @keydown.enter="saveRename"
        @keydown.esc="renaming = false"
        @blur="saveRename"
      />
      <h1
        v-else
        class="cursor-default text-base font-black uppercase tracking-tight"
        :title="isOwner ? t('board.renameTitle') : ''"
        @click="isOwner && startRename()"
      >
        {{ store.project.name }}
      </h1>
      <span v-if="!isOwner" class="border border-line px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-steel">
        {{ t('roles.editor') }}
      </span>

      <div class="ml-auto flex flex-wrap items-center gap-2">
        <!-- members -->
        <div class="flex -space-x-1">
          <span
            v-for="m in store.members"
            :key="m.user_id"
            :title="memberName(m)"
            class="flex h-6 w-6 items-center justify-center border border-ink bg-white font-mono text-[9px] font-bold"
            :class="m.role === 'owner' ? 'bg-ink text-paper' : ''"
          >
            {{ initials(m) }}
          </span>
        </div>

        <!-- show done toggle -->
        <label
          v-if="doneStage"
          class="flex cursor-pointer select-none items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-steel"
          :title="t('board.showDoneTitle')"
        >
          <input v-model="showDone" type="checkbox" class="peer sr-only" />
          <span class="flex h-3.5 w-3.5 items-center justify-center border border-ink peer-checked:bg-signal"></span>
          {{ t('board.showDone') }}
        </label>

        <!-- sync status -->
        <span
          class="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest"
          :class="store.wsStatus === 'on' ? 'text-emerald-700' : store.polling ? 'text-signal' : 'text-steel'"
          :title="store.polling ? t('board.pollTitle') : t('board.liveTitle')"
        >
          <span class="h-2 w-2" :class="store.wsStatus === 'on' ? 'bg-emerald-600' : store.polling ? 'bg-signal' : 'bg-steel'"></span>
          {{ store.wsStatus === 'on' ? t('board.live') : store.polling ? t('board.poll') : t('board.offline') }}
        </span>

        <Btn v-if="isOwner" variant="ghost" @click="shareOpen = true">
          <SvgIcon name="share" :size="12" /> {{ t('board.share') }}
        </Btn>
        <Btn v-else variant="ghost" @click="askLeave">
          <SvgIcon name="logout" :size="12" /> {{ t('board.leave') }}
        </Btn>
      </div>
    </div>

    <!-- error flash -->
    <p
      v-if="store.error"
      class="flex items-center justify-between gap-2 border-b border-[#C92A2A] bg-[#C92A2A]/10 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-[#C92A2A]"
    >
      <span>{{ displayError(store.error) }}</span>
      <button class="underline" @click="store.error = ''">{{ t('common.dismiss') }}</button>
    </p>

    <!-- columns -->
    <div class="flex min-h-0 flex-1 items-stretch gap-3 overflow-x-auto bg-blueprint p-3">
      <StageColumn
        v-for="stage in store.visibleStages"
        :key="stage.id"
        :stage="stage"
        :tasks="store.lanes(stage.id).active"
        :done-tasks="store.lanes(stage.id).done"
        :can-manage="isOwner"
        @move="(taskId, index, lane) => store.moveTask(taskId, stage.id, index, lane)"
        @open-task="openTask"
        @complete="(task) => store.completeTask(task.id)"
        @update-task="(task, patch) => store.updateTask(task.id, patch)"
        @rename="(name) => store.updateStage(stage.id, { name })"
        @delete="askDeleteStage(stage)"
        @add-task="(payload) => store.createTask(stage.id, payload)"
        @set-wip="(value) => store.setWipLimit(stage.id, value)"
        @toggle-split="(value) => store.toggleSplit(stage.id, value)"
      />

      <!-- add stage -->
      <div v-if="isOwner" class="w-64 shrink-0 border border-dashed border-ink/15 bg-[#F7F6F1] p-3 sm:w-72">
        <input
          v-if="addingStage"
          id="new-stage-input"
          v-model="newStageName"
          :placeholder="t('board.stageName')"
          maxlength="100"
          class="w-full border-2 border-ink bg-white px-2 py-1.5 font-mono text-xs uppercase outline-none"
          @keydown="addStageKeydown"
          @blur="createStage"
        />
        <button
          v-else
          class="w-full border border-dashed border-steel/60 py-2 font-mono text-[10px] uppercase tracking-widest text-steel hover:border-ink hover:text-ink"
          @click="openAddStage"
        >
          {{ t('board.addStage') }}
        </button>
      </div>
    </div>

    <TaskModal
      v-if="activeTask"
      :task="activeTask"
      :members="store.members"
      @close="activeTaskId = null"
    />
    <ShareModal v-if="shareOpen" @close="shareOpen = false" />
    <ConfirmDialog
      v-if="confirmState"
      :title="confirmState.title"
      :message="confirmState.message"
      :confirm-label="confirmState.confirmLabel"
      @confirm="runConfirm"
      @cancel="confirmState = null"
    />
  </div>
</template>
