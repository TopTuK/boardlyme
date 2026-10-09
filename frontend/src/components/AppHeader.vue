<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { displayName } from '../lib/format'
import { LOCALES, applyLocale } from '../i18n'
import OverflowMenu from './OverflowMenu.vue'

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

const localeSwitcherClass = (code) =>
  locale.value === code ? 'bg-ink text-paper' : 'text-steel hover:text-ink'
</script>

<template>
  <header class="safe-pt safe-px border-b-2 border-ink bg-paper">
    <div class="flex min-h-14 items-center justify-between gap-x-3 px-3 py-1">
      <RouterLink to="/boards" class="flex items-center gap-2">
        <img src="/icon.png" alt="" width="28" height="28" class="h-7 w-7" />
        <span class="text-sm font-black tracking-tight">BOARDLY</span>
      </RouterLink>

      <!-- desktop -->
      <div class="hidden items-center justify-end gap-x-3 md:flex">
        <span class="font-mono text-[11px] uppercase tracking-widest text-steel">
          {{ displayName(auth.user) }}
        </span>
        <div class="flex items-center border border-line" :title="t('header.language')">
          <button
            v-for="item in LOCALES"
            :key="item.code"
            type="button"
            class="px-1.5 py-1 font-mono text-[10px] uppercase tracking-widest disabled:cursor-default disabled:opacity-60"
            :class="localeSwitcherClass(item.code)"
            :disabled="switching"
            @click="chooseLanguage(item.code)"
          >
            {{ item.code }}
          </button>
        </div>
        <RouterLink
          to="/guide"
          :aria-label="t('guide.link')"
          class="flex items-center gap-1 border border-transparent px-2 py-1 font-mono text-[11px] uppercase tracking-widest text-steel hover:border-ink hover:text-ink"
        >
          <SvgIcon name="lines" :size="12" />
          <span>{{ t('guide.link') }}</span>
        </RouterLink>
        <RouterLink
          to="/about"
          :aria-label="t('about.link')"
          class="flex items-center gap-1 border border-transparent px-2 py-1 font-mono text-[11px] uppercase tracking-widest text-steel hover:border-ink hover:text-ink"
        >
          <SvgIcon name="user" :size="12" />
          <span>{{ t('about.link') }}</span>
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

      <!-- phone -->
      <OverflowMenu class="md:hidden" :label="t('common.more')">
        <template #default="{ close }">
          <div class="border-b border-line px-3 py-2">
            <p class="mb-1.5 font-mono text-[9px] uppercase tracking-widest text-steel">{{ t('header.language') }}</p>
            <div class="flex border border-line">
              <button
                v-for="item in LOCALES"
                :key="item.code"
                type="button"
                class="min-h-11 flex-1 font-mono text-[11px] uppercase tracking-widest disabled:cursor-default disabled:opacity-60"
                :class="localeSwitcherClass(item.code)"
                :disabled="switching"
                @click="chooseLanguage(item.code)"
              >
                {{ item.code }}
              </button>
            </div>
          </div>
          <RouterLink to="/guide" class="menu-item" @click="close">
            <SvgIcon name="lines" :size="12" /> {{ t('guide.link') }}
          </RouterLink>
          <RouterLink to="/about" class="menu-item" @click="close">
            <SvgIcon name="user" :size="12" /> {{ t('about.link') }}
          </RouterLink>
          <RouterLink to="/settings" class="menu-item" @click="close">
            <SvgIcon name="settings" :size="12" /> {{ t('header.settings') }}
          </RouterLink>
          <button v-if="!auth.isTelegram" type="button" class="menu-item" @click="(close(), logout())">
            <SvgIcon name="logout" :size="12" /> {{ t('header.exit') }}
          </button>
        </template>
      </OverflowMenu>
    </div>
  </header>
</template>
