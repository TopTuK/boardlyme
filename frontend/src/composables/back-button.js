import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { tg } from '../lib/telegram'

/** Telegram Mini App: wire the native BackButton to the router history. */
export function useBackButton() {
  const route = useRoute()
  const router = useRouter()

  const onClick = () => router.back()

  watch(
    () => route.name,
    () => {
      const t = tg()
      if (!t || !t.BackButton) return
      if (route.name === 'board') {
        t.BackButton.onClick(onClick)
        t.BackButton.show()
      } else {
        t.BackButton.offClick(onClick)
        t.BackButton.hide()
      }
    },
    { immediate: true },
  )
}
