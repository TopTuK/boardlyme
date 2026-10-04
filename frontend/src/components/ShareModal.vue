<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBoardStore } from '../stores/board'
import { initials, memberName } from '../lib/format'

const emit = defineEmits(['close'])
const { t } = useI18n()

const board = useBoardStore()
const query = ref('')
const results = ref([])
let searchTimer = null

function onInput() {
  clearTimeout(searchTimer)
  const q = query.value.trim()
  if (q.length < 2) {
    results.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    results.value = await board.searchUsers(q)
  }, 300)
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  clearTimeout(searchTimer)
})
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 sm:items-center sm:p-4">
    <div class="max-h-[92vh] w-full max-w-lg overflow-y-auto border-2 border-ink bg-paper shadow-offset">
      <header class="flex items-center justify-between border-b-2 border-ink px-4 py-3">
        <div class="flex items-center gap-2">
          <span class="bg-ink px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-paper">{{ t('share.badge') }}</span>
          <span class="truncate text-sm font-black uppercase">{{ board.project?.name }}</span>
        </div>
        <button class="text-steel hover:text-ink" @click="emit('close')">
          <SvgIcon name="x" :size="14" />
        </button>
      </header>

      <div class="space-y-5 p-4">
        <!-- current members -->
        <section>
          <h3 class="mb-2 font-mono text-[10px] uppercase tracking-widest text-steel">
            {{ t('share.members', { n: board.members.length }) }}
          </h3>
          <ul class="divide-y divide-line border border-line bg-white">
            <li v-for="m in board.members" :key="m.user_id" class="flex items-center gap-3 px-3 py-2">
              <span
                class="flex h-6 w-6 items-center justify-center border border-ink bg-white font-mono text-[9px] font-bold"
                :class="m.role === 'owner' ? 'bg-ink text-paper' : ''"
              >
                {{ initials(m) }}
              </span>
              <span class="min-w-0 flex-1 truncate text-[13px]">{{ memberName(m) }}</span>
              <span
                class="px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest"
                :class="m.role === 'owner' ? 'bg-signal text-white' : 'border border-line text-steel'"
              >
                {{ t('roles.' + m.role) }}
              </span>
              <button
                v-if="m.role !== 'owner'"
                class="text-steel hover:text-[#C92A2A]"
                :title="t('share.remove')"
                @click="board.removeMember(m.user_id)"
              >
                <SvgIcon name="x" :size="12" />
              </button>
            </li>
          </ul>
        </section>

        <!-- search -->
        <section>
          <h3 class="mb-2 font-mono text-[10px] uppercase tracking-widest text-steel">{{ t('share.add') }}</h3>
          <input
            v-model="query"
            :placeholder="t('share.search')"
            class="w-full border-2 border-ink bg-white px-3 py-2 font-mono text-xs uppercase outline-none focus:border-signal"
            @input="onInput"
          />

          <ul v-if="results.length" class="mt-2 divide-y divide-line border border-line bg-white">
            <li v-for="u in results" :key="u.id" class="flex items-center gap-3 px-3 py-2">
              <span class="flex h-6 w-6 items-center justify-center border border-ink bg-white font-mono text-[9px] font-bold">
                {{ initials(u) }}
              </span>
              <span class="min-w-0 flex-1 truncate text-[13px]">{{ memberName(u) }}</span>
              <Btn v-if="!u.is_member" variant="ghost" @click="board.addMember(u.id)">
                <SvgIcon name="plus" :size="11" /> {{ t('common.add') }}
              </Btn>
              <span v-else class="font-mono text-[9px] uppercase tracking-widest text-steel">{{ t('share.member') }}</span>
            </li>
          </ul>
          <p v-else-if="query.trim().length >= 2" class="mt-2 font-mono text-[10px] uppercase tracking-widest text-steel">
            {{ t('share.none') }}
          </p>
          <p class="mt-2 text-[11px] leading-relaxed text-steel">
            {{ t('share.hint') }}
          </p>
        </section>
      </div>
    </div>
  </div>
</template>
