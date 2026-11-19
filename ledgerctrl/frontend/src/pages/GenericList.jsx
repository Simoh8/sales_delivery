import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { services } from '../lib/services'
import { useFilters } from '../context/FiltersContext'
import { DataTable, Spinner, ErrorState, Select, EmptyState } from '../components/ui'
import { PAGE_CONFIGS } from './pageConfigs'
import RiderSnapshot from '../components/snapshots/RiderSnapshot'
import DeliverySnapshot from '../components/snapshots/DeliverySnapshot'
import VehicleSnapshot from '../components/snapshots/VehicleSnapshot'

const PAGE_SIZE = 25

export default function GenericList({ configKey }) {
  const cfg = PAGE_CONFIGS[configKey]
  // cfg.filters may be an array of filter-field descriptors or a plain
  // {field: value} object of fixed filters — normalize to a list for UI use.
  const filterList = Array.isArray(cfg.filters) ? cfg.filters : []
  const { refreshTick, company, branch } = useFilters()
  const [searchParams] = useSearchParams()
  const urlQ = searchParams.get('q') || ''

  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterVals, setFilterVals] = useState({})
  const [linkOptions, setLinkOptions] = useState({})
  const [q, setQ] = useState(urlQ)
  const [snap, setSnap] = useState(null) // {type, id}

  // load link-field options once
  useEffect(() => {
    filterList.forEach(f => {
      if (f.link && !linkOptions[f.key]) {
        services.filterOptions(f.link, f.linkField || 'name')
          .then(r => setLinkOptions(o => ({ ...o, [f.key]: r.options || [] })))
          .catch(() => setLinkOptions(o => ({ ...o, [f.key]: [] })))
      }
    })
  }, [cfg]) // eslint-disable-line

  const buildFilters = useCallback(() => {
    const f = { ...(cfg.filters && !Array.isArray(cfg.filters) ? cfg.filters : {}) }
    ;filterList.forEach(fl => {
      if (filterVals[fl.key]) f[fl.key] = filterVals[fl.key]
    })
    if (company && cfg.doctype === 'Delivery Job') f.company = company
    if (branch && cfg.doctype === 'Delivery Job') f.branch = branch
    if (q.trim()) {
      const like = `%${q.trim()}%`
      // search name + customer_name via or_filters
      return { filters: f, orFilters: { name: ['like', like], customer_name: ['like', like] } }
    }
    return { filters: f }
  }, [cfg, filterVals, company, branch, q])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { filters, orFilters } = buildFilters()
      const res = await services.listDoctype({
        doctype: cfg.doctype,
        filters,
        orFilters,
        fields: cfg.fields,
        orderBy: cfg.orderBy,
        start: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      })
      setRows(res.data || [])
      setTotal(res.total || 0)
      setError(null)
    } catch (e) { setError(e) }
    finally { setLoading(false) }
  }, [cfg, buildFilters, page])

  useEffect(() => { setPage(0) }, [filterVals, q, company, branch])
  useEffect(() => { load() }, [load, refreshTick])

  const onRow = cfg.onRow
    ? (row) => {
        if (cfg.onRow === 'delivery') setSnap({ type: 'delivery', id: row.name })
        else if (cfg.onRow === 'rider') setSnap({ type: 'rider', id: row.rider || row.name })
        else if (cfg.onRow === 'vehicle') setSnap({ type: 'vehicle', id: row.vehicle || row.name })
      }
    : undefined

  if (cfg.view === 'settings') {
    return <SettingsView cfg={cfg} refreshTick={refreshTick} />
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-4 py-2.5">
        <h2 className="text-sm font-semibold text-slate-900">{cfg.title}</h2>
        <span className="text-xs text-slate-400">{total.toLocaleString()} records</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {cfg.doctype === 'Delivery Job' && (
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Search job / customer…"
              className="h-8 w-52 rounded-md border border-slate-200 px-2.5 text-xs outline-none focus:border-sky-400"
            />
          )}
          {filterList.map(f => (
            <Select
              key={f.key}
              value={filterVals[f.key] || ''}
              onChange={v => setFilterVals(s => ({ ...s, [f.key]: v }))}
              options={f.link ? (linkOptions[f.key] || []).map(o => ({ value: o, label: o })) : f.options}
              placeholder={f.label}
              className="w-36"
            />
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {error ? <ErrorState error={error} onRetry={load} /> : (
          <DataTable
            columns={cfg.columns}
            rows={rows}
            loading={loading}
            total={total}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
            onRowClick={onRow}
            empty={<EmptyState title={`No ${cfg.title.toLowerCase()} found`} />}
          />
        )}
      </div>

      {snap?.type === 'rider' && (
        <RiderSnapshot open riderName={snap.id} onClose={() => setSnap(null)} />
      )}
      {snap?.type === 'delivery' && (
        <DeliverySnapshot open jobName={snap.id} onClose={() => setSnap(null)} />
      )}
      {snap?.type === 'vehicle' && (
        <VehicleSnapshot open vehicleName={snap.id} onClose={() => setSnap(null)} />
      )}
    </div>
  )
}

const SETTING_LABELS = {
  require_otp: 'Require OTP for delivery',
  require_signature: 'Require customer signature',
  require_photograph: 'Require delivery photograph',
  require_recipient_confirmation: 'Require recipient confirmation',
  allow_multiple_active_deliveries: 'Allow multiple active deliveries per rider',
  allow_overlapping_shifts: 'Allow overlapping shifts',
  allow_multiple_active_vehicle_assignments: 'Allow multiple active vehicle assignments',
  maintenance_reminder_days: 'Maintenance reminder (days before service)',
  document_expiry_alert_days: 'Document expiry alert (days)',
  sla_breach_alert_hours: 'SLA breach alert (hours before breach)',
}

function SettingsView({ cfg }) {
  const { refreshTick } = useFilters()
  const [doc, setDoc] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    services.listDoctype({ doctype: cfg.doctype, fields: cfg.fields, limit: 1 })
      .then(r => setDoc(r.data?.[0] || {}))
      .catch(() => setDoc({}))
      .finally(() => setLoading(false))
  }, [cfg, refreshTick])

  return (
    <div className="h-full overflow-y-auto">
      <div className="border-b border-slate-200 bg-white px-4 py-2.5">
        <h2 className="text-sm font-semibold text-slate-900">{cfg.title}</h2>
        <p className="text-xs text-slate-400">Operational configuration for the delivery module. Edit values in ERPNext Desk → {cfg.doctype}.</p>
      </div>
      <div className="max-w-3xl p-4">
        {loading ? <Spinner /> : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {cfg.fields.split(',').map(f => {
              const v = doc?.[f]
              const isBool = typeof v === 'boolean' || v === 0 || v === 1
              return (
                <div key={f} className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3">
                  <span className="text-sm text-slate-700">{SETTING_LABELS[f] || f}</span>
                  {isBool ? (
                    <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${v ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{v ? 'Enabled' : 'Disabled'}</span>
                  ) : (
                    <span className="text-sm font-medium text-slate-900">{v ?? '—'}</span>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
