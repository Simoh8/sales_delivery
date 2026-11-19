import { X, Inbox, ChevronLeft, ChevronRight, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { useState } from 'react'

export function Badge({ children, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-4 ${className}`}>
      {children}
    </span>
  )
}

export function Spinner({ size = 16, className = '' }) {
  return (
    <svg className={`animate-spin ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function EmptyState({ title = 'No data', hint, icon }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center text-slate-400">
      <div className="mb-2 rounded-full bg-slate-100 p-3 text-slate-400">{icon || <Inbox size={20} />}</div>
      <div className="text-sm font-medium text-slate-500">{title}</div>
      {hint && <div className="mt-1 max-w-sm text-xs">{hint}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <div className="mb-2 text-sm font-medium text-rose-600">Failed to load data</div>
      <div className="mb-3 max-w-md text-xs text-slate-500">{error?.message || String(error)}</div>
      {onRetry && (
        <button onClick={onRetry} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700">
          Retry
        </button>
      )}
    </div>
  )
}

export function Modal({ open, onClose, title, children, width = 'max-w-3xl', footer }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-[2px]" onClick={onClose} />
      <div className={`relative flex max-h-[92vh] w-full ${width} flex-col overflow-hidden rounded-xl bg-white shadow-2xl ring-1 ring-slate-200`}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5">
          <div className="text-sm font-semibold text-slate-900">{title}</div>
          <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">{children}</div>
        {footer && <div className="border-t border-slate-200 px-5 py-3">{footer}</div>}
      </div>
    </div>
  )
}

export function KpiCard({ label, value, delta, hint, onClick, active }) {
  const DeltaIcon = delta == null ? Minus : delta > 0 ? ArrowUpRight : delta < 0 ? ArrowDownRight : Minus
  const deltaColor = delta == null ? 'text-slate-400' : delta > 0 ? 'text-emerald-600' : delta < 0 ? 'text-rose-600' : 'text-slate-400'
  return (
    <button
      onClick={onClick}
      className={`group flex min-w-0 flex-col rounded-lg border bg-white px-3.5 py-3 text-left transition-shadow ${active ? 'border-sky-400 ring-1 ring-sky-200' : 'border-slate-200 hover:shadow-sm'} ${onClick ? 'cursor-pointer' : 'cursor-default'}`}
    >
      <div className="truncate text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-xl font-semibold tabular-nums text-slate-900">{value}</span>
        {delta !== undefined && (
          <span className={`flex items-center text-[11px] font-medium tabular-nums ${deltaColor}`}>
            <DeltaIcon size={12} />
            {delta == null ? '—' : `${Math.abs(delta)}%`}
          </span>
        )}
      </div>
      {hint && <div className="mt-0.5 truncate text-[11px] text-slate-400">{hint}</div>}
    </button>
  )
}

export function SectionTitle({ children, right }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h3 className="text-[13px] font-semibold text-slate-800">{children}</h3>
      {right}
    </div>
  )
}

export function Field({ label, children }) {
  return (
    <div className="min-w-0">
      <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className="text-sm text-slate-800">{children ?? '—'}</div>
    </div>
  )
}

export function Select({ value, onChange, options, placeholder = 'All', className = '' }) {
  return (
    <select
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      className={`h-8 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700 outline-none focus:border-sky-400 ${className}`}
    >
      <option value="">{placeholder}</option>
      {options.map(o => (
        <option key={typeof o === 'object' ? o.value : o} value={typeof o === 'object' ? o.value : o}>
          {typeof o === 'object' ? o.label : o}
        </option>
      ))}
    </select>
  )
}

export function DataTable({ columns, rows, loading, empty, onRowClick, page, pageSize = 25, total, onPage }) {
  const [localPage, setLocalPage] = useState(0)
  const current = page !== undefined ? page : localPage
  const setPage = onPage || ((p) => setLocalPage(p))
  const paged = page === undefined ? rows?.slice(current * pageSize, (current + 1) * pageSize) : rows
  const totalPages = Math.max(1, Math.ceil((total ?? rows?.length ?? 0) / pageSize))

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              {columns.map(c => (
                <th key={c.key} className={`px-3 py-2 ${c.className || ''}`}>{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={columns.length} className="px-3 py-10 text-center text-slate-400">
                <span className="inline-flex items-center gap-2"><Spinner size={14} /> Loading…</span>
              </td></tr>
            ) : !paged?.length ? (
              <tr><td colSpan={columns.length}>{empty || <EmptyState />}</td></tr>
            ) : paged.map((row, i) => (
              <tr
                key={row.name || i}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={`border-b border-slate-100 last:border-0 ${onRowClick ? 'cursor-pointer hover:bg-slate-50' : ''}`}
              >
                {columns.map(c => (
                  <td key={c.key} className={`px-3 py-2 align-middle ${c.className || ''}`}>
                    {c.render ? c.render(row, i) : (row[c.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(total !== undefined || rows?.length > pageSize) && (
        <div className="flex items-center justify-between border-t border-slate-200 px-3 py-2 text-xs text-slate-500">
          <span>{total !== undefined ? `${total.toLocaleString()} records` : `${rows?.length ?? 0} records`}</span>
          <div className="flex items-center gap-1">
            <button disabled={current <= 0} onClick={() => setPage(current - 1)} className="rounded p-1 hover:bg-slate-100 disabled:opacity-30"><ChevronLeft size={15} /></button>
            <span className="px-1 tabular-nums">{current + 1} / {totalPages}</span>
            <button disabled={current >= totalPages - 1} onClick={() => setPage(current + 1)} className="rounded p-1 hover:bg-slate-100 disabled:opacity-30"><ChevronRight size={15} /></button>
          </div>
        </div>
      )}
    </div>
  )
}
