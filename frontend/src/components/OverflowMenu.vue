<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  align: { type: String, default: 'right' }, // 'left' | 'right'
  label: { type: String, required: true },
})

const open = ref(false)
const btn = ref(null)
const menu = ref(null)
const pos = ref({ top: 0, left: 0 })

function place() {
  const r = btn.value?.getBoundingClientRect()
  if (!r) return
  const width = menu.value?.offsetWidth || 200
  const rawLeft = props.align === 'left' ? r.left : r.right - width
  const left = Math.max(8, Math.min(rawLeft, window.innerWidth - width - 8))
  const below = r.bottom + 4
  const height = menu.value?.offsetHeight || 0
  const top = below + height > window.innerHeight - 8 ? Math.max(8, r.top - height - 4) : below
  pos.value = { top, left }
}

async function toggle() {
  open.value = !open.value
  if (open.value) {
    await nextTick()
    place()
  }
}

function close() {
  open.value = false
}

function onDoc(e) {
  if (!open.value) return
  if (btn.value?.contains(e.target) || menu.value?.contains(e.target)) return
  close()
}

onMounted(() => {
  document.addEventListener('pointerdown', onDoc)
  window.addEventListener('resize', close)
  window.addEventListener('scroll', close, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDoc)
  window.removeEventListener('resize', close)
  window.removeEventListener('scroll', close, true)
})

defineExpose({ close })
</script>

<template>
  <div class="relative inline-flex">
    <button
      ref="btn"
      type="button"
      class="inline-flex min-h-11 min-w-11 items-center justify-center text-steel hover:text-ink"
      :aria-label="label"
      :aria-expanded="open"
      @click.stop="toggle"
    >
      <slot name="trigger">
        <SvgIcon name="more" :size="14" />
      </slot>
    </button>
    <Teleport to="body">
      <div
        v-if="open"
        ref="menu"
        class="fixed z-[70] min-w-[11rem] border-2 border-ink bg-paper shadow-offset"
        :style="{ top: `${pos.top}px`, left: `${pos.left}px` }"
        role="menu"
      >
        <slot :close="close" />
      </div>
    </Teleport>
  </div>
</template>
