import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import L from 'leaflet'
import 'leaflet.markercluster'
import {
  ZoomIn, ZoomOut, LocateFixed, Maximize2, Minimize2, Layers, Filter,
  Eye, EyeOff, Bike, Truck, Package, Route as RouteIcon, X,
} from 'lucide-react'
import { riderStatusColor } from '../../lib/status'
import { initials, fmtRelative, fmtNum } from '../../lib/format'
import { services } from '../../lib/services'

const TILE_LAYERS = {
  street: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri, Maxar, Earthstar Geographics',
    maxZoom: 19,
  },
}

const STATUS_LABEL = {
  Available: 'Available', 'On Delivery': 'On delivery', Busy: 'Busy',
  'On Break': 'On break', Offline: 'Offline', Delayed: 'Delayed', Stale: 'Stale location',
}

function riderIcon(r) {
  const color = riderStatusColor(r.status)
  const border = r.stale ? '#f97316' : '#fff'
  return L.divIcon({
    className: 'lc-marker',
    html: `<div style="
      width:34px;height:34px;border-radius:9999px;
      background:${color};color:#fff;border:2.5px solid ${border};
      display:flex;align-items:center;justify-content:center;
      font-size:11px;font-weight:700;box-shadow:0 1px 4px rgba(0,0,0,.35);
      position:relative;">
      ${initials(r.rider_name || r.rider)}
      <span style="position:absolute;bottom:-3px;right:-3px;width:12px;height:12px;border-radius:9999px;background:#fff;border:2px solid ${color};display:flex;align-items:center;justify-content:center;font-size:8px;color:${color}">${r.vehicle_type === 'Motorcycle' ? '🏍' : r.vehicle_type === 'Truck' ? '🚚' : '🚐'}</span>
    </div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  })
}

function deliveryIcon(d) {
  const isDelayed = (d.delay_minutes || 0) > 0 || d.sla_status === 'Breached'
  const isHigh = d.priority === 'High' || d.priority === 'Urgent'
  const bg = isDelayed ? '#f43f5e' : isHigh ? '#f59e0b' : '#0ea5e9'
  return L.divIcon({
    className: 'lc-marker',
    html: `<div style="
      width:26px;height:26px;border-radius:8px;background:${bg};color:#fff;
      border:2px solid #fff;display:flex;align-items:center;justify-content:center;
      font-size:11px;font-weight:800;box-shadow:0 1px 4px rgba(0,0,0,.35);">
      ${d.status === 'Completed' ? '✓' : '📦'}
    </div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -14],
  })
}

function vehicleIcon(v) {
  return L.divIcon({
    className: 'lc-marker',
    html: `<div style="
      width:30px;height:30px;border-radius:8px;background:#0f172a;color:#fff;
      border:2px solid #94a3b8;display:flex;align-items:center;justify-content:center;
      box-shadow:0 1px 4px rgba(0,0,0,.35);">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 17h4V5H2v12h3"/><path d="M20 17h2v-3.34a4 4 0 0 0-1.17-2.83L19 9h-5v8h1"/><circle cx="7.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/></svg>
    </div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -16],
  })
}

const VIEW_MODES = [
  { key: 'riders', label: 'Riders', icon: Bike },
  { key: 'deliveries', label: 'Deliveries', icon: Package },
  { key: 'vehicles', label: 'Vehicles', icon: Truck },
  { key: 'combined', label: 'Combined', icon: RouteIcon },
]

export default function LiveMap({
  riders = [], vehicles = [], deliveries = [], zones = [],
  onRiderClick, onDeliveryClick, onVehicleClick,
  selectedRider, selectedDelivery,
  className = '',
}) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const layersRef = useRef({ riders: null, deliveries: null, vehicles: null, zones: null, route: null })
  const tileRef = useRef(null)

  const [view, setView] = useState('combined')
  const [tile, setTile] = useState('street')
  const [showZones, setShowZones] = useState(true)
  const [filters, setFilters] = useState({ status: '', vehicleType: '', jobStatus: '', zone: '', delayedOnly: false })
  const [filterOpen, setFilterOpen] = useState(false)
  const [legendOpen, setLegendOpen] = useState(true)
  const [fullscreen, setFullscreen] = useState(false)
  const [routeInfo, setRouteInfo] = useState(null)

  // init map once
  useEffect(() => {
    if (mapRef.current || !containerRef.current) return
    const map = L.map(containerRef.current, {
      zoomControl: false,
      attributionControl: true,
    }).setView([ -1.286389, 36.817223 ], 6) // Nairobi default
    mapRef.current = map

    tileRef.current = L.tileLayer(TILE_LAYERS.street.url, {
      attribution: TILE_LAYERS.street.attribution,
      maxZoom: TILE_LAYERS.street.maxZoom,
    }).addTo(map)

    layersRef.current.riders = L.markerClusterGroup({
      chunkedLoading: true, maxClusterRadius: 45, spiderfyOnMaxZoom: true,
    })
    layersRef.current.deliveries = L.markerClusterGroup({
      chunkedLoading: true, maxClusterRadius: 40,
    })
    layersRef.current.vehicles = L.layerGroup()
    layersRef.current.zones = L.layerGroup()
    layersRef.current.route = L.layerGroup()

    L.control.zoom({ position: 'bottomright' }).addTo(map)
    return () => { map.remove(); mapRef.current = null }
  }, [])

  // tile layer switch
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (tileRef.current) map.removeLayer(tileRef.current)
    tileRef.current = L.tileLayer(TILE_LAYERS[tile].url, {
      attribution: TILE_LAYERS[tile].attribution, maxZoom: TILE_LAYERS[tile].maxZoom,
    }).addTo(map)
  }, [tile])

  const showRiders = view === 'riders' || view === 'combined'
  const showDeliveries = view === 'deliveries' || view === 'combined'
  const showVehicles = view === 'vehicles' || view === 'combined'

  const filteredRiders = useMemo(() => riders.filter(r => {
    if (filters.status && r.status !== filters.status) return false
    if (filters.vehicleType && r.vehicle_type !== filters.vehicleType) return false
    if (filters.delayedOnly && r.status !== 'Delayed') return false
    if (filters.zone) {
      // zone filter applies to deliveries mainly; riders match via current job zone (not present) — skip
    }
    return true
  }), [riders, filters])

  const filteredDeliveries = useMemo(() => deliveries.filter(d => {
    if (filters.jobStatus && d.status !== filters.jobStatus) return false
    if (filters.zone && d.delivery_zone !== filters.zone && d.zone !== filters.zone) return false
    if (filters.delayedOnly && !((d.delay_minutes || 0) > 0 || d.sla_status === 'Breached')) return false
    if (filters.vehicleType) {
      // deliveries don't carry vehicle_type; resolve via vehicle list
      const v = vehicles.find(x => x.vehicle === d.vehicle)
      if (v && v.vehicle_type !== filters.vehicleType) return false
    }
    return true
  }), [deliveries, vehicles, filters])

  // rebuild marker layers when data/filters/view change
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const { riders: rl, deliveries: dl, vehicles: vl, zones: zl, route } = layersRef.current

    // riders
    rl.clearLayers()
    if (showRiders) {
      filteredRiders.forEach(r => {
        if (r.latitude == null || r.longitude == null) return
        const m = L.marker([r.latitude, r.longitude], { icon: riderIcon(r) })
        m.bindPopup(`
          <div style="min-width:160px;font-family:inherit">
            <div style="font-weight:700;font-size:13px">${r.rider_name || r.rider}</div>
            <div style="font-size:11px;color:#64748b">${STATUS_LABEL[r.status] || r.status}${r.stale ? ' · stale' : ''}</div>
            <div style="font-size:11px;color:#64748b;margin-top:4px">${r.license_plate || r.vehicle || ''} · updated ${fmtRelative(r.last_updated)}</div>
            ${r.current_job ? `<div style="font-size:11px;margin-top:4px"><a href="#" onclick="return false" class="lc-open-rider" data-rider="${r.rider}">Open profile</a></div>` : ''}
          </div>`)
        m.on('click', () => onRiderClick?.(r))
        rl.addLayer(m)
      })
    }

    // deliveries
    dl.clearLayers()
    if (showDeliveries) {
      filteredDeliveries.forEach(d => {
        if (d.latitude == null || d.longitude == null) return
        const m = L.marker([d.latitude, d.longitude], { icon: deliveryIcon(d) })
        m.bindPopup(`
          <div style="min-width:170px;font-family:inherit">
            <div style="font-weight:700;font-size:13px">${d.name}</div>
            <div style="font-size:11px;color:#64748b">${d.customer_name || d.customer || ''}</div>
            <div style="font-size:11px;color:#64748b;margin-top:2px">${d.status}${d.priority && d.priority !== 'Normal' ? ' · ' + d.priority : ''}${(d.delay_minutes || 0) > 0 ? ` · ${d.delay_minutes}m late` : ''}</div>
            <div style="font-size:11px;margin-top:4px"><a href="#" class="lc-open-delivery" data-job="${d.name}">Open delivery</a></div>
          </div>`)
        m.on('click', () => onDeliveryClick?.(d))
        dl.addLayer(m)
      })
    }

    // vehicles
    vl.clearLayers()
    if (showVehicles) {
      vehicles.forEach(v => {
        if (v.latitude == null || v.longitude == null) return
        const m = L.marker([v.latitude, v.longitude], { icon: vehicleIcon(v) })
        m.bindPopup(`
          <div style="min-width:160px;font-family:inherit">
            <div style="font-weight:700;font-size:13px">${v.license_plate || v.vehicle}</div>
            <div style="font-size:11px;color:#64748b">${v.vehicle_type || ''}${v.rider_name ? ' · ' + v.rider_name : ''}</div>
            <div style="font-size:11px;color:#64748b;margin-top:4px">updated ${fmtRelative(v.last_updated)}</div>
          </div>`)
        m.on('click', () => onVehicleClick?.(v))
        vl.addLayer(m)
      })
    }

    // zones
    zl.clearLayers()
    if (showZones && filters.zone === '') {
      zones.forEach(z => {
        if (z.latitude == null || z.longitude == null) return
        const circle = L.circle([z.latitude, z.longitude], {
          radius: (z.radius || 5) * 1000,
          color: '#6366f1', weight: 1.5, dashArray: '6 6',
          fillColor: '#6366f1', fillOpacity: 0.06,
        })
        circle.bindTooltip(z.zone_name || z.name, { permanent: false })
        zl.addLayer(circle)
      })
    }

    // ensure layers on map
    if (!map.hasLayer(rl)) rl.addTo(map)
    if (!map.hasLayer(dl)) dl.addTo(map)
    if (!map.hasLayer(vl)) vl.addTo(map)
    if (showZones && !map.hasLayer(zl)) zl.addTo(map)
    if (!showZones && map.hasLayer(zl)) map.removeLayer(zl)

    // fit bounds once when data first arrives
    if (!layersRef.current._fitDone) {
      const pts = []
      filteredRiders.forEach(r => r.latitude != null && pts.push([r.latitude, r.longitude]))
      filteredDeliveries.forEach(d => d.latitude != null && pts.push([d.latitude, d.longitude]))
      if (pts.length) {
        map.fitBounds(L.latLngBounds(pts).pad(0.15))
        layersRef.current._fitDone = true
      }
    }
  }, [filteredRiders, filteredDeliveries, vehicles, zones, showRiders, showDeliveries, showVehicles, showZones, filters.zone, onRiderClick, onDeliveryClick, onVehicleClick])

  // selected rider route
  useEffect(() => {
    const map = mapRef.current
    const routeLayer = layersRef.current.route
    if (!map || !routeLayer) return
    routeLayer.clearLayers()
    setRouteInfo(null)

    const jobName = selectedDelivery?.name || selectedRider?.current_job
    if (!jobName) return

    let cancelled = false
    services.deliveryRoute(jobName).then(res => {
      if (cancelled || !mapRef.current) return
      const pts = (res.points || []).map(p => [p.latitude, p.longitude])
      if (pts.length > 1) {
        L.polyline(pts, { color: '#0ea5e9', weight: 4, opacity: 0.75 }).addTo(routeLayer)
      }
      const job = res.job || {}
      if (job.latitude != null && job.longitude != null) {
        L.marker([job.latitude, job.longitude], {
          icon: L.divIcon({
            className: 'lc-marker',
            html: `<div style="width:22px;height:22px;border-radius:9999px;background:#fff;border:3px solid #0ea5e9;box-shadow:0 1px 4px rgba(0,0,0,.3)"></div>`,
            iconSize: [22, 22], iconAnchor: [11, 11],
          }),
        }).addTo(routeLayer)
      }
      const dists = pts.slice(1).map((p, i) => {
        const a = pts[i], b = p
        const R = 6371, rad = Math.PI / 180
        const h = Math.sin((b[0]-a[0])*rad/2)**2 + Math.cos(a[0]*rad)*Math.cos(b[0]*rad)*Math.sin((b[1]-a[1])*rad/2)**2
        return 2 * R * Math.asin(Math.sqrt(h))
      })
      setRouteInfo({
        points: pts.length,
        distanceKm: dists.reduce((a, b) => a + b, 0).toFixed(1),
      })
    }).catch(() => {})
    return () => { cancelled = true }
  }, [selectedRider?.rider, selectedRider?.current_job, selectedDelivery?.name])

  const fitAll = useCallback(() => {
    const map = mapRef.current
    if (!map) return
    const pts = []
    riders.forEach(r => r.latitude != null && pts.push([r.latitude, r.longitude]))
    deliveries.forEach(d => d.latitude != null && pts.push([d.latitude, d.longitude]))
    if (pts.length) map.flyToBounds(L.latLngBounds(pts).pad(0.15), { duration: 0.6 })
    else map.setView([0, 20], 2)
  }, [riders, deliveries])

  const toggleFullscreen = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    if (!document.fullscreenElement) { el.requestFullscreen?.(); setFullscreen(true) }
    else { document.exitFullscreen?.(); setFullscreen(false) }
  }, [])

  useEffect(() => {
    const h = () => setFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', h)
    return () => document.removeEventListener('fullscreenchange', h)
  }, [])

  const vehicleTypes = useMemo(() => [...new Set(riders.map(r => r.vehicle_type).filter(Boolean))], [riders])
  const statuses = useMemo(() => [...new Set(riders.map(r => r.status).filter(Boolean))], [riders])
  const jobStatuses = useMemo(() => [...new Set(deliveries.map(d => d.status).filter(Boolean))], [deliveries])
  const zoneOptions = useMemo(() => zones.map(z => ({ value: z.name, label: z.zone_name || z.name })), [zones])

  const anyFilter = filters.status || filters.vehicleType || filters.jobStatus || filters.zone || filters.delayedOnly

  return (
    <div className={`relative flex h-full w-full flex-col ${className}`}>
      {/* map canvas */}
      <div ref={containerRef} className="min-h-0 flex-1" />

      {/* view mode switcher */}
      <div className="absolute left-3 top-3 z-[500] flex overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        {VIEW_MODES.map(v => (
          <button
            key={v.key}
            onClick={() => setView(v.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium ${view === v.key ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-50'}`}
          >
            <v.icon size={13} /> {v.label}
          </button>
        ))}
      </div>

      {/* control buttons */}
      <div className="absolute right-3 top-3 z-[500] flex flex-col gap-1.5">
        <MapBtn onClick={() => mapRef.current?.zoomIn()} title="Zoom in"><ZoomIn size={15} /></MapBtn>
        <MapBtn onClick={() => mapRef.current?.zoomOut()} title="Zoom out"><ZoomOut size={15} /></MapBtn>
        <MapBtn onClick={fitAll} title="Fit all"><LocateFixed size={15} /></MapBtn>
        <MapBtn onClick={() => setTile(t => t === 'street' ? 'satellite' : 'street')} title="Toggle imagery">
          <Layers size={15} />
        </MapBtn>
        <MapBtn onClick={toggleFullscreen} title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
          {fullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
        </MapBtn>
        <MapBtn onClick={() => setFilterOpen(o => !o)} title="Filters" active={!!anyFilter}>
          <Filter size={15} />
        </MapBtn>
        <MapBtn onClick={() => setLegendOpen(o => !o)} title="Legend"><Eye size={15} /></MapBtn>
      </div>

      {/* filter panel */}
      {filterOpen && (
        <div className="absolute right-3 top-[168px] z-[500] w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-800">Map filters</span>
            {anyFilter && <button onClick={() => setFilters({ status: '', vehicleType: '', jobStatus: '', zone: '', delayedOnly: false })} className="text-[11px] text-sky-600 hover:underline">Clear</button>}
          </div>
          <label className="mb-2 block">
            <span className="mb-1 block text-[11px] font-medium text-slate-500">Rider status</span>
            <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))} className="h-7 w-full rounded border border-slate-200 px-1.5 text-xs">
              <option value="">All</option>
              {statuses.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label className="mb-2 block">
            <span className="mb-1 block text-[11px] font-medium text-slate-500">Vehicle type</span>
            <select value={filters.vehicleType} onChange={e => setFilters(f => ({ ...f, vehicleType: e.target.value }))} className="h-7 w-full rounded border border-slate-200 px-1.5 text-xs">
              <option value="">All</option>
              {vehicleTypes.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label className="mb-2 block">
            <span className="mb-1 block text-[11px] font-medium text-slate-500">Delivery status</span>
            <select value={filters.jobStatus} onChange={e => setFilters(f => ({ ...f, jobStatus: e.target.value }))} className="h-7 w-full rounded border border-slate-200 px-1.5 text-xs">
              <option value="">All</option>
              {jobStatuses.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label className="mb-2 block">
            <span className="mb-1 block text-[11px] font-medium text-slate-500">Delivery zone</span>
            <select value={filters.zone} onChange={e => setFilters(f => ({ ...f, zone: e.target.value }))} className="h-7 w-full rounded border border-slate-200 px-1.5 text-xs">
              <option value="">All</option>
              {zoneOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <label className="mb-2 flex items-center gap-2 text-xs text-slate-700">
            <input type="checkbox" checked={filters.delayedOnly} onChange={e => setFilters(f => ({ ...f, delayedOnly: e.target.checked }))} className="accent-rose-500" />
            Delayed only
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input type="checkbox" checked={showZones} onChange={e => setShowZones(e.target.checked)} className="accent-indigo-500" />
            Show delivery zones
          </label>
        </div>
      )}

      {/* legend */}
      {legendOpen && (
        <div className="absolute bottom-6 left-3 z-[500] rounded-xl border border-slate-200 bg-white/95 p-3 shadow-sm backdrop-blur">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-700">Legend</span>
            <button onClick={() => setLegendOpen(false)} className="text-slate-400 hover:text-slate-600"><X size={12} /></button>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-slate-600">
            {Object.entries({ Available: '#10b981', 'On Delivery': '#3b82f6', Busy: '#f59e0b', 'On Break': '#8b5cf6', Offline: '#94a3b8', Delayed: '#f43f5e', Stale: '#f97316' }).map(([k, c]) => (
              <span key={k} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />{k}</span>
            ))}
            <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-[4px] bg-sky-500" />Delivery</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-[4px] bg-amber-500" />Priority</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-[4px] bg-rose-500" />Delayed</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-[4px] bg-slate-900" />Vehicle</span>
          </div>
        </div>
      )}

      {/* stats strip */}
      <div className="absolute bottom-3 left-1/2 z-[500] -translate-x-1/2 rounded-full border border-slate-200 bg-white/95 px-4 py-1.5 text-[11px] font-medium text-slate-600 shadow-sm backdrop-blur">
        {filteredRiders.length} riders · {filteredDeliveries.length} deliveries · {vehicles.length} vehicles
        {routeInfo && <span className="ml-2 text-sky-600">· route {routeInfo.distanceKm} km / {routeInfo.points} pts</span>}
      </div>
    </div>
  )
}

function MapBtn({ children, onClick, title, active }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`flex h-8 w-8 items-center justify-center rounded-lg border bg-white shadow-sm transition-colors ${active ? 'border-sky-400 text-sky-600' : 'border-slate-200 text-slate-600 hover:bg-slate-50'}`}
    >
      {children}
    </button>
  )
}
