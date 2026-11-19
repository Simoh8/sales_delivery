export function fmtDate(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (isNaN(d)) return String(v)
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}
export function fmtDateTime(v) {
  if (!v) return '—'
  const d = new Date(String(v).replace(' ', 'T'))
  if (isNaN(d)) return String(v)
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}
export function fmtTime(v) {
  if (!v) return '—'
  const d = new Date(String(v).replace(' ', 'T'))
  if (isNaN(d)) return String(v)
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}
export function fmtRelative(v) {
  if (!v) return 'never'
  const d = new Date(String(v).replace(' ', 'T'))
  if (isNaN(d)) return String(v)
  const s = Math.max(0, (Date.now() - d.getTime()) / 1000)
  if (s < 60) return `${Math.floor(s)}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}
export function fmtMoney(v, currency = '') {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (isNaN(n)) return String(v)
  return `${currency ? currency + ' ' : ''}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
export function fmtNum(v, digits = 0) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (isNaN(n)) return String(v)
  return n.toLocaleString(undefined, { maximumFractionDigits: digits })
}
export function fmtDuration(minutes) {
  if (minutes === null || minutes === undefined) return '—'
  const m = Number(minutes)
  if (isNaN(m)) return '—'
  if (m < 60) return `${Math.round(m)}m`
  const h = Math.floor(m / 60)
  const rem = Math.round(m % 60)
  return `${h}h ${rem}m`
}
export function initials(name = '') {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?'
}
export function pct(v) {
  if (v === null || v === undefined) return '—'
  return `${Number(v).toFixed(1)}%`
}
export function todayStr() { return new Date().toISOString().slice(0, 10) }
export function daysAgo(n) {
  const d = new Date(); d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}
