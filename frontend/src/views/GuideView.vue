<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import CfdChart from '../components/CfdChart.vue'
import { stageName } from '../lib/messages'

const { t } = useI18n()
const auth = useAuthStore()

// Sample flow for the step 4 figure: two weeks of a board that keeps
// delivering, ending today.
const SAMPLE = {
  Backlog: [4, 4, 4, 5, 4, 4, 5, 4, 4, 4, 5, 4, 4, 5],
  ToDo: [2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 3, 3, 4, 3],
  Active: [1, 2, 2, 2, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2],
  Done: [0, 0, 1, 1, 2, 3, 3, 4, 5, 6, 6, 7, 8, 9],
}

function isoDaysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return [d.getFullYear(), d.getMonth() + 1, d.getDate()].map((v) => String(v).padStart(2, '0')).join('-')
}

const sampleBands = computed(() => Object.keys(SAMPLE).map((key) => ({ key, label: stageName(key) })))
const samplePoints = SAMPLE.Done.map((_, i) => ({
  day: isoDaysAgo(SAMPLE.Done.length - 1 - i),
  counts: Object.fromEntries(Object.entries(SAMPLE).map(([key, values]) => [key, values[i]])),
}))

const metricTerms = computed(() =>
  ['Cycle', 'Ttm', 'Cfd', 'Levels'].map((k) => ({
    title: t(`guide.step4${k}Title`),
    text: t(`guide.step4${k}Text`),
  }))
)
</script>

<template>
  <div class="min-h-screen bg-paper">
    <!-- top bar -->
    <header class="border-b-2 border-ink">
      <div class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <RouterLink to="/" class="flex items-center gap-2">
          <img src="/icon.png" alt="" width="32" height="32" class="h-8 w-8" />
          <span class="text-base font-black tracking-tight">BOARDLY</span>
        </RouterLink>
        <div class="flex items-center gap-3">
          <RouterLink
            to="/"
            class="font-mono text-[11px] uppercase tracking-widest text-steel hover:text-ink"
          >
            {{ t('guide.back') }}
          </RouterLink>
          <RouterLink
            v-if="!auth.isAuthenticated"
            to="/login"
            class="border-2 border-ink px-4 py-2 font-mono text-[11px] uppercase tracking-widest hover:bg-ink hover:text-paper"
          >
            {{ t('landing.login') }}
          </RouterLink>
        </div>
      </div>
    </header>

    <!-- heading -->
    <section class="border-b-2 border-ink bg-blueprint">
      <div class="mx-auto max-w-6xl px-4 py-14">
        <p class="font-mono text-[11px] uppercase tracking-[0.25em] text-signal">{{ t('guide.badge') }}</p>
        <h1 class="mt-4 text-4xl font-black leading-[0.95] tracking-tight sm:text-5xl">
          {{ t('guide.title') }}
        </h1>
        <p class="mt-6 max-w-2xl text-sm leading-relaxed text-steel">{{ t('guide.intro') }}</p>
      </div>
    </section>

    <!-- steps -->
    <section class="border-b-2 border-ink">
      <div class="mx-auto max-w-6xl space-y-6 px-4 py-14">
        <article class="border-2 border-ink bg-white shadow-offset">
          <div class="grid lg:grid-cols-2 lg:items-center">
            <div class="grid gap-4 p-6 sm:grid-cols-[auto_1fr] sm:p-8">
              <span class="font-mono text-2xl font-black text-signal">{{ t('guide.step1No') }}</span>
              <div>
                <h2 class="text-lg font-black uppercase tracking-tight">{{ t('guide.step1Title') }}</h2>
                <p class="mt-3 text-[13px] leading-relaxed text-steel">{{ t('guide.step1Text') }}</p>
              </div>
            </div>
            <figure class="relative border-t-2 border-ink lg:border-l-2 lg:border-t-0">
              <img
                src="/guide-context.jpg"
                :alt="t('guide.step1Alt')"
                width="1600"
                height="1073"
                class="aspect-[3/2] w-full object-cover"
              />
              <figcaption class="absolute left-3 top-3 bg-paper px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-steel">
                {{ t('guide.step1Fig') }}
              </figcaption>
            </figure>
          </div>
        </article>
        <article class="border-2 border-ink bg-white shadow-offset">
          <div class="grid lg:grid-cols-2 lg:items-center">
            <div class="grid gap-4 p-6 sm:grid-cols-[auto_1fr] sm:p-8">
              <span class="font-mono text-2xl font-black text-signal">{{ t('guide.step2No') }}</span>
              <div>
                <h2 class="text-lg font-black uppercase tracking-tight">{{ t('guide.step2Title') }}</h2>
                <p class="mt-3 text-[13px] leading-relaxed text-steel">{{ t('guide.step2Text') }}</p>
              </div>
            </div>
            <figure class="relative border-t-2 border-ink lg:border-l-2 lg:border-t-0">
              <img
                src="/guide-flow.jpg"
                :alt="t('guide.step2Alt')"
                width="1600"
                height="1073"
                class="aspect-[3/2] w-full object-cover"
              />
              <figcaption class="absolute left-3 top-3 bg-paper px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-steel">
                {{ t('guide.step2Fig') }}
              </figcaption>
            </figure>
          </div>
        </article>
        <article class="border-2 border-ink bg-white shadow-offset">
          <div class="grid lg:grid-cols-2 lg:items-center">
            <div class="grid gap-4 p-6 sm:grid-cols-[auto_1fr] sm:p-8">
              <span class="font-mono text-2xl font-black text-signal">{{ t('guide.step3No') }}</span>
              <div>
                <h2 class="text-lg font-black uppercase tracking-tight">{{ t('guide.step3Title') }}</h2>
                <p class="mt-3 text-[13px] leading-relaxed text-steel">{{ t('guide.step3Text') }}</p>
              </div>
            </div>
            <figure class="relative border-t-2 border-ink lg:border-l-2 lg:border-t-0">
              <img
                src="/guide-tasks.jpg"
                :alt="t('guide.step3Alt')"
                width="1600"
                height="1073"
                class="aspect-[3/2] w-full object-cover"
              />
              <figcaption class="absolute left-3 top-3 bg-paper px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-steel">
                {{ t('guide.step3Fig') }}
              </figcaption>
            </figure>
          </div>
        </article>
        <article class="border-2 border-ink bg-white shadow-offset">
          <div class="grid lg:grid-cols-2 lg:items-center">
            <div class="grid gap-4 p-6 sm:grid-cols-[auto_1fr] sm:p-8">
              <span class="font-mono text-2xl font-black text-signal">{{ t('guide.step4No') }}</span>
              <div>
                <h2 class="text-lg font-black uppercase tracking-tight">{{ t('guide.step4Title') }}</h2>
                <p class="mt-3 text-[13px] leading-relaxed text-steel">{{ t('guide.step4Text') }}</p>
                <dl class="mt-4 space-y-3 border-l-2 border-ink pl-4">
                  <div v-for="term in metricTerms" :key="term.title">
                    <dt class="font-mono text-[11px] font-bold uppercase tracking-widest text-ink">{{ term.title }}</dt>
                    <dd class="mt-0.5 text-[13px] leading-relaxed text-steel">{{ term.text }}</dd>
                  </div>
                </dl>
                <p class="mt-4 text-[12px] leading-relaxed text-steel">{{ t('guide.step4Note') }}</p>
              </div>
            </div>
            <!-- min-w-0: let the grid track shrink so the chart measures its real width -->
            <figure class="relative min-w-0 border-t-2 border-ink px-4 pb-4 pt-10 lg:border-l-2 lg:border-t-0">
              <CfdChart :bands="sampleBands" :points="samplePoints" :total-label="t('metrics.total')" />
              <figcaption class="absolute left-3 top-3 bg-paper px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-steel">
                {{ t('guide.step4Fig') }}
              </figcaption>
            </figure>
          </div>
        </article>
      </div>
    </section>

    <!-- cta -->
    <section class="border-b-2 border-ink">
      <div class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-10">
        <RouterLink
          to="/boards"
          class="bg-ink px-5 py-3 font-mono text-xs uppercase tracking-widest text-paper shadow-offset transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-signal"
        >
          {{ t('guide.openApp') }}
        </RouterLink>
        <RouterLink
          to="/"
          class="font-mono text-xs uppercase tracking-widest text-steel hover:text-ink"
        >
          {{ t('guide.back') }}
        </RouterLink>
      </div>
    </section>

    <footer class="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-2 px-4 py-6">
      <span class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('landing.copyright') }}</span>
    </footer>
  </div>
</template>
