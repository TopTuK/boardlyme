<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { LOCALES } from '../i18n'
import { startGoogleAuth } from '../lib/google'
import { displayError } from '../lib/messages'

const { t, locale } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const error = ref('')
const saving = ref(false)
const linkError = ref('')
const linkOk = ref('')
const widgetHost = ref(null)

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

function mountTelegramLinkWidget() {
  const botUsername = auth.meta?.bot_username
  if (!botUsername || auth.user?.telegram_linked || !widgetHost.value || widgetHost.value.childElementCount) return
  const script = document.createElement('script')
  script.src = 'https://telegram.org/js/telegram-widget.js?22'
  script.async = true
  script.setAttribute('data-telegram-login', botUsername)
  script.setAttribute('data-size', 'medium')
  script.setAttribute('data-userpic', 'false')
  script.setAttribute('data-auth-url', `${window.location.origin}/settings`)
  widgetHost.value.appendChild(script)
}

function linkGoogle() {
  startGoogleAuth(auth.meta.google_client_id, { mode: 'link' })
}

onMounted(async () => {
  // Return from the Telegram Login Widget: the signed payload rides the query string.
  const query = window.location.search
  if (query.includes('hash=') && query.includes('id=')) {
    router.replace('/settings')
    try {
      await auth.linkTelegram(query.slice(1))
      linkOk.value = 'settings.telegramLinkedOk'
    } catch (e) {
      linkError.value = e?.response?.data?.detail || e?.message || 'errors.authFailed'
    }
  }
  mountTelegramLinkWidget()
})
</script>

<template>
  <main class="mx-auto max-w-6xl px-4 py-8 safe-px">
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

    <section class="mt-6 max-w-lg border border-ink bg-white">
      <header class="border-b border-line px-4 py-3">
        <h2 class="font-mono text-[11px] font-bold uppercase tracking-widest text-steel">{{ t('settings.accounts') }}</h2>
        <p class="mt-2 text-[13px] leading-relaxed text-steel">{{ t('settings.accountsHint') }}</p>
      </header>
      <div class="divide-y divide-line">
        <div class="flex items-center justify-between gap-3 bg-paper px-4 py-4">
          <span>
            <span class="block text-sm font-black uppercase tracking-tight">Telegram</span>
            <span class="mt-1 block font-mono text-[10px] uppercase tracking-widest text-steel">
              {{ auth.user?.telegram_linked ? t('settings.linked') : t('settings.notLinked') }}
            </span>
          </span>
          <SvgIcon v-if="auth.user?.telegram_linked" name="check" :size="14" />
          <div v-else-if="auth.meta?.bot_username" ref="widgetHost"></div>
        </div>
        <div class="flex items-center justify-between gap-3 bg-paper px-4 py-4">
          <span>
            <span class="block text-sm font-black uppercase tracking-tight">Google</span>
            <span class="mt-1 block font-mono text-[10px] uppercase tracking-widest text-steel">
              {{ auth.user?.google_linked ? auth.user?.email || t('settings.linked') : t('settings.notLinked') }}
            </span>
          </span>
          <SvgIcon v-if="auth.user?.google_linked" name="check" :size="14" />
          <Btn v-else-if="auth.meta?.google_client_id" @click="linkGoogle">{{ t('settings.linkGoogle') }}</Btn>
        </div>
      </div>
    </section>

    <p
      v-if="linkOk"
      class="mt-4 max-w-lg border border-ink bg-ink/5 px-3 py-2 font-mono text-[10px] uppercase tracking-widest"
    >
      {{ t(linkOk) }}
    </p>
    <p
      v-if="linkError"
      class="mt-4 max-w-lg border border-[#C92A2A] bg-[#C92A2A]/10 px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#C92A2A]"
    >
      {{ displayError(linkError) }}
    </p>

    <p
      v-if="error"
      class="mt-4 max-w-lg border border-[#C92A2A] bg-[#C92A2A]/10 px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#C92A2A]"
    >
      {{ displayError(error) }}
    </p>
  </main>
</template>
