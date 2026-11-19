import { useEffect, useState, useCallback } from 'react'
import { services } from '../lib/services'
import { useFilters } from '../context/FiltersContext'
import { DataTable, Spinner, ErrorState, Select, EmptyState, Badge } from '../components/ui'
import VehicleSnapshot from '../components/snapshots/VehicleSnapshot'
import { fmtNum } from '../lib/format'
import { Search } from 'lucide-react'

const FIELDS = 'name,license_plate,vehicle_type,make,model,last_odometer,employee,location,fuel_type,acquisition_date,vehicle_value'
const PAGE_SIZE = 25
const TYPES = ['Motorcycle', 'Pickup', 'Van', 'Truck', 'Other']

export default function Fleet() {
  const { refreshTick } = useFilters()
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [type, setType] = useState('')
  const [q, setQ] = useState('')
  const [snap, setSnap] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const filters = {}
      if (type) filters.vehicle_type = type
      const orFilters = q.trim() ? {
        license_plate: ['like', `%${q.trim()}%`],
        name: ['like', `%${q.trim()}%`],
      } : undefined
      const res = await services.listDoctype({
        doctype: 'Vehicle', filters, orFilters, fields: FIELDS,
        orderBy: 'license_plate asc', start: page * PAGE_SIZE, limit: PAGE_SIZE,
      })
      setRows(res.data || [])
      setTotal(res.total || 0)
      setError(null)
    } catch (e) { setError(e) }
    finally { setLoading(false) }
  }, [type, q, page])

  useEffect(() => { setPage(0) }, [type, q])
  useEffect(() => { load() }, [load, refreshTick])

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-4 py-2.5">
        <h2 className="text-sm font-semibold text-slate-900">Vehicles</h2>
        <span className="text-xs text-slate-400">{total.toLocaleString()} vehicles</span>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search plate / vehicle…"
              className="h-8 w-48 rounded-md border border-slate-200 pl-7 pr-2 text-xs outline-none focus:border-sky-400" />
          </div>
          <Select value={type} onChange={setType} options={TYPES} placeholder="All types" className="w-32" />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {error ? <ErrorState error={error} onRetry={load} /> : (
          <DataTable
            columns={[
              { key: 'license_plate', label: 'Registration', render: r => <span className="font-mono text-xs font-semibold">{r.license_plate || r.name}</span> },
              { key: 'vehicle_type', label: 'Type', render: r => <Badge className="border-slate-200 bg-slate-50 text-slate-600">{r.vehicle_type || '—'}</Badge> },
              { key: 'make', label: 'Make', render: r => [r.make, r.model].filter(Boolean).join(' ') || '—' },
              { key: 'employee', label: 'Assigned employee' },
              { key: 'last_odometer', label: 'Odometer', render: r => r.last_odometer != null ? `${fmtNum(r.last_odometer)} km` : '—', className: 'text-right' },
              { key: 'fuel_type', label: 'Fuel' },
              { key: 'location', label: 'Location' },
            ]}
            rows={rows}
            loading={loading}
            total={total}
            page={page}
            pageSize={PAGE_SIZE}
            onPage={setPage}
            onRowClick={r => setSnap(r.name)}
            empty={<EmptyState title="No vehicles found" />}
          />
        )}
      </div>
      {snap && <VehicleSnapshot open vehicleName={snap} onClose={() => setSnap(null)} />}
    </div>
  )
}
