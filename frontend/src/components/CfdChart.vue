<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { fmtDeadline } from '../lib/format'

/**
 * Cumulative flow diagram: one stacked area per band, the last band of the
 * flow (Done) at the bottom and the first (Backlog) on top.
 *
 * bands:  [{ key, label }] in board (flow) order
 * points: [{ day: 'YYYY-MM-DD', counts: { [key]: n } }] ascending
 */
const props = defineProps({
  bands: { type: Array, required: true },
  points: { type: Array, required: true },
  totalLabel: { type: String, default: 'Total' },
})

// Validated categorical order (adjacent CVD ΔE ≥ 9 on white). Bands past the
// eighth fold into a neutral instead of cycling hues.
const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
const OVERFLOW = '#9a9a92'
const HEIGHT = 260
const M = { top: 10, right: 10, bottom: 26, left: 34 }
const TIP_WIDTH = 192 // px, matches the tooltip's w-48

const root = ref(null)
const width = ref(640)
const hover = ref(null) // index into points
let observer = null

onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    width.value = Math.max(280, Math.floor(entry.contentRect.width))
  })
  if (root.value) observer.observe(root.value)
})
onBeforeUnmount(() => observer?.disconnect())

const colored = computed(() =>
  props.bands.map((b, i) => ({ ...b, color: PALETTE[i] || OVERFLOW }))
)
const plotW = computed(() => width.value - M.left - M.right)
const plotH = HEIGHT - M.top - M.bottom

// Whole-number tick step (1, 2, 5, 10, 20, …) giving at most 4 intervals.
function niceStep(max) {
  const raw = Math.max(1, max / 4)
  const mag = 10 ** Math.floor(Math.log10(raw))
  for (const k of [1, 2, 5, 10]) if (k * mag >= raw) return k * mag
  return 10 * mag
}

const totals = computed(() =>
  props.points.map((p) => props.bands.reduce((sum, b) => sum + (p.counts[b.key] || 0), 0))
)
const yStep = computed(() => niceStep(Math.max(0, ...totals.value)))
const yMax = computed(() => Math.max(yStep.value, Math.ceil(Math.max(0, ...totals.value) / yStep.value) * yStep.value))
const yTicks = computed(() => {
  const ticks = []
  for (let v = 0; v <= yMax.value; v += yStep.value) ticks.push(v)
  return ticks
})

function x(i) {
  const n = props.points.length
  return M.left + (n <= 1 ? plotW.value / 2 : (i / (n - 1)) * plotW.value)
}
function y(v) {
  return M.top + plotH - (v / yMax.value) * plotH
}

// Stack bottom-up from the end of the flow. A single point is drawn across
// the full width so a one-day period still shows bands.
const layers = computed(() => {
  const pts = props.points
  const xs = pts.length === 1 ? [M.left, M.left + plotW.value] : pts.map((_, i) => x(i))
  const series = pts.length === 1 ? [pts[0], pts[0]] : pts
  const base = series.map(() => 0)
  const out = []
  for (const band of [...colored.value].reverse()) {
    const lower = [...base]
    series.forEach((p, i) => (base[i] += p.counts[band.key] || 0))
    const upper = [...base]
    const top = upper.map((v, i) => `${xs[i].toFixed(1)},${y(v).toFixed(1)}`)
    const bottom = lower.map((v, i) => `${xs[i].toFixed(1)},${y(v).toFixed(1)}`).reverse()
    out.push({ ...band, area: `M${top.join('L')}L${bottom.join('L')}Z`, edge: `M${top.join('L')}` })
  }
  return out
})

const xTicks = computed(() => {
  const n = props.points.length
  if (!n) return []
  const want = Math.max(2, Math.min(6, Math.floor(plotW.value / 90)))
  const step = Math.max(1, Math.ceil((n - 1) / (want - 1)))
  const idx = []
  for (let i = 0; i < n; i += step) idx.push(i)
  if (idx[idx.length - 1] !== n - 1) {
    // Drop a tick that would crowd the final one.
    if (n - 1 - idx[idx.length - 1] < step / 2) idx.pop()
    idx.push(n - 1)
  }
  return idx.map((i) => ({ i, x: x(i), label: fmtDeadline(props.points[i].day) }))
})

function onPointer(e) {
  const n = props.points.length
  if (!n) return
  const rect = e.currentTarget.getBoundingClientRect()
  const px = ((e.clientX - rect.left) / rect.width) * width.value
  const i = n <= 1 ? 0 : Math.round(((px - M.left) / plotW.value) * (n - 1))
  hover.value = Math.max(0, Math.min(n - 1, i))
}

const tip = computed(() => {
  if (hover.value === null) return null
  const p = props.points[hover.value]
  if (!p) return null
  const left = x(hover.value)
  return {
    left,
    // Flip to the left of the crosshair when the box would overflow the chart.
    alignRight: left + 10 + TIP_WIDTH > width.value,
    day: fmtDeadline(p.day),
    rows: colored.value.map((b) => ({ ...b, value: p.counts[b.key] || 0 })),
    total: totals.value[hover.value],
  }
})

const latest = computed(() => props.points[props.points.length - 1]?.counts || {})
</script>

<template>
  <div ref="root" class="relative w-full select-none">
    <svg
      :width="width"
      :height="HEIGHT"
      :viewBox="`0 0 ${width} ${HEIGHT}`"
      class="block touch-pan-y"
      role="img"
      @pointermove="onPointer"
      @pointerdown="onPointer"
      @pointerleave="hover = null"
    >
      <!-- grid -->
      <g>
        <line
          v-for="tk in yTicks"
          :key="`g${tk}`"
          :x1="M.left"
          :x2="width - M.right"
          :y1="y(tk)"
          :y2="y(tk)"
          :stroke="tk === 0 ? '#c3c2b7' : '#e1e0d9'"
          stroke-width="1"
        />
        <text
          v-for="tk in yTicks"
          :key="`t${tk}`"
          :x="M.left - 6"
          :y="y(tk) + 3"
          text-anchor="end"
          class="fill-steel font-mono text-[10px] tabular-nums"
        >
          {{ tk }}
        </text>
        <text
          v-for="tk in xTicks"
          :key="`x${tk.i}`"
          :x="tk.x"
          :y="HEIGHT - 8"
          :text-anchor="tk.i === 0 ? 'start' : tk.i === points.length - 1 ? 'end' : 'middle'"
          class="fill-steel font-mono text-[10px] uppercase"
        >
          {{ tk.label }}
        </text>
      </g>

      <!-- stacked bands, then 2px surface gaps along each band's top edge -->
      <path v-for="l in layers" :key="`a${l.key}`" :d="l.area" :fill="l.color" />
      <path
        v-for="l in layers"
        :key="`e${l.key}`"
        :d="l.edge"
        fill="none"
        stroke="#ffffff"
        stroke-width="2"
        stroke-linejoin="round"
      />

      <!-- crosshair -->
      <line
        v-if="tip"
        :x1="tip.left"
        :x2="tip.left"
        :y1="M.top"
        :y2="M.top + plotH"
        stroke="#161616"
        stroke-width="1"
      />
    </svg>

    <div
      v-if="tip"
      class="pointer-events-none absolute top-2 z-10 w-48 border-2 border-ink bg-white px-2.5 py-2 shadow-offset-sm"
      :style="tip.alignRight ? { right: `${width - tip.left + 10}px` } : { left: `${tip.left + 10}px` }"
    >
      <div class="mb-1 font-mono text-[10px] font-bold uppercase tracking-widest text-ink">{{ tip.day }}</div>
      <div v-for="r in tip.rows" :key="r.key" class="flex items-center gap-2 text-[11px] leading-5 text-ink">
        <span class="h-2.5 w-2.5 shrink-0" :style="{ background: r.color }"></span>
        <span class="min-w-0 flex-1 truncate">{{ r.label }}</span>
        <span class="font-mono tabular-nums">{{ r.value }}</span>
      </div>
      <div class="mt-1 flex justify-between border-t border-line pt-1 font-mono text-[10px] uppercase text-steel">
        <span>{{ totalLabel }}</span>
        <span class="tabular-nums">{{ tip.total }}</span>
      </div>
    </div>

    <!-- legend: flow order, with the latest count -->
    <ul class="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
      <li v-for="b in colored" :key="b.key" class="flex items-center gap-1.5 text-[11px] text-ink">
        <span class="h-2.5 w-2.5 shrink-0" :style="{ background: b.color }"></span>
        <span>{{ b.label }}</span>
        <span class="font-mono text-steel tabular-nums">{{ latest[b.key] || 0 }}</span>
      </li>
    </ul>
  </div>
</template>
