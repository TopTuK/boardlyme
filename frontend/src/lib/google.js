const STATE_KEY = 'bm_google_state'
const MODE_KEY = 'bm_google_mode'
const REDIRECT_KEY = 'bm_google_redirect'

export const GOOGLE_CALLBACK_PATH = '/auth/signin-google'

/** Redirect the browser to Google's consent screen. mode: 'login' | 'link'. */
export function startGoogleAuth(clientId, { mode = 'login', redirect = '' } = {}) {
  const state = window.crypto.randomUUID()
  sessionStorage.setItem(STATE_KEY, state)
  sessionStorage.setItem(MODE_KEY, mode)
  if (redirect) sessionStorage.setItem(REDIRECT_KEY, redirect)
  else sessionStorage.removeItem(REDIRECT_KEY)
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: `${window.location.origin}${GOOGLE_CALLBACK_PATH}`,
    response_type: 'code',
    scope: 'openid email profile',
    state,
  })
  window.location.assign(`https://accounts.google.com/o/oauth2/v2/auth?${params}`)
}

/**
 * Validate the callback query against the stored state (CSRF check).
 * Returns { code, mode, redirect } or { error }.
 */
export function consumeGoogleCallback(search) {
  const params = new URLSearchParams(search)
  const state = sessionStorage.getItem(STATE_KEY)
  const mode = sessionStorage.getItem(MODE_KEY) || 'login'
  const redirect = sessionStorage.getItem(REDIRECT_KEY) || ''
  sessionStorage.removeItem(STATE_KEY)
  sessionStorage.removeItem(MODE_KEY)
  sessionStorage.removeItem(REDIRECT_KEY)

  if (params.get('error')) return { error: params.get('error') }
  const code = params.get('code')
  if (!code || !state || params.get('state') !== state) return { error: 'errors.googleState' }
  return { code, mode, redirect }
}
