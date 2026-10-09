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
      <header class="border-b-2 border-ink px-4 py-3 font-mono text-xs font-bold uppercase tracking-widest">
        {{ title }}
      </header>
      <p class="px-4 py-4 text-sm leading-relaxed text-steel">{{ message }}</p>
      <footer class="flex justify-end gap-2 border-t border-line px-4 py-3">
        <Btn variant="ghost" @click="emit('cancel')">{{ t('common.cancel') }}</Btn>
        <Btn variant="danger" @click="emit('confirm')">{{ confirmLabel || t('common.delete') }}</Btn>
      </footer>
    </div>
  </div>
</template>
