<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { stageName } from '../lib/messages'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const features = computed(() => [
  { no: '01', title: t('landing.f1Title'), text: t('landing.f1Text') },
  { no: '02', title: t('landing.f2Title'), text: t('landing.f2Text') },
  { no: '03', title: t('landing.f3Title'), text: t('landing.f3Text') },
  { no: '04', title: t('landing.f4Title'), text: t('landing.f4Text') },
  { no: '05', title: t('landing.f5Title'), text: t('landing.f5Text') },
])

const mock = computed(() => [
  { name: stageName('ToDo'), items: [{ t: t('landing.mock1') }, { t: t('landing.mock2'), accent: true }, { t: t('landing.mock3') }] },
  { name: stageName('Active'), items: [{ t: t('landing.mock4') }, { t: t('landing.mock5') }] },
  { name: stageName('Done'), items: [{ t: t('landing.mock6') }] },
])
</script>

<template>
  <div class="min-h-screen bg-paper">
    <!-- top bar -->
    <header class="border-b-2 border-ink">
      <div class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <div class="flex items-center gap-2">
          <img src="/icon.png" alt="" width="32" height="32" class="h-8 w-8" />
          <span class="text-base font-black tracking-tight">BOARDLY</span>
        </div>
        <RouterLink
          v-if="!auth.isAuthenticated"
          to="/login"
          class="border-2 border-ink px-4 py-2 font-mono text-[11px] uppercase tracking-widest hover:bg-ink hover:text-paper"
        >
          {{ t('landing.login') }}
        </RouterLink>
      </div>
    </header>

    <!-- hero -->
    <section class="border-b-2 border-ink bg-blueprint">
      <div class="mx-auto grid max-w-6xl gap-12 px-4 py-16 lg:grid-cols-2 lg:py-24">
        <div>
          <p class="font-mono text-[11px] uppercase tracking-[0.25em] text-signal">
            {{ t('landing.spec') }}
          </p>
          <h1 class="mt-4 text-5xl font-black leading-[0.95] tracking-tight sm:text-6xl">
            {{ t('landing.heroTitle1') }}<br />{{ t('landing.heroTitle2') }}
          </h1>
          <p class="mt-6 max-w-md text-sm leading-relaxed text-steel">
            {{ t('landing.heroText') }}
          </p>
          <div class="mt-8 flex flex-wrap gap-3">
            <RouterLink
              v-if="!auth.isAuthenticated"
              to="/login"
              class="bg-ink px-5 py-3 font-mono text-xs uppercase tracking-widest text-paper shadow-offset transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-signal"
            >
              {{ t('landing.loginTelegram') }}
            </RouterLink>
            <RouterLink
              to="/boards"
              class="border-2 border-ink px-5 py-3 font-mono text-xs uppercase tracking-widest transition-colors hover:bg-ink hover:text-paper"
            >
              {{ t('landing.openApp') }}
            </RouterLink>
          </div>
        </div>

        <!-- mock board -->
        <div class="relative self-center">
          <div class="grid grid-cols-3 gap-2 border-2 border-ink bg-paper p-2 shadow-offset sm:gap-3 sm:p-3">
            <div v-for="col in mock" :key="col.name" class="border border-line bg-white">
              <div class="flex items-center justify-between border-b border-line px-2 py-1.5">
                <span class="font-mono text-[10px] font-bold uppercase tracking-widest text-steel">{{ col.name }}</span>
                <span class="font-mono text-[10px] text-steel">{{ col.items.length }}</span>
              </div>
              <div class="space-y-2 p-2">
                <div
                  v-for="item in col.items"
                  :key="item.t"
                  class="border px-2 py-1.5 text-[11px] font-semibold leading-snug"
                  :class="item.accent ? 'border-signal bg-signal/10' : 'border-line text-ink/80'"
                >
                  {{ item.t }}
                </div>
              </div>
            </div>
          </div>
          <span class="absolute -top-2.5 left-3 bg-paper px-1 font-mono text-[9px] uppercase tracking-widest text-steel">
            {{ t('landing.fig') }}
          </span>
          <span class="absolute -bottom-2.5 right-3 bg-paper px-1 font-mono text-[9px] uppercase tracking-widest text-steel">
            {{ t('landing.scale') }}
          </span>
        </div>
      </div>
    </section>

    <!-- shop plate -->
    <section class="border-b-2 border-ink">
      <div class="mx-auto max-w-6xl px-4 py-10">
        <figure class="relative">
          <img
            src="/hero-board.jpg"
            :alt="t('landing.figShop')"
            class="h-64 w-full border-2 border-ink object-cover object-[center_38%] sm:h-80 lg:h-[420px]"
          />
          <figcaption class="absolute -top-2.5 left-3 bg-paper px-1 font-mono text-[9px] uppercase tracking-widest text-steel">
            {{ t('landing.figShop') }}
          </figcaption>
        </figure>
      </div>
    </section>

    <!-- features -->
    <section class="border-b-2 border-ink">
      <div class="mx-auto max-w-6xl px-4 py-14">
        <div class="flex items-end justify-between border-b border-line pb-4">
          <h2 class="text-2xl font-black tracking-tight">{{ t('landing.capabilities') }}</h2>
          <span class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('landing.modules') }}</span>
        </div>
        <div class="mt-8 grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-3">
          <article v-for="f in features" :key="f.no" class="bg-paper p-6">
            <span class="font-mono text-xs font-bold text-signal">{{ f.no }}</span>
            <h3 class="mt-3 text-sm font-black uppercase tracking-wide">{{ f.title }}</h3>
            <p class="mt-2 text-[13px] leading-relaxed text-steel">{{ f.text }}</p>
          </article>
        </div>
      </div>
    </section>

    <!-- field kit -->
    <section class="border-b-2 border-ink">
      <figure class="relative">
        <img
          src="/desk-still.jpg"
          :alt="t('landing.figKit')"
          class="h-52 w-full object-cover object-[12%_72%] sm:h-64"
        />
        <figcaption
          class="absolute bottom-3 right-4 bg-paper px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-steel sm:bottom-auto sm:right-10 sm:top-1/2 sm:-translate-y-1/2 sm:bg-transparent sm:px-0 sm:text-[10px]"
        >
          {{ t('landing.figKit') }}
        </figcaption>
      </figure>
    </section>

    <!-- telegram strip -->
    <section class="border-b-2 border-ink bg-ink text-paper">
      <div class="mx-auto grid max-w-6xl gap-10 px-4 py-14 lg:grid-cols-[1fr_1.2fr]">
        <div>
          <p class="font-mono text-[11px] uppercase tracking-[0.25em] text-signal">{{ t('landing.telegramKicker') }}</p>
          <h2 class="mt-3 text-3xl font-black leading-tight tracking-tight">{{ t('landing.telegramTitle') }}</h2>
          <p class="mt-4 max-w-md text-sm leading-relaxed text-paper/70">
            {{ t('landing.telegramText') }}
          </p>
        </div>
        <ol class="space-y-3">
          <li class="flex gap-4 border border-paper/20 p-4">
            <span class="font-mono text-xs text-signal">01</span>
            <div>
              <p class="text-sm font-bold uppercase">{{ t('landing.step1Title') }}</p>
              <p class="mt-1 text-[13px] leading-relaxed text-paper/70">
                {{ t('landing.step1Text') }}
              </p>
            </div>
          </li>
          <li class="flex gap-4 border border-paper/20 p-4">
            <span class="font-mono text-xs text-signal">02</span>
            <div>
              <p class="text-sm font-bold uppercase">{{ t('landing.step2Title') }}</p>
              <p class="mt-1 text-[13px] leading-relaxed text-paper/70">
                {{ t('landing.step2Text') }}
              </p>
            </div>
          </li>
          <li class="flex gap-4 border border-paper/20 p-4">
            <span class="font-mono text-xs text-signal">03</span>
            <div>
              <p class="text-sm font-bold uppercase">{{ t('landing.step3Title') }}</p>
              <p class="mt-1 text-[13px] leading-relaxed text-paper/70">
                {{ t('landing.step3Text') }}
              </p>
            </div>
          </li>
        </ol>
      </div>
    </section>

    <footer class="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-2 px-4 py-6">
      <span class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('landing.copyright') }}</span>
    </footer>
  </div>
</template>
