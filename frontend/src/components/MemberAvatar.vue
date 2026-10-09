<script setup>
import { computed } from 'vue'

const props = defineProps({
  user: { type: Object, required: true },
  owner: { type: Boolean, default: false },
  size: { type: [Number, String], default: 24 },
})

// Each plate pairs a fill with a mark color that stays readable on it.
const PLATES = [
  { bg: '#161616', fg: '#F3F1E8' },
  { bg: '#E8590C', fg: '#161616' },
  { bg: '#1F4E79', fg: '#F3F1E8' },
  { bg: '#1E6B45', fg: '#F3F1E8' },
  { bg: '#E7C84A', fg: '#161616' },
  { bg: '#F3F1E8', fg: '#161616' },
  { bg: '#5C3D8F', fg: '#F3F1E8' },
  { bg: '#B23A48', fg: '#F3F1E8' },
]

const BODY = 'M3.2 15.4c.35-2.7 2.1-4.15 4.8-4.15s4.45 1.45 4.8 4.15H3.2z'

// Filled stamps in a 16×16 box. Shapes stay distinct at 24px.
// The same person keeps the same stamp.
const GLYPHS = [
  {
    circles: [{ cx: 8, cy: 5.1, r: 3.15 }],
    paths: ['M4.3 15.4c.2-2.35 1.55-3.5 3.7-3.5s3.5 1.15 3.7 3.5H4.3z'],
  },
  {
    rects: [{ x: 4.5, y: 1.9, w: 7, h: 7 }],
    paths: [BODY],
  },
  {
    rects: [
      { x: 4.7, y: 1.35, w: 6.6, h: 3.7 },
      { x: 1.15, y: 4.85, w: 13.7, h: 1.85 },
      { x: 5.7, y: 6.9, w: 4.6, h: 2.15 },
    ],
    paths: [BODY],
  },
  {
    circles: [
      { cx: 3.15, cy: 4.3, r: 1.85 },
      { cx: 12.85, cy: 4.3, r: 1.85 },
      { cx: 8, cy: 5.35, r: 2.45 },
    ],
    paths: ['M4.4 15.4c.18-2.2 1.5-3.3 3.6-3.3s3.42 1.1 3.6 3.3H4.4z'],
  },
  {
    paths: ['M8 1.05L14.1 8.35H1.9Z', BODY],
  },
  {
    paths: ['M8 0.7L13.4 6.3V9.3H2.6V6.3Z', BODY],
  },
  {
    paths: ['M1.25 9.35C1.25 2.05 14.75 2.05 14.75 9.35Z', 'M4.6 15.4c.15-1.9 1.45-2.95 3.4-2.95s3.25 1.05 3.4 2.95H4.6z'],
  },
  {
    rects: [
      { x: 1.35, y: 2.6, w: 2.35, h: 9.4 },
      { x: 12.3, y: 2.6, w: 2.35, h: 9.4 },
      { x: 4.3, y: 1.7, w: 7.4, h: 6.5 },
    ],
    paths: ['M5.1 15.4c.12-2.05 1.2-3.15 2.9-3.15s2.78 1.1 2.9 3.15H5.1z'],
  },
]

function hashId(id) {
  const s = String(id || 'user')
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

const px = computed(() => {
  const n = Number(props.size)
  return Number.isFinite(n) && n > 0 ? n : 24
})

const hashed = computed(() => hashId(props.user?.user_id || props.user?.id || props.user?.username))
const plate = computed(() => PLATES[hashed.value % PLATES.length])
const glyph = computed(() => GLYPHS[(hashed.value >>> 3) % GLYPHS.length])
const ownerMark = computed(() => (plate.value.bg === '#E8590C' ? '#161616' : '#E8590C'))
</script>

<template>
  <span
    class="relative inline-flex shrink-0 overflow-hidden border border-ink"
    :style="{ width: px + 'px', height: px + 'px' }"
  >
    <svg class="h-full w-full" viewBox="0 0 16 16" aria-hidden="true">
      <rect width="16" height="16" :fill="plate.bg" />
      <circle
        v-for="(c, i) in glyph.circles || []"
        :key="'c' + i"
        :cx="c.cx"
        :cy="c.cy"
        :r="c.r"
        :fill="plate.fg"
      />
      <rect
        v-for="(r, i) in glyph.rects || []"
        :key="'r' + i"
        :x="r.x"
        :y="r.y"
        :width="r.w"
        :height="r.h"
        :fill="plate.fg"
      />
      <path v-for="(d, i) in glyph.paths || []" :key="'p' + i" :d="d" :fill="plate.fg" />
    </svg>
    <span
      v-if="owner"
      class="absolute inset-x-0 bottom-0 h-[3px]"
      :style="{ background: ownerMark }"
    />
  </span>
</template>
