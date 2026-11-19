import { useEffect, useState, useCallback } from 'react'
import { services } from '../lib/services'
import { useFilters } from '../context/FiltersContext'
import LiveMap from '../components/map/LiveMap'
import { Badge, Spinner, EmptyState, ErrorState, Select } from '../components/ui'
import { fmtDate, fmtTime, fmtNum } from '../lib/format'
import { jobStatusColor, availabilityColor, priorityColor } from '../lib/status'
import { Bike, Package, CheckCircle2 } from 'lucide-react'

export default function Dispatch() {
  const { refreshTick } = useFilters()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedJobs, setSelectedJobs] = useState({}) // jobName -> rider
  const [busyJob, setBusyJob] = useState(null)
  const [toast, setToast] = useState(null)
  const [zoneFilter, setZoneFilter] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await services.dispatchBoard()
      setData(res)
      setError(null)
    } catch (e) { setError(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load, refreshTick])

  const zones = [...new Set((data?.unassigned_jobs || []).map(j => j.delivery_zone).filter(Boolean))]
  const jobs = (data?.unassigned_jobs || []).filter(j => !zoneFilter || j.delivery_zone === zoneFilter)
  const riders = data?.riders || []
  const available = riders.filter(r => r.availability_status === 'Available' && !r.has_active_jobs)
  const busyRiders = riders.filter(r => r.availability_status !== 'Available' || r.has_active_jobs)

  const assign = async (jobName, rider) => {
    if (!rider) return
    setBusyJob(jobName)
    try {
      await services.assignDelivery(jobName, rider)
      setToast({ ok: true, text: `Assigned ${jobName} → ${rider}` })
      setSelectedJobs(s => { const n = { ...s }; delete n[jobName]; return n })
      await load()
    } catch (e) {
      setToast({ ok: false, text: `${jobName}: ${e.message}` })
    } finally {
      setBusyJob(null)
      setTimeout(() => setToast(null), 5000)
    }
  }

  const riderName = (id) => riders.find(r => r.rider === id)?.rider_name || id

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 py-2">
        <h2 className="text-sm font-semibold text-slate-900">Dispatch board</h2>
        <span className="text-xs text-slate-400">{jobs.length} unassigned · {available.length} riders available</span>
        <div className="ml-auto flex items-center gap-2">
          <Select value={zoneFilter} onChange={setZoneFilter} options={zones} placeholder="All zones" className="w-40" />
          <button onClick={load} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50">Refresh</button>
        </div>
      </div>

      {toast && (
        <div className={`shrink-0 border-b px-4 py-2 text-xs ${toast.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}`}>
          {toast.text}
        </div>
      )}

      {loading && !data ? (
        <div className="flex flex-1 items-center justify-center"><Spinner size={24} /></div>
      ) : error ? (
        <div className="flex flex-1 items-center justify-center"><ErrorState error={error} onRetry={load} /></div>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-0 lg:grid-cols-[300px_1fr_300px]">
          {/* left: unassigned jobs */}
          <div className="min-h-0 overflow-y-auto border-r border-slate-200 bg-slate-50/50 p-3">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Package size={12} /> Unassigned deliveries
            </div>
            <div className="space-y-2">
              {jobs.length === 0 && <EmptyState title="No unassigned deliveries" hint="All pending deliveries have been assigned." />}
              {jobs.map(j => (
                <div key={j.name} className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold text-slate-800">{j.name}</span>
                    <div className="flex gap-1">
                      <Badge className={jobStatusColor(j.status)}>{j.status}</Badge>
                      {j.priority !== 'Normal' && <span className={`text-[10px] font-bold ${priorityColor(j.priority)}`}>{j.priority}</span>}
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-slate-600">{j.customer_name}</div>
                  <div className="mt-0.5 text-[11px] text-slate-400">
                    {fmtDate(j.scheduled_date)} {fmtTime(j.scheduled_time)}
                    {j.estimated_distance ? ` · ${fmtNum(j.estimated_distance, 1)} km` : ''}
                    {j.delivery_zone ? ` · ${j.delivery_zone}` : ''}
                  </div>
                  <div className="mt-2 flex items-center gap-1.5">
                    <select
                      value={selectedJobs[j.name] || ''}
                      onChange={e => setSelectedJobs(s => ({ ...s, [j.name]: e.target.value }))}
                      className="h-7 min-w-0 flex-1 rounded border border-slate-200 px-1.5 text-[11px]"
                    >
                      <option value="">Assign to…</option>
                      {available.map(r => <option key={r.rider} value={r.rider}>{r.rider_name}</option>)}
                    </select>
                    <button
                      onClick={() => assign(j.name, selectedJobs[j.name])}
                      disabled={!selectedJobs[j.name] || busyJob === j.name}
                      className="flex h-7 items-center gap-1 rounded bg-slate-900 px-2 text-[11px] font-medium text-white disabled:opacity-40"
                    >
                      {busyJob === j.name ? '…' : <CheckCircle2 size={11} />}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* center: map */}
          <div className="hidden min-h-0 lg:block">
            <LiveMap
              riders={riders.filter(r => r.latitude != null).map(r => ({
                rider: r.rider, rider_name: r.rider_name, status: r.has_active_jobs ? 'Busy' : r.availability_status === 'Available' ? 'Available' : 'Offline',
                stale: false, latitude: r.latitude, longitude: r.longitude,
                vehicle_type: r.vehicle_type, license_plate: r.license_plate,
              }))}
              vehicles={[]}
              deliveries={jobs.filter(j => j.latitude != null)}
              zones={[]}
              onRiderClick={() => {}}
              onDeliveryClick={() => {}}
            />
          </div>

          {/* right: riders */}
          <div className="min-h-0 overflow-y-auto border-l border-slate-200 bg-slate-50/50 p-3">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Bike size={12} /> Riders
            </div>
            <div className="mb-2 text-[11px] font-medium text-emerald-600">{available.length} available</div>
            <div className="space-y-1.5">
              {available.map(r => (
                <RiderRow key={r.rider} r={r} />
              ))}
            </div>
            {busyRiders.length > 0 && (
              <>
                <div className="mb-2 mt-4 text-[11px] font-medium text-slate-400">Busy / offline ({busyRiders.length})</div>
                <div className="space-y-1.5 opacity-70">
                  {busyRiders.map(r => <RiderRow key={r.rider} r={r} />)}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function RiderRow({ r }) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-slate-200 bg-white px-2.5 py-2">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800 text-[11px] font-bold text-white">
        {(r.rider_name || '?').slice(0, 1).toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-xs font-medium text-slate-800">{r.rider_name}</div>
        <div className="truncate text-[10px] text-slate-400">
          {r.license_plate || r.vehicle_type || ''}
          {r.active_job_count > 0 && ` · ${r.active_job_count} job(s)`}
        </div>
      </div>
      <Badge className={availabilityColor(r.availability_status)}>{r.availability_status}</Badge>
    </div>
  )
}
