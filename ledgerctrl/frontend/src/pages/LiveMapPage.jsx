import { useEffect, useState, useCallback } from 'react'
import { services } from '../lib/services'
import { useFilters } from '../context/FiltersContext'
import LiveMap from '../components/map/LiveMap'
import RiderSnapshot from '../components/snapshots/RiderSnapshot'
import DeliverySnapshot from '../components/snapshots/DeliverySnapshot'
import VehicleSnapshot from '../components/snapshots/VehicleSnapshot'
import { Spinner, ErrorState } from '../components/ui'
import { fmtRelative } from '../lib/format'

export default function LiveMapPage() {
  const { refreshTick } = useFilters()
  const [live, setLive] = useState(null)
  const [deliveries, setDeliveries] = useState([])
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastSync, setLastSync] = useState(null)
  const [snap, setSnap] = useState(null)

  const load = useCallback(async () => {
    try {
      const [l, d] = await Promise.all([services.liveRiders(), services.activeDeliveries()])
      setLive(l); setDeliveries(d.deliveries || []); setLastSync(new Date()); setError(null)
    } catch (e) { setError(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load, refreshTick])
  useEffect(() => {
    const t = setInterval(load, 20000)
    return () => clearInterval(t)
  }, [load])
  useEffect(() => {
    services.listDoctype({ doctype: 'Delivery Zone', filters: { status: 'Active' }, fields: 'name,zone_name,latitude,longitude,radius', limit: 200 })
      .then(r => setZones(r.data || [])).catch(() => {})
  }, [])

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 py-2">
        <h2 className="text-sm font-semibold text-slate-900">Live Map</h2>
        <span className="text-xs text-slate-400">
          {live?.riders?.length ?? 0} riders · {deliveries.length} active deliveries · updated {lastSync ? fmtRelative(lastSync) : '—'}
        </span>
      </div>
      <div className="min-h-0 flex-1">
        {loading && !live ? <div className="flex h-full items-center justify-center"><Spinner size={24} /></div>
          : error && !live ? <div className="flex h-full items-center justify-center"><ErrorState error={error} onRetry={load} /></div>
          : (
            <LiveMap
              riders={live?.riders || []}
              vehicles={live?.vehicles || []}
              deliveries={deliveries}
              zones={zones}
              onRiderClick={(r) => setSnap({ type: 'rider', id: r.rider, live: r })}
              onDeliveryClick={(d) => setSnap({ type: 'delivery', id: d.name })}
              onVehicleClick={(v) => setSnap({ type: 'vehicle', id: v.vehicle })}
            />
          )}
      </div>
      {snap?.type === 'rider' && <RiderSnapshot open riderName={snap.id} liveRider={snap.live} onClose={() => setSnap(null)} />}
      {snap?.type === 'delivery' && <DeliverySnapshot open jobName={snap.id} onClose={() => setSnap(null)} />}
      {snap?.type === 'vehicle' && <VehicleSnapshot open vehicleName={snap.id} onClose={() => setSnap(null)} />}
    </div>
  )
}
