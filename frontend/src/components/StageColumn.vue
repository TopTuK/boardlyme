<script setup>
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import draggable from 'vuedraggable'
import TaskCard from './TaskCard.vue'
import { stageName } from '../lib/messages'

const props = defineProps({
  stage: { type: Object, required: true },
  // Store-backed lane arrays; vuedraggable splices them directly, which is
  // what makes cross-stage / cross-lane drag-and-drop work.
  tasks: { type: Array, required: true },
  doneTasks: { type: Array, default: () => [] },
  canManage: { type: Boolean, default: false },
})

const emit = defineEmits(['move', 'open-task', 'complete', 'update-task', 'rename', 'delete', 'add-task', 'set-wip', 'toggle-split'])
const { t } = useI18n()

const editing = ref(false)
const editName = ref('')
const renameInput = ref(null)
const wipOpen = ref(false)
const wipValue = ref('')
const wipInput = ref(null)

const total = computed(() => props.tasks.length + props.doneTasks.length)
const wipFull = computed(
  () => props.stage.wip_limit != null && props.tasks.length >= props.stage.wip_limit,
)

// Work stations in line order. Backlog and Done keep their own marks.
const WORK_ACCENTS = ['#3C5A73', '#E8590C', '#A67C42', '#5E4B8A', '#8C4A3A']
const accent = computed(() => {
  if (props.stage.is_backlog) return '#2C2C2A'
  if (props.stage.is_done) return '#3E6B52'
  const index = Math.max(0, props.stage.position - 1)
  return WORK_ACCENTS[index % WORK_ACCENTS.length]
})

async function beginRename() {
  editName.value = props.stage.name
  editing.value = true
  await nextTick()
  renameInput.value?.focus()
}

function saveRename() {
  const value = editName.value.trim()
  editing.value = false
  if (value) emit('rename', value)
}

async function openWip() {
  wipValue.value = props.stage.wip_limit ?? ''
  wipOpen.value = true
  await nextTick()
  wipInput.value?.focus()
}

function saveWip() {
  if (!wipOpen.value) return // esc already closed the form; skip the blur call
  wipOpen.value = false
  const raw = String(wipValue.value).trim()
  if (raw === '') emit('set-wip', null)
  else {
    const n = Number(raw)
    if (Number.isInteger(n) && n >= 1 && n <= 999) emit('set-wip', n)
  }
}

function onChange(evt, lane) {
  if (evt.added) emit('move', evt.added.element.id, evt.added.newIndex, lane)
  else if (evt.moved) emit('move', evt.moved.element.id, evt.moved.newIndex, lane)
}

function addTask(payload) {
  if (!payload?.title?.trim()) return
  emit('add-task', payload)
}
</script>

<template>
  <section
    class="stage flex h-full max-h-full min-h-0 w-64 shrink-0 flex-col overflow-hidden border border-ink/10 sm:w-72"
    :style="{ '--stage': accent }"
  >
    <header class="stage-head border-b border-line">
      <div class="h-[3px] bg-[var(--stage)]" />
      <div class="px-3 py-2.5">
      <template v-if="editing">
        <input
          :ref="(el) => (renameInput = el)"
          v-model="editName"
          maxlength="100"
          class="w-full border-2 border-ink bg-white px-1.5 py-1 font-sans text-sm font-semibold tracking-tight outline-none"
          @keydown.enter="saveRename"
          @keydown.esc="editing = false"
          @blur="saveRename"
        />
      </template>
      <template v-else>
        <div class="flex items-center justify-between gap-2">
          <h2 class="flex min-w-0 items-center gap-2 font-sans text-[15px] font-semibold tracking-tight text-ink">
            <SvgIcon v-if="stage.is_done" name="check" :size="13" class="text-[var(--stage)]" />
            <span v-else class="h-1.5 w-1.5 shrink-0 bg-[var(--stage)]" />
            <span class="truncate">{{ stageName(stage) }}</span>
          </h2>
          <div class="flex shrink-0 items-center gap-1.5">
            <span
              v-if="stage.wip_limit != null"
              class="font-mono text-[11px] font-medium tabular-nums"
              :class="wipFull ? 'text-[#C92A2A]' : 'text-[var(--stage)]'"
            >
              {{ tasks.length }}/{{ stage.wip_limit }}
            </span>
            <span v-else class="font-mono text-[11px] font-medium tabular-nums text-[var(--stage)]">{{ String(total).padStart(2, '0') }}</span>
          </div>
        </div>
        <div v-if="canManage && !stage.is_done" class="mt-2 flex items-center gap-2.5">
          <button class="font-mono text-[9px] uppercase tracking-widest text-steel hover:text-ink" :title="t('stage.rename')" @click="beginRename">
            <SvgIcon name="pencil" :size="11" />
          </button>
          <button
            v-if="!stage.is_backlog"
            class="font-mono text-[9px] uppercase tracking-widest text-steel hover:text-ink"
            :title="stage.wip_limit == null ? t('stage.setWip') : t('stage.changeWip')"
            @click="openWip"
          >
            {{ t('stage.wip') }}
          </button>
          <button
            v-if="!stage.is_backlog"
            class="font-mono text-[9px] uppercase tracking-widest text-steel hover:text-ink"
            :title="stage.is_split ? t('stage.mergeTitle') : t('stage.splitTitle')"
            @click="$emit('toggle-split', !stage.is_split)"
          >
            {{ stage.is_split ? t('stage.merge') : t('stage.split') }}
          </button>
          <button v-if="!stage.is_backlog" class="text-steel hover:text-[#C92A2A]" :title="t('stage.delete')" @click="$emit('delete')">
            <SvgIcon name="trash" :size="11" />
          </button>
        </div>
      </template>

      <!-- WIP limit editor -->
      <div v-if="wipOpen" class="mt-2 flex items-center gap-1.5 border-t border-line pt-2">
        <span class="font-mono text-[9px] uppercase tracking-widest text-steel">WIP</span>
        <input
          :ref="(el) => (wipInput = el)"
          v-model="wipValue"
          type="number"
          min="1"
          max="999"
          :placeholder="t('stage.none')"
          class="w-16 border border-ink bg-white px-1.5 py-0.5 font-mono text-[10px] outline-none"
          @keydown.enter="saveWip"
          @keydown.esc="wipOpen = false"
          @blur="saveWip"
        />
        <button class="font-mono text-[9px] uppercase tracking-widest text-signal hover:underline" @click="((wipOpen = false), emit('set-wip', null))">
          {{ t('stage.clear') }}
        </button>
      </div>
      </div>
    </header>

    <!-- split stage: active / done sub-stages -->
    <template v-if="stage.is_split">
      <div class="flex items-center justify-between px-3 pt-2.5">
        <span class="font-sans text-[11px] font-semibold tracking-tight text-[var(--stage)]">{{ t('stage.active') }}</span>
        <span v-if="stage.wip_limit != null" class="font-mono text-[9px]" :class="wipFull ? 'text-[#C92A2A]' : 'text-steel'">
          {{ tasks.length }}/{{ stage.wip_limit }}
        </span>
      </div>
      <div class="relative min-h-0 flex-1">
        <p
          v-if="!tasks.length"
          class="pointer-events-none absolute inset-x-0 top-0 px-3 pt-3 text-center text-[13px] text-steel"
        >
          {{ t('stage.empty') }}
        </p>
        <draggable
          :list="tasks"
          :group="{ name: 'tasks' }"
          item-key="id"
          :animation="150"
          ghost-class="drag-ghost"
          handle=".card-grip"
          class="relative min-h-[40px] h-full space-y-2 overflow-y-auto p-2"
          @change="(evt) => onChange(evt, false)"
        >
        <template #item="{ element }">
          <TaskCard
            :task="element"
            @open="$emit('open-task', element)"
            @complete="$emit('complete', element)"
            @update="(patch) => $emit('update-task', element, patch)"
          />
        </template>
        </draggable>
      </div>

      <div class="flex items-center justify-between border-t border-line px-3 py-2">
        <span class="flex items-center gap-1.5 font-sans text-[11px] font-semibold tracking-tight text-[#3E6B52]">
          <SvgIcon name="check" :size="11" /> {{ t('stage.done') }}
        </span>
        <span class="font-mono text-[10px] font-medium tabular-nums text-[#3E6B52]">{{ String(doneTasks.length).padStart(2, '0') }}</span>
      </div>
      <div class="relative max-h-56 min-h-[40px]">
        <p
          v-if="!doneTasks.length"
          class="pointer-events-none absolute inset-x-0 top-0 px-3 pt-3 text-center text-[13px] text-steel"
        >
          {{ t('stage.empty') }}
        </p>
        <draggable
          :list="doneTasks"
          :group="{ name: 'tasks' }"
          item-key="id"
          :animation="150"
          ghost-class="drag-ghost"
          handle=".card-grip"
          class="relative max-h-56 min-h-[40px] space-y-2 overflow-y-auto p-2"
          @change="(evt) => onChange(evt, true)"
        >
        <template #item="{ element }">
          <TaskCard
            :task="element"
            @open="$emit('open-task', element)"
            @complete="$emit('complete', element)"
            @update="(patch) => $emit('update-task', element, patch)"
          />
        </template>
        </draggable>
      </div>
    </template>

    <!-- regular stage: single lane -->
    <div v-else class="relative min-h-[60px] flex-1">
      <p
        v-if="!tasks.length"
        class="pointer-events-none absolute inset-x-0 top-0 px-3 pt-3 text-center text-[13px] text-steel"
      >
        {{ t('stage.empty') }}
      </p>
      <draggable
        :list="tasks"
        :group="{ name: 'tasks' }"
        item-key="id"
        :animation="150"
        ghost-class="drag-ghost"
        handle=".card-grip"
        class="relative min-h-[60px] h-full space-y-2 overflow-y-auto p-2"
        @change="(evt) => onChange(evt, false)"
      >
      <template #item="{ element }">
        <TaskCard
          :task="element"
          @open="$emit('open-task', element)"
          @complete="$emit('complete', element)"
          @update="(patch) => $emit('update-task', element, patch)"
        />
      </template>
      </draggable>
    </div>

    <footer v-if="stage.is_backlog" class="border-t border-line p-2">
      <TaskCard composing @create="addTask" />
    </footer>
  </section>
</template>
