<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { displayName } from '../lib/format'
import { LOCALES, applyLocale } from '../i18n'

const { t, locale } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const switching = ref(false)

async function chooseLanguage(code) {
  if (code === locale.value || switching.value) return
  switching.value = true
  try {
    await auth.updateLocale(code)
  } catch {
    applyLocale(code) // keep the local switch even if the profile save failed
  } finally {
    switching.value = false
  }
}

function logout() {
  auth.logout()
  router.push('/')
}
</script>

<template>
  <header class="border-b-2 border-ink bg-paper">
    <div class="flex h-14 items-center justify-between px-3">
      <RouterLink to="/boards" class="flex items-center gap-2">
        <img src="/icon.png" alt="" width="28" height="28" class="h-7 w-7" />
        <span class="text-sm font-black tracking-tight">BOARDLY</span>
      </RouterLink>
      <div class="flex items-center gap-3">
        <span class="hidden font-mono text-[11px] uppercase tracking-widest text-steel sm:inline">
          {{ displayName(auth.user) }}
        </span>
        <div class="flex items-center border border-line" :title="t('header.language')">
          <button
            v-for="item in LOCALES"
            :key="item.code"
            type="button"
            class="px-1.5 py-1 font-mono text-[10px] uppercase tracking-widest disabled:cursor-default disabled:opacity-60"
            :class="locale === item.code ? 'bg-ink text-paper' : 'text-steel hover:text-ink'"
            :disabled="switching"
            @click="chooseLanguage(item.code)"
          >
            {{ item.code }}
          </button>
        </div>
        <RouterLink
          to="/guide"
          class="flex items-center gap-1 border border-transparent px-2 py-1 font-mono text-[11px] uppercase tracking-widest text-steel hover:border-ink hover:text-ink"
        >
          <SvgIcon name="lines" :size="12" /> {{ t('guide.link') }}
        </RouterLink>
        <RouterLink
          to="/about"
          class="flex items-center gap-1 border border-transparent px-2 py-1 font-mono text-[11px] uppercase tracking-widest text-steel hover:border-ink hover:text-ink"
        >
          <SvgIcon name="user" :size="12" /> {{ t('about.link') }}
        </RouterLink>
        <RouterLink
          to="/settings"
          class="flex items-center gap-1 border border-transparent px-2 py-1 font-mono text-[11px] uppercase tracking-widest text-steel hover:border-ink hover:text-ink"
        >
          <SvgIcon name="settings" :size="12" /> {{ t('header.settings') }}
        </RouterLink>
        <Btn v-if="!auth.isTelegram" variant="ghost" @click="logout">
          <SvgIcon name="logout" :size="12" /> {{ t('header.exit') }}
        </Btn>
      </div>
    </div>
  </header>
</template>
