<script setup>
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
import { useBackButton } from './composables/back-button'

const route = useRoute()
const { t, locale } = useI18n()
useBackButton()

watch(locale, () => {
  document.title = t('meta.title')
}, { immediate: true })
</script>

<template>
  <div class="min-h-dvh bg-paper font-sans text-ink">
    <AppHeader v-if="route.meta.app" />
    <router-view />
  </div>
</template>
