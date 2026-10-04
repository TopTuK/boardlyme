<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { LOCALES } from '../i18n'
import { displayError } from '../lib/messages'

const { t, locale } = useI18n()
const auth = useAuthStore()
const error = ref('')
const saving = ref(false)

async function choose(code) {
  if (code === locale.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    await auth.updateLocale(code)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'errors.saveSettings'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="mx-auto max-w-6xl px-4 py-8">
    <div class="border-b-2 border-ink pb-4">
      <RouterLink
        to="/boards"
        class="flex items-center gap-1 font-mono text-[11px] uppercase tracking-widest text-steel hover:text-ink"
      >
        <SvgIcon name="back" :size="12" /> {{ t('settings.back') }}
      </RouterLink>
      <h1 class="mt-3 text-2xl font-black tracking-tight">{{ t('settings.title') }}</h1>
    </div>

    <section class="mt-6 max-w-lg border border-ink bg-white">
      <header class="border-b border-line px-4 py-3">
        <h2 class="font-mono text-[11px] font-bold uppercase tracking-widest text-steel">{{ t('settings.language') }}</h2>
        <p class="mt-2 text-[13px] leading-relaxed text-steel">{{ t('settings.hint') }}</p>
      </header>
      <div class="grid gap-px bg-line sm:grid-cols-2">
        <button
          v-for="item in LOCALES"
          :key="item.code"
          type="button"
          class="flex items-center justify-between bg-paper px-4 py-4 text-left transition-colors hover:bg-white disabled:opacity-60"
          :class="locale === item.code ? 'bg-ink text-paper hover:bg-ink' : ''"
          :disabled="saving"
          @click="choose(item.code)"
        >
          <span>
            <span class="block font-mono text-[10px] uppercase tracking-widest" :class="locale === item.code ? 'text-paper/70' : 'text-steel'">
              {{ item.code }}
            </span>
            <span class="mt-1 block text-sm font-black uppercase tracking-tight">{{ item.native }}</span>
          </span>
          <SvgIcon v-if="locale === item.code" name="check" :size="14" />
        </button>
      </div>
    </section>

    <p
      v-if="error"
      class="mt-4 max-w-lg border border-[#C92A2A] bg-[#C92A2A]/10 px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#C92A2A]"
    >
      {{ displayError(error) }}
    </p>
  </main>
</template>
