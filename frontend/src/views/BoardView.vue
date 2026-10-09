<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useBoardStore } from '../stores/board'
import { useIsPhone } from '../composables/media'
import { memberName } from '../lib/format'
import MemberAvatar from '../components/MemberAvatar.vue'
import OverflowMenu from '../components/OverflowMenu.vue'
import StageRail from '../components/StageRail.vue'
import StationPane from '../components/StationPane.vue'
import MoveTaskSheet from '../components/MoveTaskSheet.vue'
import { displayError, stageName } from '../lib/messages'
import draggable from 'vuedraggable'
import CreateTaskModal from '../components/CreateTaskModal.vue'
import StageColumn from '../components/StageColumn.vue'
import TaskModal from '../components/TaskModal.vue'
import ShareModal from '../components/ShareModal.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const store = useBoardStore()
const auth = useAuthStore()
const { t } = useI18n()
const isPhone = useIsPhone()

const activeTaskId = ref(null)
const createOpen = ref(false)
const shareOpen = ref(false)
const confirmState = ref(null)
const renaming = ref(false)
const renameValue = ref('')
const addingStage = ref(false)
const newStageName = ref('')
const movingTask = ref(null)
const activeStageId = ref(null)
const stageEdit = ref(null) // 'rename' | 'wip' | null
const stageEditValue = ref('')

const isOwner = computed(() => !!(store.project && auth.user && store.project.owner_id === auth.user.id))
const activeTask = computed(() => store.tasks.find((t) => t.id === activeTaskId.value) || null)
// Mirrors the API guard: a task is done in a Done stage or a done sub-stage.
const activeTaskCount = computed(() => {
  const doneStageIds = new Set(store.stages.filter((s) => s.is_done).map((s) => s.id))
  return store.tasks.filter((t) => !doneStageIds.has(t.stage_id) && !t.stage_done).length
})
const doneStage = computed(() => store.doneStage)
const showDone = computed({
  get: () => (doneStage.value ? !doneStage.value.is_hidden : false),
  set: (value) => {
    if (doneStage.value) store.updateStage(doneStage.value.id, { is_hidden: !value })
  },
})

const activeStage = computed(() => store.visibleStages.find((s) => s.id === activeStageId.value) || null)
const stageCounts = computed(() => {
  const map = {}
  for (const s of store.visibleStages) {
    const lanes = store.lanes(s.id)
    map[s.id] = lanes.active.length + lanes.done.length
  }
  return map
})

function stationKey(projectId) {
  return `boardly.station.${projectId}`
}

function syncActiveStation() {
  const stages = store.visibleStages
  if (!stages.length) {
    activeStageId.value = null
    return
  }
  const saved = store.project ? sessionStorage.getItem(stationKey(store.project.id)) : null
  if (activeStageId.value && stages.some((s) => s.id === activeStageId.value)) return
  if (saved && stages.some((s) => s.id === saved)) {
    activeStageId.value = saved
    return
  }
  activeStageId.value = stages[0].id
}

watch(
  () => [store.project?.id, store.visibleStages.map((s) => s.id).join(',')],
  () => syncActiveStation(),
)

watch(activeStageId, (id) => {
  if (id && store.project) sessionStorage.setItem(stationKey(store.project.id), id)
})

function selectStation(id) {
  activeStageId.value = id
  stageEdit.value = null
}

function goStation(dir) {
  const stages = store.visibleStages
  const idx = stages.findIndex((s) => s.id === activeStageId.value)
  const next = stages[idx + dir]
  if (next) selectStation(next.id)
}

function beginStageRename() {
  if (!activeStage.value) return
  stageEdit.value = 'rename'
  stageEditValue.value = activeStage.value.name
}

function beginStageWip() {
  if (!activeStage.value) return
  stageEdit.value = 'wip'
  stageEditValue.value = activeStage.value.wip_limit ?? ''
}

async function saveStageEdit() {
  const kind = stageEdit.value
  const stage = activeStage.value
  const value = stageEditValue.value.trim()
  stageEdit.value = null
  if (!kind || !stage) return
  if (kind === 'rename') {
    if (value) await store.updateStage(stage.id, { name: value })
    return
  }
  if (kind === 'wip') {
    if (value === '') await store.setWipLimit(stage.id, null)
    else {
      const n = Number(value)
      if (Number.isInteger(n) && n >= 1 && n <= 999) await store.setWipLimit(stage.id, n)
    }
  }
}

// Column drag-and-drop: the visible columns are dragged through vuedraggable.
// commitStageOrder turns a visible-only order into the full permutation the
// API needs: Done is stripped from the visible order and re-appended exactly
// once (after the hidden stages), so Backlog stays first and Done stays last.
function commitStageOrder(visibleOrder) {
  const work = visibleOrder.filter((s) => !s.is_done)
  const hidden = store.stages.filter((s) => s.is_hidden && !s.is_done)
  const full = [...work, ...hidden]
  if (doneStage.value) full.push(doneStage.value)
  store.reorderStages(full.map((s) => s.id))
}

const stageOrder = computed({
  get: () => store.visibleStages,
  set: (value) => commitStageOrder(value),
})

// Backlog is pinned first and Done is pinned last — cancel those drops.
function onStageMove(evt) {
  const stage = evt.draggedContext.element
  if (stage.is_backlog || stage.is_done) return false
  const { futureIndex } = evt.draggedContext
  if (futureIndex === 0) return false
  const visible = store.visibleStages
  const last = visible[visible.length - 1]
  if (last?.is_done && futureIndex >= visible.length) return false
  return true
}

// Keyboard stage moves share the pins: never before Backlog, never past Done.
function canMoveStage(stage, dir) {
  const visible = store.visibleStages
  const idx = visible.findIndex((s) => s.id === stage.id)
  if (idx === -1 || stage.is_backlog || stage.is_done) return false
  const maxIdx = visible[visible.length - 1]?.is_done ? visible.length - 2 : visible.length - 1
  const target = idx + dir
  return target >= 1 && target <= maxIdx
}

function moveStage(stage, dir) {
  if (!canMoveStage(stage, dir)) return
  const visible = [...store.visibleStages]
  const idx = visible.findIndex((s) => s.id === stage.id)
  visible.splice(idx + dir, 0, ...visible.splice(idx, 1))
  commitStageOrder(visible)
}

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

function askDeleteProject() {
  if (activeTaskCount.value) {
    store.error = 'api.projectHasActiveTasks'
    return
  }
  confirmState.value = {
    title: t('board.deleteProjectTitle', { name: store.project.name.toUpperCase() }),
    message: t('board.deleteProjectMessage', { name: store.project.name }),
    confirmLabel: t('common.yesDelete'),
    onConfirm: async () => {
      if (await store.deleteProject()) router.replace('/boards')
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

const wsClass = computed(() =>
  store.wsStatus === 'on' ? 'text-emerald-700' : store.polling ? 'text-signal' : 'text-steel',
)
const wsDot = computed(() =>
  store.wsStatus === 'on' ? 'bg-emerald-600' : store.polling ? 'bg-signal' : 'bg-steel',
)
const wsLabel = computed(() =>
  store.wsStatus === 'on' ? t('board.live') : store.polling ? t('board.poll') : t('board.offline'),
)
</script>

<template>
  <!-- loading -->
  <main v-if="store.loading && !store.project" class="flex h-[calc(100dvh-3.5rem-env(safe-area-inset-top))] items-center justify-center">
    <span class="font-mono text-xs uppercase tracking-widest text-steel">{{ t('board.loading') }}</span>
  </main>

  <div v-else-if="store.project" class="flex h-[calc(100dvh-3.5rem-env(safe-area-inset-top))] flex-col">
    <!-- phone station chrome -->
    <template v-if="isPhone">
      <div class="flex items-center gap-2 border-b border-line bg-paper px-3 py-1.5">
        <input
          v-if="renaming"
          v-model="renameValue"
          maxlength="200"
          class="min-w-0 flex-1 border-2 border-ink bg-white px-2 py-1 text-sm font-bold uppercase outline-none"
          @keydown.enter="saveRename"
          @keydown.esc="renaming = false"
          @blur="saveRename"
        />
        <h1
          v-else
          class="min-w-0 flex-1 truncate text-base font-black uppercase tracking-tight"
          :title="isOwner ? t('board.renameTitle') : ''"
          @click="isOwner && startRename()"
        >
          {{ store.project.name }}
        </h1>
        <span v-if="!isOwner" class="shrink-0 border border-line px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-steel">
          {{ t('roles.editor') }}
        </span>
        <span
          class="flex shrink-0 items-center gap-1 font-mono text-[10px] uppercase tracking-widest"
          :class="wsClass"
          :title="store.polling ? t('board.pollTitle') : t('board.liveTitle')"
        >
          <span class="h-2 w-2" :class="wsDot"></span>
        </span>
        <OverflowMenu :label="t('board.more')">
          <template #default="{ close }">
            <div v-if="store.members.length" class="flex items-center gap-1 border-b border-line px-3 py-2">
              <MemberAvatar
                v-for="m in store.members"
                :key="m.user_id"
                :user="m"
                :owner="m.role === 'owner'"
                :title="memberName(m)"
              />
            </div>
            <button
              v-if="doneStage"
              type="button"
              class="menu-item"
              @click="(showDone = !showDone, close())"
            >
              {{ showDone ? t('board.hideDone') : t('board.showDone') }}
            </button>
            <button
              type="button"
              class="menu-item"
              @click="(close(), router.push({ name: 'metrics', params: { id: store.project.id } }))"
            >
              <SvgIcon name="chart" :size="12" /> {{ t('board.metrics') }}
            </button>
            <button v-if="isOwner" type="button" class="menu-item" @click="(close(), shareOpen = true)">
              <SvgIcon name="share" :size="12" /> {{ t('board.share') }}
            </button>
            <button v-else type="button" class="menu-item" @click="(close(), askLeave())">
              <SvgIcon name="logout" :size="12" /> {{ t('board.leave') }}
            </button>
            <button v-if="isOwner" type="button" class="menu-item" @click="(close(), askDeleteProject())">
              <SvgIcon name="trash" :size="12" /> {{ t('board.delete') }}
            </button>
          </template>
        </OverflowMenu>
      </div>

      <StageRail
        :stages="store.visibleStages"
        :active-id="activeStageId"
        :counts="stageCounts"
        :can-add="isOwner"
        @select="selectStation"
        @add="openAddStage"
      />

      <div v-if="addingStage" class="flex gap-2 border-b border-line bg-paper px-3 py-2">
        <input
          id="new-stage-input"
          v-model="newStageName"
          :placeholder="t('board.stageName')"
          maxlength="100"
          class="min-w-0 flex-1 border-2 border-ink bg-white px-2 py-2 font-mono text-xs uppercase outline-none"
          @keydown="addStageKeydown"
          @blur="createStage"
        />
      </div>
      <div v-else-if="stageEdit" class="flex gap-2 border-b border-line bg-paper px-3 py-2">
        <input
          v-model="stageEditValue"
          :placeholder="stageEdit === 'wip' ? t('stage.none') : t('board.stageName')"
          :type="stageEdit === 'wip' ? 'number' : 'text'"
          class="min-w-0 flex-1 border-2 border-ink bg-white px-2 py-2 font-mono text-xs uppercase outline-none"
          @keydown.enter="saveStageEdit"
          @keydown.esc="stageEdit = null"
        />
        <Btn @click="saveStageEdit">{{ t('common.save') }}</Btn>
        <Btn v-if="stageEdit === 'wip'" variant="ghost" @click="(stageEdit = null, store.setWipLimit(activeStage.id, null))">
          {{ t('stage.clear') }}
        </Btn>
      </div>

      <p
        v-if="store.error"
        class="flex items-center justify-between gap-2 border-b border-[#C92A2A] bg-[#C92A2A]/10 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-[#C92A2A]"
      >
        <span>{{ displayError(store.error) }}</span>
        <button class="underline" @click="store.error = ''">{{ t('common.dismiss') }}</button>
      </p>

      <StationPane
        v-if="activeStage"
        class="min-h-0 flex-1"
        :stage="activeStage"
        :tasks="store.lanes(activeStage.id).active"
        :done-tasks="store.lanes(activeStage.id).done"
        @prev="goStation(-1)"
        @next="goStation(1)"
        @open-task="openTask"
        @complete="(task) => store.completeTask(task.id)"
        @update-task="(task, patch) => store.updateTask(task.id, patch)"
        @move-task="(task) => (movingTask = task)"
      />

      <div class="flex items-center gap-2 border-t-2 border-ink bg-paper px-3 py-2 safe-pb">
        <Btn class="flex-1" @click="createOpen = true">
          <SvgIcon name="plus" :size="12" /> {{ t('stage.addTask') }}
        </Btn>
        <OverflowMenu
          v-if="isOwner && activeStage && !activeStage.is_done"
          :label="t('stage.more')"
        >
          <template #default="{ close }">
            <button type="button" class="menu-item" @click="(close(), beginStageRename())">
              <SvgIcon name="pencil" :size="12" /> {{ t('stage.rename') }}
            </button>
            <template v-if="!activeStage.is_backlog">
              <button type="button" class="menu-item" :disabled="!canMoveStage(activeStage, -1)" @click="(close(), moveStage(activeStage, -1))">
                <SvgIcon name="left" :size="12" /> {{ t('stage.moveLeft') }}
              </button>
              <button type="button" class="menu-item" :disabled="!canMoveStage(activeStage, 1)" @click="(close(), moveStage(activeStage, 1))">
                <SvgIcon name="right" :size="12" /> {{ t('stage.moveRight') }}
              </button>
              <button type="button" class="menu-item" @click="(close(), beginStageWip())">
                {{ t('stage.wip') }}
              </button>
              <button type="button" class="menu-item" @click="(close(), store.toggleSplit(activeStage.id, !activeStage.is_split))">
                {{ activeStage.is_split ? t('stage.merge') : t('stage.split') }}
              </button>
              <button type="button" class="menu-item" @click="(close(), askDeleteStage(activeStage))">
                <SvgIcon name="trash" :size="12" /> {{ t('stage.delete') }}
              </button>
            </template>
          </template>
        </OverflowMenu>
      </div>
    </template>

    <!-- desktop kanban -->
    <template v-else>
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
          <div class="flex -space-x-1">
            <MemberAvatar
              v-for="m in store.members"
              :key="m.user_id"
              :user="m"
              :owner="m.role === 'owner'"
              :title="memberName(m)"
            />
          </div>

          <label
            v-if="doneStage"
            class="flex cursor-pointer select-none items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-steel"
            :title="t('board.showDoneTitle')"
          >
            <input v-model="showDone" type="checkbox" class="peer sr-only" />
            <span class="flex h-3.5 w-3.5 items-center justify-center border border-ink peer-checked:bg-signal"></span>
            {{ t('board.showDone') }}
          </label>

          <span
            class="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest"
            :class="wsClass"
            :title="store.polling ? t('board.pollTitle') : t('board.liveTitle')"
          >
            <span class="h-2 w-2" :class="wsDot"></span>
            {{ wsLabel }}
          </span>

          <Btn
            variant="ghost"
            :title="t('board.metricsTitle')"
            @click="router.push({ name: 'metrics', params: { id: store.project.id } })"
          >
            <SvgIcon name="chart" :size="12" /> {{ t('board.metrics') }}
          </Btn>
          <Btn v-if="isOwner" variant="ghost" :title="t('board.deleteTitle')" @click="askDeleteProject">
            <SvgIcon name="trash" :size="12" /> {{ t('board.delete') }}
          </Btn>
          <Btn v-if="isOwner" variant="ghost" @click="shareOpen = true">
            <SvgIcon name="share" :size="12" /> {{ t('board.share') }}
          </Btn>
          <Btn v-else variant="ghost" @click="askLeave">
            <SvgIcon name="logout" :size="12" /> {{ t('board.leave') }}
          </Btn>
        </div>
      </div>

      <p
        v-if="store.error"
        class="flex items-center justify-between gap-2 border-b border-[#C92A2A] bg-[#C92A2A]/10 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-[#C92A2A]"
      >
        <span>{{ displayError(store.error) }}</span>
        <button class="underline" @click="store.error = ''">{{ t('common.dismiss') }}</button>
      </p>

      <div class="flex min-h-0 flex-1 items-stretch gap-3 overflow-x-auto bg-blueprint p-3">
        <draggable
          v-model="stageOrder"
          :move="onStageMove"
          :disabled="!isOwner"
          item-key="id"
          tag="div"
          :animation="150"
          ghost-class="drag-ghost"
          handle=".stage-grip"
          class="flex items-stretch gap-3"
        >
          <template #item="{ element: stage }">
            <StageColumn
              :stage="stage"
              :tasks="store.lanes(stage.id).active"
              :done-tasks="store.lanes(stage.id).done"
              :can-manage="isOwner"
              :can-move-left="canMoveStage(stage, -1)"
              :can-move-right="canMoveStage(stage, 1)"
              @move="(taskId, index, lane) => store.moveTask(taskId, stage.id, index, lane)"
              @move-stage="(dir) => moveStage(stage, dir)"
              @open-task="openTask"
              @complete="(task) => store.completeTask(task.id)"
              @update-task="(task, patch) => store.updateTask(task.id, patch)"
              @rename="(name) => store.updateStage(stage.id, { name })"
              @delete="askDeleteStage(stage)"
              @add-task="createOpen = true"
              @set-wip="(value) => store.setWipLimit(stage.id, value)"
              @toggle-split="(value) => store.toggleSplit(stage.id, value)"
            />
          </template>
        </draggable>

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
    </template>

    <CreateTaskModal v-if="createOpen" :members="store.members" @close="createOpen = false" />
    <TaskModal
      v-if="activeTask"
      :task="activeTask"
      :members="store.members"
      @close="activeTaskId = null"
    />
    <MoveTaskSheet v-if="movingTask" :task="movingTask" @close="movingTask = null" />
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
