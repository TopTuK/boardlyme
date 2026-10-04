export function tg() {
  return window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null
}

export function isTelegram() {
  const t = tg()
  return !!(t && t.initData)
}

export function initTelegram() {
  const t = tg()
  if (!t) return
  try {
    t.ready()
    t.expand()
    if (typeof t.disableVerticalSwipes === 'function') t.disableVerticalSwipes()
  } catch {
    /* older Telegram clients */
  }
}
