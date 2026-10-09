<script setup>
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
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
        <article class="grid gap-4 border-2 border-ink bg-white p-6 shadow-offset sm:grid-cols-[auto_1fr] sm:p-8">
          <span class="font-mono text-2xl font-black text-signal">{{ t('guide.step1No') }}</span>
          <div>
            <h2 class="text-lg font-black uppercase tracking-tight">{{ t('guide.step1Title') }}</h2>
            <p class="mt-3 max-w-2xl text-[13px] leading-relaxed text-steel">{{ t('guide.step1Text') }}</p>
          </div>
        </article>
        <article class="grid gap-4 border-2 border-ink bg-white p-6 shadow-offset sm:grid-cols-[auto_1fr] sm:p-8">
          <span class="font-mono text-2xl font-black text-signal">{{ t('guide.step2No') }}</span>
          <div>
            <h2 class="text-lg font-black uppercase tracking-tight">{{ t('guide.step2Title') }}</h2>
            <p class="mt-3 max-w-2xl text-[13px] leading-relaxed text-steel">{{ t('guide.step2Text') }}</p>
          </div>
        </article>
        <article class="grid gap-4 border-2 border-ink bg-white p-6 shadow-offset sm:grid-cols-[auto_1fr] sm:p-8">
          <span class="font-mono text-2xl font-black text-signal">{{ t('guide.step3No') }}</span>
          <div>
            <h2 class="text-lg font-black uppercase tracking-tight">{{ t('guide.step3Title') }}</h2>
            <p class="mt-3 max-w-2xl text-[13px] leading-relaxed text-steel">{{ t('guide.step3Text') }}</p>
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
