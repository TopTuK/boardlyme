<script setup>
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const REPO_URL = 'https://github.com/TopTuK/boardlyme'
const AUTHOR_URL = 'https://s-sidorov.ru'

const { t, tm } = useI18n()
const auth = useAuthStore()
</script>

<template>
  <div class="min-h-dvh bg-paper">
    <!-- top bar -->
    <header class="safe-pt safe-px border-b-2 border-ink">
      <div class="mx-auto flex min-h-14 max-w-6xl items-center justify-between gap-2 px-4 py-2">
        <RouterLink to="/" class="flex items-center gap-2">
          <img src="/icon.png" alt="" width="32" height="32" class="h-8 w-8" />
          <span class="text-base font-black tracking-tight">BOARDLY</span>
        </RouterLink>
        <div class="flex items-center gap-3">
          <RouterLink
            to="/"
            class="font-mono text-[11px] uppercase tracking-widest text-steel hover:text-ink"
          >
            {{ t('about.back') }}
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
        <p class="font-mono text-[11px] uppercase tracking-[0.25em] text-signal">{{ t('about.badge') }}</p>
        <h1 class="mt-4 text-4xl font-black leading-[0.95] tracking-tight sm:text-5xl">
          {{ t('about.title') }}
        </h1>
        <p class="mt-6 max-w-2xl text-sm leading-relaxed text-steel">{{ t('about.intro') }}</p>
      </div>
    </section>

    <!-- how it is built + open source -->
    <section class="border-b-2 border-ink">
      <div class="mx-auto grid max-w-6xl gap-6 px-4 py-14 lg:grid-cols-2">
        <div class="border-2 border-ink bg-white p-6 shadow-offset sm:p-8">
          <h2 class="text-lg font-black uppercase tracking-tight">{{ t('about.builtTitle') }}</h2>
          <ul class="mt-4 space-y-3">
            <li
              v-for="item in tm('about.builtItems')"
              :key="item"
              class="flex gap-3 text-[13px] leading-relaxed text-steel"
            >
              <span class="mt-0.5 font-mono text-xs font-bold text-signal">▸</span>
              {{ item }}
            </li>
          </ul>
        </div>
        <div class="flex flex-col border-2 border-ink bg-ink p-6 text-paper shadow-offset sm:p-8">
          <h2 class="text-lg font-black uppercase tracking-tight">{{ t('about.sourceTitle') }}</h2>
          <p class="mt-4 text-[13px] leading-relaxed text-paper/70">{{ t('about.sourceText') }}</p>
          <a
            :href="REPO_URL"
            target="_blank"
            rel="noopener"
            class="mt-6 inline-flex w-fit items-center gap-2 bg-paper px-5 py-3 font-mono text-xs uppercase tracking-widest text-ink transition-colors hover:bg-signal hover:text-white"
          >
            <SvgIcon name="share" :size="12" /> {{ t('about.sourceCta') }}
          </a>
        </div>
      </div>
    </section>

    <!-- author -->
    <section class="border-b-2 border-ink">
      <div class="mx-auto max-w-6xl px-4 py-14">
        <h2 class="border-b border-line pb-4 text-2xl font-black tracking-tight">{{ t('about.authorTitle') }}</h2>
        <div class="mt-8 flex flex-col gap-6 border-2 border-ink bg-white p-6 shadow-offset sm:flex-row sm:p-8">
          <div class="flex h-20 w-20 shrink-0 items-center justify-center border-2 border-ink bg-paper font-mono text-2xl font-black">
            SS
          </div>
          <div>
            <h3 class="text-xl font-black uppercase tracking-tight">{{ t('about.authorName') }}</h3>
            <p class="mt-1 font-mono text-[10px] uppercase tracking-widest text-signal">{{ t('about.authorRole') }}</p>
            <p class="mt-4 max-w-2xl text-[13px] leading-relaxed text-steel">{{ t('about.authorBio') }}</p>
            <a
              :href="AUTHOR_URL"
              target="_blank"
              rel="noopener"
              class="mt-6 inline-flex items-center gap-2 border-2 border-ink px-5 py-3 font-mono text-xs uppercase tracking-widest transition-colors hover:bg-ink hover:text-paper"
            >
              <SvgIcon name="user" :size="12" /> {{ t('about.authorCta') }}
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- back -->
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
          {{ t('about.back') }}
        </RouterLink>
      </div>
    </section>

    <footer class="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-2 px-4 py-6">
      <span class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('landing.copyright') }}</span>
    </footer>
  </div>
</template>
