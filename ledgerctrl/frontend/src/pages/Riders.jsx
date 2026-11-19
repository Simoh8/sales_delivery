import { useEffect, useState, useCallback } from 'react'
import { services } from '../lib/services'
import { useFilters } from '../context/FiltersContext'
import { DataTable, Spinner, ErrorState, Select, EmptyState, Badge } from '../components/ui'
import RiderSnapshot from '../components/snapshots/RiderSnapshot'
import { fmtDate, initials } from '../lib/format'
import { availabilityColor } from '../lib/status'
import { LayoutGrid, Rows3, Search } from 'lucide-react'

const FIELDS = 'name,rider_name,employee,mobile_number,employment_status,default_vehicle,company,verification_status,joining_date'
const PAGE_SIZE = 24

export default function Riders() {
  const { refreshTick, company } = useFilters()
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [view, setView] = useState('table')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState('Active')
  const [q, setQ] = useState('')
  const [snap, setSnap] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const filters = { employment_status: status }
      if (company) filters.company = company
      const orFilters = q.trim() ? {
        rider_name: ['like', `%${q.trim()}%`],
        employee: ['like', `%${q.trim()}%`],
        name: ['like', `%${q.trim()}%`],
      } : undefined
      const res = await services.listDoctype({
        doctype: 'Rider Profile', filters, orFilters, fields: FIELDS,
        orderBy: 'rider_name asc', start: page * PAGE_SIZE, limit: PAGE_SIZE,
      })
      setRows(res.data || [])
      setTotal(res.total || 0)
      setError(null)
    } catch (e) { setError(e) }
    finally { setLoading(false) }
  }, [status, q, company, page])

  useEffect(() => { setPage(0) }, [status, q, company])
  useEffect(() => { load() }, [load, refreshTick])

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-4 py-2.5">
        <h2 className="text-sm font-semibold text-slate-900">Riders</h2>
        <span className="text-xs text-slate-400">{total.toLocaleString()} profiles</span>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search riders…"
              className="h-8 w-48 rounded-md border border-slate-200 pl-7 pr-2 text-xs outline-none focus:border-sky-400" />
          </div>
          <Select value={status} onChange={setStatus}
            options={['Active', 'Inactive', 'Suspended', 'On Leave']} placeholder="Status" className="w-32" />
          <div className="flex overflow-hidden rounded-md border border-slate-200">
            <button onClick={() => setView('table')} className={`p-1.5 ${view === 'table' ? 'bg-slate-900 text-white' : 'text-slate-500'}`}><Rows3 size={14} /></button>
            <button onClick={() => setView('cards')} className={`p-1.5 ${view === 'cards' ? 'bg-slate-900 text-white' : 'text-slate-500'}`}><LayoutGrid size={14} /></button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {error ? <ErrorState error={error} onRetry={load} /> : view === 'table' ? (
          <DataTable
            columns={[
              { key: 'rider_name', label: 'Rider', render: r => (
                <div className="flex items-center gap-2.5">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800 text-[10px] font-bold text-white">{initials(r.rider_name || r.name)}</div>
                  <div>
                    <div className="font-medium text-slate-800">{r.rider_name || '—'}</div>
                    <div className="font-mono text-[10px] text-slate-400">{r.name}</div>
                  </div>
                </div>
              )},
              { key: 'employee', label: 'Employee' },
              { key: 'mobile_number', label: 'Mobile' },
              { key: 'default_vehicle', label: 'Vehicle' },
              { key: 'employment_status', label: 'Status', render: r => <Badge className={r.employment_status === 'Active' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-500'}>{r.employment_status}</Badge> },
              { key: 'verification_status', label: 'Verification' },
              { key: 'joining_date', label: 'Joined', render: r => fmtDate(r.joining_date) },
            ]}
            rows={rows}
            loading={loading}
            total={total}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
            onRowClick={r => setSnap(r.name)}
            empty={<EmptyState title="No riders found" />}
          />
        ) : (
          <>
            {loading ? <div className="flex justify-center py-16"><Spinner size={22} /></div> : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {rows.map(r => (
                  <button key={r.name} onClick={() => setSnap(r.name)}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm hover:shadow">
                    <div className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-800 text-sm font-bold text-white">{initials(r.rider_name || r.name)}</div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold text-slate-800">{r.rider_name || r.name}</div>
                      <div className="truncate text-[11px] text-slate-400">{r.employee || r.mobile_number || ''}</div>
                      <div className="mt-1 flex gap-1.5">
                        <Badge className={r.employment_status === 'Active' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-500'}>{r.employment_status}</Badge>
                        {r.default_vehicle && <Badge className="border-slate-200 bg-slate-50 text-slate-600">{r.default_vehicle}</Badge>}
                      </div>
                    </div>
                  </button>
                ))}
                {rows.length === 0 && <EmptyState title="No riders found" />}
              </div>
            )}
            {total > PAGE_SIZE && (
              <div className="mt-4 flex items-center justify-center gap-2 text-xs text-slate-500">
                <button disabled={page <= 0} onClick={() => setPage(p => p - 1)} className="rounded border border-slate-200 px-2 py-1 disabled:opacity-30">Prev</button>
                <span>Page {page + 1} / {Math.ceil(total / PAGE_SIZE)}</span>
                <button disabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)} className="rounded border border-slate-200 px-2 py-1 disabled:opacity-30">Next</button>
              </div>
            )}
          </>
        )}
      </div>

      {snap && <RiderSnapshot open riderName={snap} onClose={() => setSnap(null)} />}
    </div>
  )
}
