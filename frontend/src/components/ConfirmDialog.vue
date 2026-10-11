<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: '' },
})

const emit = defineEmits(['confirm', 'cancel'])
const { t } = useI18n()
</script>

<template>
  <div class="sheet-overlay z-[60]" @click.self="emit('cancel')">
    <div class="sheet-panel max-w-sm" role="dialog" aria-modal="true">
      <div class="sheet-handle" aria-hidden="true"></div>
      <header class="sheet-head font-mono text-xs font-bold uppercase tracking-widest">
        {{ title }}
      </header>
      <p class="sheet-body text-sm leading-relaxed text-steel">{{ message }}</p>
      <footer class="sheet-foot sm:justify-end">
        <Btn class="w-full sm:w-auto" variant="ghost" @click="emit('cancel')">{{ t('common.cancel') }}</Btn>
        <Btn class="w-full sm:w-auto" variant="danger" @click="emit('confirm')">{{ confirmLabel || t('common.delete') }}</Btn>
      </footer>
    </div>
  </div>
</template>
