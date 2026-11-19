// Thin fetch wrapper for Frappe whitelisted methods + JWT auth.

const TOKEN_KEY = 'lc_access_token'
const REFRESH_KEY = 'lc_refresh_token'
const USER_KEY = 'lc_user'

// In dev, Vite proxies /api to the bench site. For a production build set
// VITE_API_BASE to the site origin (e.g. https://ledgerctl.example.com).
export const API_BASE = import.meta.env.VITE_API_BASE || ''

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY)
}
export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}
export function getStoredUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null }
}
export function setSession({ access_token, refresh_token }, user) {
  localStorage.setItem(TOKEN_KEY, access_token)
  localStorage.setItem(REFRESH_KEY, refresh_token || '')
  localStorage.setItem(USER_KEY, JSON.stringify(user || {}))
}
export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_KEY)
}

// Frappe enforces CSRF on POSTs for cookie sessions (the desk session is
// shared with this app when embedded in the /command_center iframe).
// Fetch the session token once and echo it back on unsafe requests.
let csrfPromise = null
function getCsrfToken() {
  if (!csrfPromise) {
    csrfPromise = fetch(`${API_BASE}/api/method/ledgerctrl.ledgerctrl.api.login_api.get_csrf_token`)
      .then((r) => r.json())
      .then((b) => b?.message || null)
      .catch(() => {
        csrfPromise = null
        return null
      })
  }
  return csrfPromise
}
function resetCsrfToken() {
  csrfPromise = null
}
function isCsrfError(e) {
  return e?.body?.exc_type === 'CSRFTokenError' ||
    (typeof e?.body?.exception === 'string' && e.body.exception.includes('CSRFTokenError'))
}

async function rawCall(method, params = {}, { auth = true, method: httpMethod = 'POST' } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (httpMethod !== 'GET') {
    const csrf = await getCsrfToken()
    if (csrf) headers['X-Frappe-CSRF-Token'] = csrf
  }
  if (auth) {
    const t = getAccessToken()
    if (t) headers.Authorization = `Bearer ${t}`
  }
  const qs = httpMethod === 'GET'
    ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null)).toString()
    : ''
  const res = await fetch(`${API_BASE}/api/method/${method}${qs}`, {
    method: httpMethod,
    headers,
    body: httpMethod === 'GET' ? undefined : JSON.stringify(params),
  })
  const text = await res.text()
  let body
  try { body = JSON.parse(text) } catch { body = { raw: text } }
  if (!res.ok) {
    const msg = body?.exception || body?.message || body?.raw || `HTTP ${res.status}`
    const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    err.status = res.status
    err.body = body
    throw err
  }
  return body?.message !== undefined ? body.message : body
}

let refreshing = null
async function tryRefresh() {
  if (refreshing) return refreshing
  const rt = getRefreshToken()
  if (!rt) return false
  refreshing = (async () => {
    try {
      const csrf = await getCsrfToken()
      const headers = { 'Content-Type': 'application/json' }
      if (csrf) headers['X-Frappe-CSRF-Token'] = csrf
      const res = await fetch(`${API_BASE}/api/method/ledgerctrl.ledgerctrl.api.login_api.refresh_token`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ refresh_token_str: rt }),
      })
      const body = await res.json()
      const d = body?.message?.data || body?.data || body?.message
      if (d?.access_token) {
        localStorage.setItem(TOKEN_KEY, d.access_token)
        if (d.refresh_token) localStorage.setItem(REFRESH_KEY, d.refresh_token)
        return true
      }
      return false
    } catch { return false }
  })()
  try { return await refreshing } finally { refreshing = null }
}

export async function callApi(method, params = {}, opts = {}) {
  try {
    return await rawCall(method, params, opts)
  } catch (e) {
    if (isCsrfError(e) && opts.method !== 'GET') {
      resetCsrfToken()
      try {
        return await rawCall(method, params, opts)
      } catch (e2) {
        e = e2
      }
    }
    if (e.status === 401 || e.status === 403) {
      const ok = await tryRefresh()
      if (ok) return rawCall(method, params, opts)
      if (e.status === 401) {
        clearSession()
        if (!location.pathname.startsWith('/login')) location.href = '/login'
      }
    }
    throw e
  }
}

export const M = {
  login: 'ledgerctrl.ledgerctrl.api.login_api.user_logn',
  sessionLogin: 'ledgerctrl.ledgerctrl.api.login_api.session_login',
  logout: 'ledgerctrl.ledgerctrl.api.login_api.logout',
  commandCenter: 'ledgerctrl.ledgerctrl.api.command_center_api.get_command_center_summary',
  liveRiders: 'ledgerctrl.ledgerctrl.api.command_center_api.get_live_rider_locations',
  activeDeliveries: 'ledgerctrl.ledgerctrl.api.command_center_api.get_active_delivery_locations',
  availableRiders: 'ledgerctrl.ledgerctrl.api.command_center_api.get_available_riders',
  dispatchBoard: 'ledgerctrl.ledgerctrl.api.command_center_api.get_dispatch_board_data',
  riderSnapshot: 'ledgerctrl.ledgerctrl.api.command_center_api.get_rider_snapshot',
  riderPerformance: 'ledgerctrl.ledgerctrl.api.command_center_api.get_rider_performance',
  riderEarnings: 'ledgerctrl.ledgerctrl.api.command_center_api.get_rider_earnings',
  riderHistory: 'ledgerctrl.ledgerctrl.api.command_center_api.get_rider_delivery_history',
  riderTimeline: 'ledgerctrl.ledgerctrl.api.command_center_api.get_rider_activity_timeline',
  vehicleSnapshot: 'ledgerctrl.ledgerctrl.api.command_center_api.get_vehicle_snapshot',
  vehiclePerformance: 'ledgerctrl.ledgerctrl.api.command_center_api.get_vehicle_performance',
  deliverySnapshot: 'ledgerctrl.ledgerctrl.api.command_center_api.get_delivery_snapshot',
  deliveryRoute: 'ledgerctrl.ledgerctrl.api.command_center_api.get_delivery_route',
  assignDelivery: 'ledgerctrl.ledgerctrl.api.command_center_api.assign_delivery',
  unassignDelivery: 'ledgerctrl.ledgerctrl.api.command_center_api.unassign_delivery',
  deliveryAnalytics: 'ledgerctrl.ledgerctrl.api.command_center_api.get_delivery_analytics',
  riderAnalytics: 'ledgerctrl.ledgerctrl.api.command_center_api.get_rider_analytics',
  fleetAnalytics: 'ledgerctrl.ledgerctrl.api.command_center_api.get_fleet_analytics',
  geographicAnalytics: 'ledgerctrl.ledgerctrl.api.command_center_api.get_geographic_analytics',
  doctypeFields: 'ledgerctrl.ledgerctrl.api.command_center_api.get_doctype_fields',
  listDoctype: 'ledgerctrl.ledgerctrl.api.command_center_api.list_doctype',
  filterOptions: 'ledgerctrl.ledgerctrl.api.command_center_api.get_filter_options',
}
