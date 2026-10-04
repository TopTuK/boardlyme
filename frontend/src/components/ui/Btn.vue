<script setup>
defineProps({
  variant: { type: String, default: 'primary' }, // 'primary' | 'ghost' | 'danger'
  block: Boolean,
})
</script>

<template>
  <button
    class="inline-flex items-center justify-center gap-1.5 px-3 py-2 font-mono text-[11px] uppercase tracking-widest transition-colors disabled:pointer-events-none disabled:opacity-40"
    :class="{
      'bg-ink text-paper hover:bg-signal': variant === 'primary',
      'border border-ink bg-transparent text-ink hover:bg-ink hover:text-paper': variant === 'ghost',
      'border border-[#C92A2A] bg-transparent text-[#C92A2A] hover:bg-[#C92A2A] hover:text-white': variant === 'danger',
      'w-full': block,
    }"
  >
    <slot />
  </button>
</template>
