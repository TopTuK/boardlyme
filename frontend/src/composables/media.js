import { onBeforeUnmount, onMounted, ref } from 'vue'

const PHONE_QUERY = '(max-width: 767px)'

/** True below Tailwind `md` (768px) — station chrome, compact header, touch cards. */
export function useIsPhone() {
  const isPhone = ref(typeof window !== 'undefined' ? window.matchMedia(PHONE_QUERY).matches : false)
  let mql

  function onChange(event) {
    isPhone.value = event.matches
  }

  onMounted(() => {
    mql = window.matchMedia(PHONE_QUERY)
    isPhone.value = mql.matches
    mql.addEventListener('change', onChange)
  })

  onBeforeUnmount(() => {
    mql?.removeEventListener('change', onChange)
  })

  return isPhone
}
