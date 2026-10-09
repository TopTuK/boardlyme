<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 14 },
})

const PATHS = {
  plus: 'M8 3v10M3 8h10',
  check: 'M3 9l4 4 6-8',
  x: 'M4 4l8 8M12 4l-8 8',
  trash: 'M3 5h10M6 5V3h4v2M5 5l1 8h4l1-8',
  pencil: 'M11 2l3 3-8 8H3v-3l8-8z',
  calendar: 'M3 5h10v8H3V5zM3 8h10M6 3v2M10 3v2',
  user: 'M8 8a3 3 0 100-6 3 3 0 000 6zM2 14c0-3 3-4 6-4s6 1 6 4',
  share: 'M8 2v8M5 5l3-3 3 3M3 10v3h10v-3',
  logout: 'M6 2h7v12H6M2 8h8M7 5L4 8l3 3',
  back: 'M10 3L5 8l5 5',
  left: 'M10 3L5 8l5 5',
  right: 'M6 3l5 5-5 5',
  lines: 'M3 4h10M3 8h10M3 12h7',
  square: 'M4 4h8v8H4z',
  chart: 'M2 14h12M4 11v-3M7 11V5M10 11V7M13 11V3',
  clock:'M8 14A6 6 0 108 2a6 6 0 000 12zM8 5v3l2 2',
  settings: 'M8 6.2a1.8 1.8 0 100 3.6 1.8 1.8 0 000-3.6zM8 1.5v1.6M8 12.9v1.6M1.5 8h1.6M12.9 8h1.6M3.2 3.2l1.2 1.2M11.6 11.6l1.2 1.2M12.8 3.2l-1.2 1.2M4.4 11.6l-1.2 1.2',
}

const d = computed(() => PATHS[props.name] || '')
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    stroke-linecap="square"
    class="inline-block shrink-0"
    aria-hidden="true"
  >
    <path :d="d" />
  </svg>
</template>
