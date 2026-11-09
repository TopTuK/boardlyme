<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { consumeGoogleCallback } from '../lib/google'
import { displayError } from '../lib/messages'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()

const error = ref('')

onMounted(async () => {
  const result = consumeGoogleCallback(window.location.search)
  if (!result.code) {
    error.value = result.error
    return
  }
  try {
    if (result.mode === 'link') {
      await auth.linkGoogle(result.code)
      router.push('/settings')
    } else {
      await auth.loginGoogle(result.code)
      const target = result.redirect
      router.push(target && target.startsWith('/') && !target.startsWith('/login') ? target : '/boards')
    }
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || 'errors.authFailed'
  }
})
</script>

<template>
  <div class="flex min-h-dvh items-center justify-center bg-blueprint px-4 py-10 safe-px safe-pt safe-pb">
    <div class="w-full max-w-sm border-2 border-ink bg-paper px-5 py-6 shadow-offset">
      <p v-if="!error" class="font-mono text-[11px] uppercase tracking-widest text-steel">
        {{ t('login.googlePending') }}
      </p>
      <template v-else>
        <p class="border border-[#C92A2A] bg-[#C92A2A]/10 px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#C92A2A]">
          {{ displayError(error) }}
        </p>
        <RouterLink
          :to="auth.isAuthenticated ? '/settings' : '/login'"
          class="mt-4 block font-mono text-[10px] uppercase tracking-widest text-steel hover:text-ink"
        >
          {{ t('login.back') }}
        </RouterLink>
      </template>
    </div>
  </div>
</template>
