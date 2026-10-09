<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/client'
import CfdChart from '../components/CfdChart.vue'
import { fmtDeadline } from '../lib/format'
import { displayError, stageName } from '../lib/messages'
import { complexityLabel } from '../lib/complexity'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()

const PERIODS = [14, 30, 90, 0] // 0 = since the board was created

const days = ref(30)
const data = ref(null)
const loading = ref(false)
const error = ref('')
const view = ref('chart') // 'chart' | 'table'

const projectId = computed(() => route.params.id)

async function load(initial = false) {
  loading.value = true
  error.value = ''
  try {
    const { data: body } = await api.get(`/projects/${projectId.value}/metrics`, {
      params: { days: days.value, tz_offset: new Date().getTimezoneOffset() },
    })
    data.value = body
  } catch (e) {
    const status = e?.response?.status
    if (initial && (status === 403 || status === 404)) {
      router.replace('/boards')
      return
    }
    error.value = e?.response?.data?.detail || 'errors.loadMetrics'
  } finally {
    loading.value = false
  }
}

onMounted(() => load(true))
watch(days, () => load())
watch(projectId, () => {
  if (route.name === 'metrics') load(true)
})

const numberFmt = computed(() => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }))

function fmtDays(value) {
  if (value === null || value === undefined) return t('metrics.none')
  return t('metrics.daysValue', { n: numberFmt.value.format(value) })
}

function bandLabel(band) {
  const name = stageName(band.name)
  return band.lane ? `${name} · ${t(`stage.${band.lane}`)}` : name
}

const bands = computed(() => (data.value?.cfd_bands || []).map((b) => ({ ...b, label: bandLabel(b) })))
const points = computed(() => data.value?.cfd || [])
const tableRows = computed(() => [...points.value].reverse())

const durationTiles = computed(() => {
  if (!data.value) return []
  return [
    { key: 'cycle', title: t('metrics.cycleTime'), hint: t('metrics.cycleHint'), stats: data.value.cycle_time },
    { key: 'ttm', title: t('metrics.ttm'), hint: t('metrics.ttmHint'), stats: data.value.time_to_market },
  ]
})
</script>

<template>
  <div class="min-h-[calc(100dvh-3.5rem-env(safe-area-inset-top))]">
    <!-- topbar -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line bg-paper px-4 py-2.5">
      <RouterLink
        :to="{ name: 'board', params: { id: projectId } }"
        class="flex items-center gap-1 font-mono text-[11px] uppercase tracking-widest text-steel hover:text-ink"
      >
        <SvgIcon name="back" :size="12" /> {{ t('metrics.back') }}
      </RouterLink>
      <span class="hidden h-4 w-px bg-line sm:block"></span>
      <h1 class="min-w-0 truncate text-base font-black uppercase tracking-tight">{{ data?.project_name || '' }}</h1>
      <span class="bg-ink px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-paper">{{ t('metrics.badge') }}</span>

      <div class="ml-auto flex flex-wrap items-center gap-2" role="group" :aria-label="t('metrics.period')">
        <span class="hidden font-mono text-[10px] uppercase tracking-widest text-steel sm:inline">{{ t('metrics.period') }}</span>
        <div class="flex flex-wrap border border-ink">
          <button
            v-for="p in PERIODS"
            :key="p"
            type="button"
            class="min-h-11 border-r border-ink px-3 font-mono text-[10px] uppercase tracking-widest last:border-r-0"
            :class="days === p ? 'bg-ink text-paper' : 'bg-white text-ink hover:bg-paper'"
            :aria-pressed="days === p"
            @click="days = p"
          >
            {{ p ? t('metrics.days', { n: p }) : t('metrics.all') }}
          </button>
        </div>
      </div>
    </div>

    <p
      v-if="error"
      class="flex items-center justify-between gap-2 border-b border-[#C92A2A] bg-[#C92A2A]/10 px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest text-[#C92A2A]"
    >
      <span>{{ displayError(error) }}</span>
      <button class="underline" @click="load()">{{ t('common.retry') }}</button>
    </p>

    <main v-if="!data && loading" class="flex h-64 items-center justify-center">
      <span class="font-mono text-xs uppercase tracking-widest text-steel">{{ t('metrics.loading') }}</span>
    </main>

    <main v-else-if="data" class="mx-auto max-w-6xl space-y-4 p-4" :class="loading ? 'opacity-60' : ''">
      <p class="font-mono text-[10px] uppercase tracking-widest text-steel">
        {{ fmtDeadline(data.period_start) }} — {{ fmtDeadline(data.period_end) }}
      </p>

      <!-- KPI tiles -->
      <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div class="border-2 border-ink bg-white p-3">
          <div class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('metrics.throughput') }}</div>
          <div class="mt-1 text-3xl font-black tabular-nums">{{ data.throughput }}</div>
          <div class="mt-1 text-[11px] text-steel">{{ t('metrics.throughputHint') }}</div>
        </div>
        <div class="border-2 border-ink bg-white p-3">
          <div class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('metrics.wip') }}</div>
          <div class="mt-1 text-3xl font-black tabular-nums">{{ data.wip }}</div>
          <div class="mt-1 text-[11px] text-steel">{{ t('metrics.wipHint') }}</div>
        </div>
        <div v-for="tile in durationTiles" :key="tile.key" class="col-span-2 border-2 border-ink bg-white p-3 sm:col-span-1">
          <div class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ tile.title }}</div>
          <div class="mt-1 flex items-baseline gap-1.5">
            <span class="text-3xl font-black">{{ fmtDays(tile.stats.median) }}</span>
            <span class="font-mono text-[10px] uppercase text-steel">{{ t('metrics.median') }}</span>
          </div>
          <div class="mt-1 flex gap-3 font-mono text-[10px] uppercase text-steel">
            <span>{{ t('metrics.avg') }} <b class="text-ink">{{ fmtDays(tile.stats.avg) }}</b></span>
            <span>{{ t('metrics.p85') }} <b class="text-ink">{{ fmtDays(tile.stats.p85) }}</b></span>
            <span>n <b class="text-ink">{{ tile.stats.count }}</b></span>
          </div>
          <div class="mt-1 text-[11px] text-steel">{{ tile.hint }}</div>
        </div>
      </section>

      <!-- CFD -->
      <section class="border-2 border-ink bg-white">
        <header class="flex flex-wrap items-center justify-between gap-2 border-b-2 border-ink px-3 py-2">
          <h2 class="font-mono text-[11px] font-bold uppercase tracking-widest">{{ t('metrics.cfd') }}</h2>
          <div class="flex border border-ink">
            <button
              v-for="v in ['chart', 'table']"
              :key="v"
              type="button"
              class="border-r border-ink px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest last:border-r-0"
              :class="view === v ? 'bg-ink text-paper' : 'bg-white text-ink hover:bg-paper'"
              :aria-pressed="view === v"
              @click="view = v"
            >
              {{ t(`metrics.${v}`) }}
            </button>
          </div>
        </header>
        <div class="min-w-0 p-3">
          <p class="mb-3 text-[12px] text-steel">{{ t('metrics.cfdHint') }}</p>
          <CfdChart v-if="view === 'chart'" :bands="bands" :points="points" :total-label="t('metrics.total')" />
          <div v-else class="max-h-96 overflow-auto border border-line">
            <table class="w-full border-collapse text-[12px]">
              <thead class="sticky top-0 bg-paper">
                <tr>
                  <th class="px-2 py-1.5 text-left font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('metrics.date') }}</th>
                  <th
                    v-for="b in bands"
                    :key="b.key"
                    class="whitespace-nowrap px-2 py-1.5 text-right font-mono text-[10px] uppercase tracking-widest text-steel"
                  >
                    {{ b.label }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in tableRows" :key="p.day" class="border-t border-line">
                  <td class="whitespace-nowrap px-2 py-1 font-mono text-[11px] uppercase">{{ fmtDeadline(p.day) }}</td>
                  <td v-for="b in bands" :key="b.key" class="px-2 py-1 text-right font-mono tabular-nums">
                    {{ p.counts[b.key] || 0 }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- by complexity -->
      <section class="border-2 border-ink bg-white">
        <header class="border-b-2 border-ink px-3 py-2">
          <h2 class="font-mono text-[11px] font-bold uppercase tracking-widest">{{ t('metrics.byComplexity') }}</h2>
        </header>
        <p v-if="!data.throughput" class="px-3 py-4 text-[12px] text-steel">{{ t('metrics.emptyDone') }}</p>
        <div v-else>
          <div class="divide-y divide-line md:hidden">
            <div
              v-for="row in data.by_complexity"
              :key="row.complexity"
              class="px-3 py-3"
              :class="row.completed ? '' : 'text-steel'"
            >
              <p class="text-sm font-semibold">{{ complexityLabel(row.complexity) }}</p>
              <dl class="mt-2 grid grid-cols-3 gap-2 font-mono text-[10px] uppercase tracking-widest text-steel">
                <div>
                  <dt>{{ t('metrics.completed') }}</dt>
                  <dd class="mt-0.5 text-ink tabular-nums">{{ row.completed }}</dd>
                </div>
                <div>
                  <dt>{{ t('metrics.avgCycle') }}</dt>
                  <dd class="mt-0.5 text-ink tabular-nums">{{ fmtDays(row.cycle_time.avg) }}</dd>
                </div>
                <div>
                  <dt>{{ t('metrics.avgTtm') }}</dt>
                  <dd class="mt-0.5 text-ink tabular-nums">{{ fmtDays(row.time_to_market.avg) }}</dd>
                </div>
              </dl>
            </div>
          </div>
          <div class="hidden overflow-x-auto md:block">
            <table class="w-full border-collapse text-[12px]">
              <thead>
                <tr class="bg-paper">
                  <th class="px-3 py-1.5 text-left font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('metrics.complexity') }}</th>
                  <th class="px-3 py-1.5 text-right font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('metrics.completed') }}</th>
                  <th class="px-3 py-1.5 text-right font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('metrics.avgCycle') }}</th>
                  <th class="px-3 py-1.5 text-right font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('metrics.avgTtm') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in data.by_complexity"
                  :key="row.complexity"
                  class="border-t border-line"
                  :class="row.completed ? '' : 'text-steel'"
                >
                  <td class="px-3 py-1.5 font-semibold">{{ complexityLabel(row.complexity) }}</td>
                  <td class="px-3 py-1.5 text-right font-mono tabular-nums">{{ row.completed }}</td>
                  <td class="px-3 py-1.5 text-right font-mono tabular-nums">{{ fmtDays(row.cycle_time.avg) }}</td>
                  <td class="px-3 py-1.5 text-right font-mono tabular-nums">{{ fmtDays(row.time_to_market.avg) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <p class="text-[11px] text-steel">{{ t('metrics.legacyNote') }}</p>
    </main>
  </div>
</template>
