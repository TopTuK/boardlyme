import { i18n } from '../i18n'

function pad(n) {
  return String(n).padStart(2, '0')
}

export function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** "2026-10-04" -> "OCT 4" (no Date parsing, so timezones can't shift the day) */
export function fmtDeadline(iso) {
  if (!iso) return ''
  const [, m, d] = iso.split('-')
  const months = i18n.global.tm('months')
  const label = Array.isArray(months) ? months[Number(m) - 1] : ''
  return `${label || '?'} ${Number(d)}`
}

/** 'none' | 'overdue' | 'today' | 'soon' | 'later' */
export function deadlineState(iso) {
  if (!iso) return 'none'
  const today = todayStr()
  if (iso < today) return 'overdue'
  if (iso === today) return 'today'
  const diff = (new Date(`${iso}T00:00:00`) - new Date(`${today}T00:00:00`)) / 86400000
  return diff <= 3 ? 'soon' : 'later'
}

export function initials(user) {
  if (!user) return '?'
  const first = user.first_name || user.username || ''
  const last = user.last_name || ''
  return ((first[0] || '') + (last[0] || '')).toUpperCase() || '?'
}

export function displayName(user) {
  if (!user) return ''
  if (user.first_name) return [user.first_name, user.last_name].filter(Boolean).join(' ')
  return `@${user.username || 'user'}`
}

/** Works for both User objects and board MemberOut rows */
export function memberName(m) {
  if (!m) return ''
  const name = [m.first_name, m.last_name].filter(Boolean).join(' ')
  if (name) return m.username ? `${name} (@${m.username})` : name
  return `@${m.username || m.user_id}`
}
