<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useProjectsStore } from '../stores/projects'
import { displayError } from '../lib/messages'

const { t } = useI18n()
const projects = useProjectsStore()
const creating = ref(false)
const name = ref('')

onMounted(() => projects.fetch())

async function create() {
  const value = name.value.trim()
  if (!value) return
  try {
    await projects.create(value)
    name.value = ''
    creating.value = false
  } catch (e) {
    projects.error = e?.response?.data?.detail || 'errors.createProject'
  }
}

function progress(p) {
  if (!p.task_count) return 0
  return Math.round((p.done_count / p.task_count) * 100)
}
</script>

<template>
  <main class="mx-auto max-w-6xl px-4 py-8">
    <!-- heading -->
    <div class="flex flex-wrap items-end justify-between gap-3 border-b-2 border-ink pb-4">
      <div class="flex items-baseline gap-3">
        <h1 class="text-2xl font-black tracking-tight">{{ t('boards.title') }}</h1>
        <span class="font-mono text-[11px] uppercase tracking-widest text-steel">{{ t('boards.total', { n: projects.list.length }) }}</span>
      </div>
      <Btn v-if="!creating" @click="creating = true"><SvgIcon name="plus" :size="11" /> {{ t('boards.new') }}</Btn>
    </div>

    <!-- composer -->
    <form v-if="creating" class="mt-4 flex gap-2" @submit.prevent="create">
      <input
        v-model="name"
        :placeholder="t('boards.name')"
        maxlength="200"
        autofocus
        class="min-w-0 flex-1 border-2 border-ink bg-white px-3 py-2 text-sm font-semibold uppercase outline-none focus:border-signal"
      />
      <Btn :disabled="!name.trim()">{{ t('common.create') }}</Btn>
      <Btn variant="ghost" type="button" @click="((creating = false), (name = ''))">{{ t('common.cancel') }}</Btn>
    </form>

    <p v-if="projects.error" class="mt-4 border border-[#C92A2A] bg-[#C92A2A]/10 px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#C92A2A]">
      {{ displayError(projects.error) }}
    </p>

    <!-- grid -->
    <div v-if="projects.list.length" class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink
        v-for="p in projects.list"
        :key="p.id"
        :to="`/board/${p.id}`"
        class="group flex flex-col border border-ink/80 bg-white transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:border-ink hover:shadow-offset-sm"
      >
        <div class="flex items-start justify-between gap-2 border-b border-line px-4 py-3">
          <h2 class="text-sm font-black uppercase leading-snug tracking-tight group-hover:text-signal">
            {{ p.name }}
          </h2>
          <span
            class="shrink-0 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest"
            :class="p.role === 'owner' ? 'bg-signal text-white' : 'border border-line text-steel'"
          >
            {{ t('roles.' + p.role) }}
          </span>
        </div>
        <div class="mt-auto px-4 py-3">
          <p class="font-mono text-[10px] uppercase tracking-widest text-steel">
            {{ t('boards.tasks', { count: p.task_count, done: p.done_count }) }}
          </p>
          <!-- progress gauge -->
          <div class="mt-2 h-1.5 w-full border border-line">
            <div class="h-full bg-signal transition-all" :style="{ width: `${progress(p)}%` }"></div>
          </div>
          <p class="mt-2 font-mono text-[9px] uppercase tracking-widest text-steel/70">
            {{ t('boards.established', { date: p.created_at?.slice(0, 10) }) }}
          </p>
        </div>
      </RouterLink>
    </div>

    <!-- empty -->
    <div v-else-if="!projects.loading" class="mt-6 border border-dashed border-steel/60 p-10 text-center">
      <p class="font-mono text-[11px] uppercase tracking-widest text-steel">{{ t('boards.emptyTitle') }}</p>
      <p class="mt-2 text-sm text-steel">{{ t('boards.emptyText') }}</p>
      <Btn class="mt-4" @click="creating = true"><SvgIcon name="plus" :size="11" /> {{ t('boards.new') }}</Btn>
    </div>

    <p v-else class="mt-6 font-mono text-[11px] uppercase tracking-widest text-steel">{{ t('boards.loading') }}</p>
  </main>
</template>
