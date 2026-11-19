import { useEffect, useState, useCallback, useRef } from 'react'
import { services } from '../lib/services'
import { useFilters } from '../context/FiltersContext'
import LiveMap from '../components/map/LiveMap'
import RiderSnapshot from '../components/snapshots/RiderSnapshot'
import DeliverySnapshot from '../components/snapshots/DeliverySnapshot'
import VehicleSnapshot from '../components/snapshots/VehicleSnapshot'
import { KpiCard, Spinner, ErrorState } from '../components/ui'
import { fmtRelative, fmtDateTime } from '../lib/format'

const POLL_MS = 20000

export default function CommandCenter() {
  const { from, to, company, branch, refreshTick } = useFilters()
  const [summary, setSummary] = useState(null)
  const [live, setLive] = useState(null)
  const [deliveries, setDeliveries] = useState([])
  const [zones, setZones] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastSync, setLastSync] = useState(null)
  const [selectedRider, setSelectedRider] = useState(null)
  const [selectedDelivery, setSelectedDelivery] = useState(null)
  const [selectedVehicle, setSelectedVehicle] = useState(null)
  const timer = useRef(null)

  const load = useCallback(async (initial = false) => {
    try {
      const [s, l, d] = await Promise.all([
        services.summary(from, to, company, branch),
        services.liveRiders(),
        services.activeDeliveries(),
      ])
      setSummary(s)
      setLive(l)
      setDeliveries(d.deliveries || [])
      setError(null)
      setLastSync(new Date())
      if (initial) setLoading(false)
    } catch (e) {
      setError(e)
      if (initial) setLoading(false)
    }
  }, [from, to, company, branch])

  useEffect(() => {
    setLoading(true)
    load(true)
  }, [load, refreshTick])

  // polling for live ops data (summary refreshes less often)
  useEffect(() => {
    const poll = async () => {
      try {
        const [l, d] = await Promise.all([services.liveRiders(), services.activeDeliveries()])
        setLive(l); setDeliveries(d.deliveries || []); setLastSync(new Date())
      } catch { /* keep stale data, show warning via lastSync age */ }
    }
    timer.current = setInterval(poll, POLL_MS)
    return () => clearInterval(timer.current)
  }, [])

  useEffect(() => {
    services.listDoctype({
      doctype: 'Delivery Zone',
      filters: { status: 'Active' },
      fields: 'name,zone_name,latitude,longitude,radius',
      limit: 200,
    }).then(r => setZones(r.data || [])).catch(() => {})
  }, [])

  const k = summary?.kpis || {}
  const deltas = summary?.deltas || {}

  const riderByName = (name) => (live?.riders || []).find(r => r.rider === name)

  if (loading && !summary) {
    return <div className="flex h-full items-center justify-center"><Spinner size={24} /></div>
  }
  if (error && !summary) {
    return <div className="flex h-full items-center justify-center"><ErrorState error={error} onRetry={() => load(true)} /></div>
  }

  return (
    <div className="flex h-full flex-col">
      {/* KPI strip */}
      <div className="grid shrink-0 grid-cols-2 gap-2 overflow-x-auto border-b border-slate-200 bg-white px-4 py-2.5 sm:grid-cols-3 lg:grid-cols-6 xl:grid-cols-10">
        <KpiCard label="Total riders" value={k.total_riders ?? '—'} hint={`${k.riders_with_location ?? 0} with location`} />
        <KpiCard label="Available" value={k.available_riders ?? '—'} />
        <KpiCard label="Busy" value={k.busy_riders ?? '—'} />
        <KpiCard label="Offline" value={k.offline_riders ?? '—'} />
        <KpiCard label="Active deliveries" value={k.active_deliveries ?? '—'} delta={deltas.active_deliveries} />
        <KpiCard label="Completed" value={k.completed_deliveries ?? '—'} delta={deltas.completed_deliveries} />
        <KpiCard label="Delayed" value={k.delayed_deliveries ?? '—'} />
        <KpiCard label="Failed" value={k.failed_deliveries ?? '—'} delta={deltas.failed_deliveries} />
        <KpiCard label="Active vehicles" value={k.active_vehicles ?? '—'} />
        <KpiCard label="In maintenance" value={k.vehicles_under_maintenance ?? '—'} />
      </div>

      {/* sync strip */}
      <div className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-1.5 text-[11px] text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className={`h-1.5 w-1.5 rounded-full ${lastSync ? 'bg-emerald-500' : 'bg-slate-300'}`} />
          Live ops · updated {lastSync ? fmtRelative(lastSync) : '—'} · polling every {POLL_MS / 1000}s
        </span>
        {from !== to && <span>Period: {from} → {to}</span>}
        {summary?.generated_at && <span className="ml-auto">Summary generated {fmtDateTime(summary.generated_at)}</span>}
      </div>

      {/* map */}
      <div className="min-h-0 flex-1 p-3">
        <LiveMap
          riders={live?.riders || []}
          vehicles={live?.vehicles || []}
          deliveries={deliveries}
          zones={zones}
          selectedRider={selectedRider}
          selectedDelivery={selectedDelivery}
          onRiderClick={(r) => setSelectedRider(r)}
          onDeliveryClick={(d) => setSelectedDelivery(d)}
          onVehicleClick={(v) => setSelectedVehicle(v)}
        />
      </div>

      {/* snapshot dialogs */}
      <RiderSnapshot
        open={!!selectedRider}
        riderName={selectedRider?.rider}
        liveRider={selectedRider}
        onClose={() => setSelectedRider(null)}
        onExpandMap={() => { /* map already shows rider via selection */ }}
      />
      <DeliverySnapshot
        open={!!selectedDelivery}
        jobName={selectedDelivery?.name}
        onClose={() => setSelectedDelivery(null)}
      />
      <VehicleSnapshot
        open={!!selectedVehicle}
        vehicleName={selectedVehicle?.vehicle}
        onClose={() => setSelectedVehicle(null)}
      />
    </div>
  )
}
