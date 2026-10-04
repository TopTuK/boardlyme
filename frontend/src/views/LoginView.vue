<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { displayError } from '../lib/messages'

const { t } = useI18n()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const error = ref('')
const busy = ref(false)
const devName = ref('')
const widgetHost = ref(null)

async function handle(fn) {
  busy.value = true
  error.value = ''
  try {
    await fn()
    const target = typeof route.query.redirect === 'string' ? route.query.redirect : '/boards'
    router.push(target)
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || 'errors.authFailed'
  } finally {
    busy.value = false
  }
}

function mountWidget() {
  const botUsername = auth.meta?.bot_username
  if (!botUsername || !widgetHost.value || widgetHost.value.childElementCount) return
  const script = document.createElement('script')
  script.src = 'https://telegram.org/js/telegram-widget.js?22'
  script.async = true
  script.setAttribute('data-telegram-login', botUsername)
  script.setAttribute('data-size', 'large')
  script.setAttribute('data-userpic', 'false')
  script.setAttribute('data-request-access', 'write')
  script.setAttribute('data-auth-url', `${window.location.origin}/login`)
  widgetHost.value.appendChild(script)
}

onMounted(async () => {
  const query = window.location.search
  if (query.includes('hash=') && query.includes('id=')) {
    await handle(() => auth.loginWidget(query.slice(1)))
    if (auth.isAuthenticated) return
  }
  mountWidget()
})
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-blueprint px-4 py-10">
    <div class="w-full max-w-sm border-2 border-ink bg-paper shadow-offset">
      <header class="border-b-2 border-ink px-5 py-4">
        <div class="flex items-center gap-2">
          <img src="/icon.png" alt="" width="32" height="32" class="h-8 w-8" />
          <div>
            <p class="text-sm font-black tracking-tight">BOARDLY</p>
            <p class="font-mono text-[9px] uppercase tracking-widest text-steel">{{ t('login.access') }}</p>
          </div>
        </div>
      </header>

      <div class="space-y-5 px-5 py-5">
        <!-- Telegram Login Widget -->
        <section>
          <h1 class="text-xl font-black uppercase tracking-tight">{{ t('login.title') }}</h1>
          <p class="mt-1 text-[13px] leading-relaxed text-steel">
            {{ t('login.text') }}
          </p>
          <div ref="widgetHost" class="mt-4 min-h-[40px]"></div>
          <p
            v-if="auth.meta && !auth.meta.bot_username"
            class="mt-2 font-mono text-[10px] uppercase leading-relaxed tracking-widest text-steel"
          >
            {{ t('login.inactive') }}
          </p>
        </section>

        <!-- Telegram Mini App retry -->
        <section v-if="auth.isTelegram && !auth.isAuthenticated" class="border border-line bg-white p-3">
          <p class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('login.miniFailed') }}</p>
          <Btn class="mt-2" :disabled="busy" @click="handle(() => auth.loginMiniApp())">{{ t('login.retry') }}</Btn>
        </section>

        <!-- Dev access -->
        <section v-if="auth.meta?.dev_fake_auth" class="border-t border-line pt-4">
          <p class="font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('login.dev') }}</p>
          <div class="mt-3 flex gap-2">
            <Btn :disabled="busy" @click="handle(() => auth.devLogin('alice'))">Alice</Btn>
            <Btn :disabled="busy" @click="handle(() => auth.devLogin('bob'))">Bob</Btn>
          </div>
          <form class="mt-2 flex gap-2" @submit.prevent="devName.trim() && handle(() => auth.devLogin(devName.trim()))">
            <input
              v-model="devName"
              :placeholder="t('login.username')"
              maxlength="32"
              class="min-w-0 flex-1 border border-line bg-white px-3 py-2 font-mono text-xs uppercase outline-none focus:border-ink"
            />
            <Btn :disabled="busy || !devName.trim()">{{ t('login.go') }}</Btn>
          </form>
        </section>

        <p v-if="error" class="border border-[#C92A2A] bg-[#C92A2A]/10 px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#C92A2A]">
          {{ displayError(error) }}
        </p>

        <RouterLink to="/" class="block font-mono text-[10px] uppercase tracking-widest text-steel hover:text-ink">
          {{ t('login.back') }}
        </RouterLink>
      </div>
    </div>
  </div>
</template>
