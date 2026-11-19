import { useEffect, useRef, useState, useMemo } from 'react'
import L from 'leaflet'
import {
  X, Phone, MessageSquare, Bike, Truck, MapPin, Clock, Gauge,
  TrendingUp, Wallet, Package, Activity, ChevronRight, Navigation,
  UserCheck, CalendarDays,
} from 'lucide-react'
import { Modal, Badge, Spinner, EmptyState, SectionTitle, Field, KpiCard } from '../ui'
import { services } from '../../lib/services'
import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import {
  fmtDate, fmtDateTime, fmtRelative, fmtMoney, fmtNum, fmtDuration, initials, todayStr, daysAgo,
} from '../../lib/format'
import { jobStatusColor, availabilityColor, slaColor, priorityColor } from '../../lib/status'

const PERIODS = [
  { key: 'today', label: 'Today' },
  { key: 'week', label: 'This week' },
  { key: 'month', label: 'This month' },
]

function periodRange(key) {
  const t = todayStr()
  if (key === 'today') return [t, t]
  if (key === 'week') return [daysAgo(6), t]
  if (key === 'month') return [daysAgo(29), t]
  return [daysAgo(29), t]
}

export default function RiderSnapshot({ open, riderName, liveRider, onClose, onExpandMap }) {
  const { hasRole } = useAuth()
  const navigate = useNavigate()
  const [snap, setSnap] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('overview')
  const [period, setPeriod] = useState('today')
  const [perf, setPerf] = useState(null)
  const [earnings, setEarnings] = useState(null)
  const [history, setHistory] = useState({ data: [], total: 0 })
  const [timeline, setTimeline] = useState([])
  const [histStart, setHistStart] = useState(0)
  const [assignOpen, setAssignOpen] = useState(false)

  const canManage = hasRole('Delivery Manager', 'Delivery Dispatcher', 'Delivery Supervisor', 'System Manager', 'Fleet Manager')

  useEffect(() => {
    if (!open || !riderName) return
    setLoading(true); setError(null); setTab('overview'); setPeriod('today'); setHistStart(0)
    setSnap(null); setPerf(null); setEarnings(null); setTimeline([])
    services.riderSnapshot(riderName)
      .then(setSnap)
      .catch(e => setError(e))
      .finally(() => setLoading(false))
    services.riderTimeline(riderName, 60).then(r => setTimeline(r.timeline || [])).catch(() => {})
    services.riderHistory(riderName, 0, 15).then(r => setHistory({ data: r.data || [], total: r.total || 0 })).catch(() => {})
  }, [open, riderName])

  const [frm, to] = periodRange(period)
  useEffect(() => {
    if (!open || !riderName) return
    services.riderPerformance(riderName, frm, to).then(setPerf).catch(() => setPerf(null))
    services.riderEarnings(riderName, frm, to).then(setEarnings).catch(() => setEarnings(null))
  }, [open, riderName, frm, to])

  const loadMoreHistory = () => {
    const next = histStart + 15
    services.riderHistory(riderName, next, 15).then(r => {
      setHistory(h => ({ data: [...h.data, ...(r.data || [])], total: r.total || 0 }))
      setHistStart(next)
    }).catch(() => {})
  }

  const rider = snap?.rider
  const live = liveRider || snap?.live
  const job = snap?.current_job

  return (
    <Modal open={open} onClose={onClose} title={null} width="max-w-5xl">
      {loading && !snap ? (
        <div className="flex h-64 items-center justify-center"><Spinner size={22} /></div>
      ) : error ? (
        <div className="p-8 text-center text-sm text-rose-600">{error.message}</div>
      ) : snap && rider ? (
        <div className="flex min-h-0 flex-col">
          {/* header */}
          <div className="border-b border-slate-200 bg-slate-50/60 px-5 py-4">
            <div className="flex items-start gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-slate-900 text-lg font-bold text-white">
                {initials(rider.rider_name || rider.employee || '?')}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-bold text-slate-900">{rider.rider_name || rider.employee}</h2>
                  <Badge className={availabilityColor(live?.status || rider.employment_status)}>
                    {live?.status || rider.employment_status}
                  </Badge>
                  {live?.stale && <Badge className="border-orange-200 bg-orange-50 text-orange-600">Stale GPS</Badge>}
                </div>
                <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
                  <span>ID: {rider.name}</span>
                  {rider.employee && <span>Employee: {rider.employee_name || rider.employee}</span>}
                  {rider.mobile_number && <span className="flex items-center gap-1"><Phone size={11} />{rider.mobile_number}</span>}
                  {snap.vehicle?.license_plate && (
                    <span className="flex items-center gap-1">
                      {snap.vehicle.vehicle_type === 'Motorcycle' ? <Bike size={11} /> : <Truck size={11} />}
                      {snap.vehicle.license_plate} · {snap.vehicle.vehicle_type}
                    </span>
                  )}
                  {job && <span className="text-sky-600">Job: {job.name} · {job.status}</span>}
                  {snap.shift?.shift_status === 'Active' && <span className="flex items-center gap-1 text-emerald-600"><Clock size={11} />On shift</span>}
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap gap-1.5">
                {canManage && (
                  <button onClick={() => { setAssignOpen(true) }} className="rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-slate-700">Assign delivery</button>
                )}
                {rider.mobile_number && (
                  <a href={`tel:${rider.mobile_number}`} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">Call</a>
                )}
                {rider.mobile_number && (
                  <a href={`sms:${rider.mobile_number}`} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">Message</a>
                )}
                <button onClick={() => navigate('/riders')} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">Full profile</button>
                <button onClick={onClose} className="rounded-md p-1.5 text-slate-400 hover:bg-slate-200"><X size={16} /></button>
              </div>
            </div>

            {/* tabs */}
            <div className="mt-3 flex gap-1 border-b border-slate-200">
              {[['overview', 'Overview'], ['performance', 'Performance'], ['earnings', 'Earnings'], ['deliveries', 'Deliveries'], ['activity', 'Activity']].map(([k, l]) => (
                <button key={k} onClick={() => setTab(k)}
                  className={`border-b-2 px-3 py-1.5 text-xs font-medium ${tab === k ? 'border-sky-500 text-sky-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>
                  {l}
                </button>
              ))}
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-5">
            {tab === 'overview' && <OverviewTab snap={snap} live={live} onExpandMap={onExpandMap} />}
            {tab === 'performance' && <PerformanceTab perf={perf} period={period} setPeriod={setPeriod} />}
            {tab === 'earnings' && <EarningsTab earnings={earnings} period={period} setPeriod={setPeriod} />}
            {tab === 'deliveries' && (
              <DeliveriesTab history={history} onLoadMore={loadMoreHistory} onJobClick={(j) => navigate(`/deliveries?q=${encodeURIComponent(j.name)}`)} />
            )}
            {tab === 'activity' && <ActivityTab timeline={timeline} />}
          </div>
        </div>
      ) : null}

      {assignOpen && riderName && (
        <AssignDialog rider={riderName} riderName={rider?.rider_name || riderName} onClose={() => setAssignOpen(false)} />
      )}
    </Modal>
  )
}

/* ---------------- Overview tab ---------------- */

function OverviewTab({ snap, live, onExpandMap }) {
  const live2 = snap.live
  const st = live?.status || live2?.status
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      <div className="space-y-5 lg:col-span-2">
        {/* live operational snapshot */}
        <div>
          <SectionTitle>Live status</SectionTitle>
          <div className="grid grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-3">
            <Field label="Status"><Badge className={availabilityColor(st)}>{st}</Badge></Field>
            <Field label="Location">
              {live2?.latitude != null ? (
                <span className="flex items-center gap-1 text-xs"><MapPin size={11} className="text-sky-500" />{fmtNum(live2.latitude, 5)}, {fmtNum(live2.longitude, 5)}</span>
              ) : 'No location'}
            </Field>
            <Field label="Last update">{fmtRelative(live2?.last_updated)}{live2?.stale ? ' (stale)' : ''}</Field>
            <Field label="Speed">{live2?.speed != null ? `${fmtNum(live2.speed, 1)} km/h` : '—'}</Field>
            <Field label="GPS accuracy">{live2?.accuracy != null ? `±${fmtNum(live2.accuracy, 0)} m` : '—'}</Field>
            <Field label="Current job">{snap.current_job ? <span className="font-mono text-xs">{snap.current_job.name}</span> : 'None'}</Field>
            <Field label="Batch">{snap.current_job?.delivery_batch || '—'}</Field>
            <Field label="Destination">{snap.current_job?.customer_name || '—'}</Field>
            <Field label="Shift">
              {snap.shift?.shift_status === 'Active'
                ? `Active since ${fmtDateTime(snap.shift.actual_clock_in)}`
                : snap.shift?.shift_status || 'Off shift'}
            </Field>
          </div>
        </div>

        {/* today stats */}
        <div>
          <SectionTitle>Today</SectionTitle>
          <div className="grid grid-cols-4 gap-2">
            <MiniStat label="Assigned" value={snap.today.total} />
            <MiniStat label="Completed" value={snap.today.completed} tone="emerald" />
            <MiniStat label="Failed" value={snap.today.failed} tone="rose" />
            <MiniStat label="Pending" value={snap.today.pending} tone="sky" />
          </div>
        </div>

        {/* active jobs */}
        <div>
          <SectionTitle>Active deliveries ({snap.active_jobs?.length || 0})</SectionTitle>
          <div className="space-y-1.5">
            {(snap.active_jobs || []).length === 0 && <EmptyState title="No active deliveries" hint="This rider has no deliveries in progress." />}
            {(snap.active_jobs || []).map(j => (
              <div key={j.name} className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2">
                <div className="min-w-0">
                  <div className="font-mono text-xs font-medium text-slate-800">{j.name}</div>
                  <div className="truncate text-[11px] text-slate-500">{j.customer_name} · {j.delivery_zone || 'no zone'}</div>
                </div>
                <Badge className={jobStatusColor(j.status)}>{j.status}</Badge>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-5">
        {/* vehicle */}
        <div>
          <SectionTitle>Vehicle</SectionTitle>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            {snap.vehicle ? (
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Truck size={16} className="text-slate-400" />
                  <span className="font-semibold">{snap.vehicle.license_plate || snap.vehicle.name}</span>
                  <Badge className="border-slate-200 bg-slate-50 text-slate-600">{snap.vehicle.vehicle_type}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
                  <span>Odometer: {snap.vehicle.last_odometer != null ? `${fmtNum(snap.vehicle.last_odometer)} km` : '—'}</span>
                  <span>Fuel: {snap.vehicle.fuel_type || '—'}</span>
                  <span>Make/Model: {[snap.vehicle.make, snap.vehicle.model].filter(Boolean).join(' ') || '—'}</span>
                  <span>Location: {snap.vehicle.location || '—'}</span>
                </div>
                {snap.fleet_assignment?.assignment_start && (
                  <div className="text-[11px] text-slate-400">Assigned since {fmtDate(snap.fleet_assignment.assignment_start)}</div>
                )}
              </div>
            ) : <EmptyState title="No vehicle assigned" />}
          </div>
        </div>

        {/* mini map */}
        <div>
          <SectionTitle right={
            <button onClick={onExpandMap} className="flex items-center gap-1 text-[11px] font-medium text-sky-600 hover:underline">
              <Navigation size={11} /> Expand
            </button>
          }>Location</SectionTitle>
          <MiniMap snap={snap} />
        </div>

        {/* shift */}
        <div>
          <SectionTitle>Shift</SectionTitle>
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
            {snap.shift ? (
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between"><span className="text-slate-500">Status</span><Badge className={snap.shift.shift_status === 'Active' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'}>{snap.shift.shift_status}</Badge></div>
                <div className="flex justify-between"><span className="text-slate-500">Clock in</span><span>{fmtDateTime(snap.shift.actual_clock_in)}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Clock out</span><span>{fmtDateTime(snap.shift.actual_clock_out)}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Working hours</span><span>{fmtNum(snap.shift.total_working_hours, 1)}h</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Distance</span><span>{fmtNum(snap.shift.total_distance_travelled, 1)} km</span></div>
              </div>
            ) : <EmptyState title="No shift today" />}
          </div>
        </div>
      </div>
    </div>
  )
}

function MiniStat({ label, value, tone }) {
  const tones = { emerald: 'text-emerald-600', rose: 'text-rose-600', sky: 'text-sky-600' }
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-center">
      <div className={`text-lg font-bold tabular-nums ${tones[tone] || 'text-slate-800'}`}>{value ?? 0}</div>
      <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{label}</div>
    </div>
  )
}

function MiniMap({ snap }) {
  const ref = useRef(null)
  const mapRef = useRef(null)
  useEffect(() => {
    if (!ref.current || mapRef.current) return
    const lat = snap.live?.latitude ?? snap.current_job?.latitude
    const lng = snap.live?.longitude ?? snap.current_job?.longitude
    const map = L.map(ref.current, { zoomControl: false, attributionControl: false })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map)
    mapRef.current = map
    const pts = []
    if (snap.live?.latitude != null) {
      L.marker([snap.live.latitude, snap.live.longitude], {
        icon: L.divIcon({ className: 'lc-marker', html: `<div style="width:16px;height:16px;border-radius:9999px;background:#3b82f6;border:3px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.4)"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] }),
      }).addTo(map); pts.push([snap.live.latitude, snap.live.longitude])
    }
    if (snap.current_job?.latitude != null) {
      L.marker([snap.current_job.latitude, snap.current_job.longitude], {
        icon: L.divIcon({ className: 'lc-marker', html: `<div style="width:16px;height:16px;border-radius:9999px;background:#f43f5e;border:3px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.4)"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] }),
      }).addTo(map); pts.push([snap.current_job.latitude, snap.current_job.longitude])
      L.polyline(pts, { color: '#94a3b8', weight: 2, dashArray: '4 4' }).addTo(map)
    }
    if (pts.length === 1) map.setView(pts[0], 13)
    else if (pts.length > 1) map.fitBounds(L.latLngBounds(pts).pad(0.3))
    else map.setView([0, 20], 2)
    setTimeout(() => map.invalidateSize(), 50)
    return () => { map.remove(); mapRef.current = null }
  }, [snap])
  return <div ref={ref} className="h-44 w-full rounded-lg border border-slate-200" />
}

/* ---------------- Performance tab ---------------- */

function PerformanceTab({ perf, period, setPeriod }) {
  const d = perf?.rider
  const assessment = useMemo(() => {
    if (!d) return null
    const rows = [
      { label: 'Delivery efficiency', value: d.deliveries_per_working_hour != null ? `${fmtNum(d.deliveries_per_working_hour, 1)} /hr` : '—', score: d.deliveries_per_working_hour },
      { label: 'Timeliness (on-time proxy)', value: fmtNum(d.completion_rate, 0) + '% completion', score: d.completion_rate },
      { label: 'First-attempt success', value: fmtNum(d.first_attempt_success_rate, 0) + '%', score: d.first_attempt_success_rate },
      { label: 'Avg delivery time', value: fmtDuration(d.avg_delivery_duration_min), score: d.avg_delivery_duration_min },
      { label: 'Customer rating', value: d.avg_customer_rating != null ? fmtNum(d.avg_customer_rating, 1) : 'Not collected', score: d.avg_customer_rating },
    ]
    return rows
  }, [perf])

  return (
    <div>
      <div className="mb-3 flex items-center gap-1">
        {PERIODS.map(p => (
          <button key={p.key} onClick={() => setPeriod(p.key)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${period === p.key ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
            {p.label}
          </button>
        ))}
        <span className="ml-auto text-[11px] text-slate-400">Score = 60% completion rate + 40% first-attempt success</span>
      </div>
      {!d ? (
        <EmptyState title="No performance data" hint="No delivery jobs found for this rider in the selected period." />
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            <KpiCard label="Total deliveries" value={d.total_assigned ?? 0} />
            <KpiCard label="Completed" value={d.completed ?? 0} />
            <KpiCard label="Failed" value={d.failed ?? 0} />
            <KpiCard label="Success rate" value={`${fmtNum(d.completion_rate, 1)}%`} />
            <KpiCard label="First-attempt success" value={`${fmtNum(d.first_attempt_success_rate, 1)}%`} />
            <KpiCard label="Avg delivery time" value={fmtDuration(d.avg_delivery_duration_min)} />
            <KpiCard label="Distance covered" value={`${fmtNum(d.total_distance_km, 1)} km`} />
            <KpiCard label="Deliveries / working hr" value={fmtNum(d.deliveries_per_working_hour, 2)} />
            <KpiCard label="Avg customer rating" value={d.avg_customer_rating != null ? fmtNum(d.avg_customer_rating, 1) : '—'} />
            <KpiCard label="Working hours" value={fmtNum(d.active_working_hours, 1)} />
            <KpiCard label="Performance score" value={fmtNum(d.performance_score, 1)} />
            <KpiCard label="Accepted" value={d.total_accepted ?? 0} />
          </div>
          <SectionTitle>Performance assessment</SectionTitle>
          <div className="overflow-hidden rounded-lg border border-slate-200">
            {assessment.map(r => (
              <div key={r.label} className="flex items-center justify-between border-b border-slate-100 px-3 py-2 text-sm last:border-0">
                <span className="text-slate-600">{r.label}</span>
                <span className="font-medium text-slate-800">{r.value}</span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            Composite performance score = completion_rate × 0.6 + first_attempt_success_rate × 0.4, computed server-side from Delivery Job records.
          </p>
        </>
      )}
    </div>
  )
}

/* ---------------- Earnings tab ---------------- */

function EarningsTab({ earnings, period, setPeriod }) {
  const s = earnings?.summary
  return (
    <div>
      <div className="mb-3 flex items-center gap-1">
        {PERIODS.map(p => (
          <button key={p.key} onClick={() => setPeriod(p.key)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${period === p.key ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
            {p.label}
          </button>
        ))}
      </div>
      {!s ? <Spinner /> : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <KpiCard label="Delivery charges" value={fmtMoney(s.total_delivery_charges)} />
            <KpiCard label="Delivery revenue" value={fmtMoney(s.total_delivery_revenue)} />
            <KpiCard label="Expenses" value={fmtMoney(s.total_expenses)} />
            <KpiCard label="Reimbursed" value={fmtMoney(s.expenses_reimbursed)} />
            <KpiCard label="Net (calculated)" value={fmtMoney(s.net_calculated)} />
            <KpiCard label="Completed deliveries" value={s.deliveries_completed} />
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200">
              <div className="border-b border-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">Expenses by type</div>
              {(earnings.expenses_by_type || []).length === 0
                ? <div className="p-3 text-xs text-slate-400">No expenses recorded</div>
                : earnings.expenses_by_type.map(e => (
                  <div key={e.type} className="flex justify-between border-b border-slate-50 px-3 py-1.5 text-xs last:border-0">
                    <span className="text-slate-600">{e.type}</span><span className="font-medium">{fmtMoney(e.amount)}</span>
                  </div>
                ))}
            </div>
            <div className="rounded-lg border border-slate-200">
              <div className="border-b border-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">Expenses by status</div>
              {(earnings.expenses_by_status || []).length === 0
                ? <div className="p-3 text-xs text-slate-400">No expenses recorded</div>
                : earnings.expenses_by_status.map(e => (
                  <div key={e.status} className="flex justify-between border-b border-slate-50 px-3 py-1.5 text-xs last:border-0">
                    <span className="text-slate-600">{e.status}</span><span className="font-medium">{fmtMoney(e.amount)}</span>
                  </div>
                ))}
            </div>
          </div>
          <p className="rounded-md bg-slate-50 px-3 py-2 text-[11px] text-slate-500">{earnings.note}</p>
        </div>
      )}
    </div>
  )
}

/* ---------------- Deliveries tab ---------------- */

function DeliveriesTab({ history, onLoadMore, onJobClick }) {
  return (
    <div>
      <SectionTitle>Delivery history ({history.total})</SectionTitle>
      <div className="space-y-1.5">
        {history.data.length === 0 && <EmptyState title="No deliveries" />}
        {history.data.map(j => (
          <button key={j.name} onClick={() => onJobClick(j)}
            className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-left hover:bg-slate-50">
            <div className="min-w-0">
              <div className="font-mono text-xs font-medium text-slate-800">{j.name}</div>
              <div className="truncate text-[11px] text-slate-500">
                {j.customer_name} · {fmtDate(j.scheduled_date)} · {j.number_of_attempts || 0} attempts
              </div>
            </div>
            <div className="flex items-center gap-2">
              {j.actual_duration != null && <span className="text-[11px] text-slate-400">{fmtDuration(j.actual_duration)}</span>}
              <Badge className={jobStatusColor(j.status)}>{j.status}</Badge>
              <ChevronRight size={13} className="text-slate-300" />
            </div>
          </button>
        ))}
      </div>
      {history.data.length < history.total && (
        <button onClick={onLoadMore} className="mt-3 w-full rounded-md border border-slate-200 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50">
          Load more
        </button>
      )}
    </div>
  )
}

/* ---------------- Activity tab ---------------- */

function ActivityTab({ timeline }) {
  return (
    <div>
      <SectionTitle>Activity timeline</SectionTitle>
      <div className="relative ml-2 space-y-3 border-l border-slate-200 pl-5">
        {timeline.length === 0 && <EmptyState title="No activity" />}
        {timeline.map((e, i) => (
          <div key={i} className="timeline-dot relative">
            <div className="text-xs font-medium text-slate-800">{e.title}</div>
            <div className="text-[11px] text-slate-500">
              {e.delivery_job && <span className="font-mono">{e.delivery_job} · </span>}
              {e.detail}
            </div>
            <div className="text-[10px] text-slate-400">{fmtDateTime(e.at)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ---------------- Assign dialog ---------------- */

function AssignDialog({ rider, riderName, onClose }) {
  const [riders, setRiders] = useState(null)
  const [jobs, setJobs] = useState(null)
  const [selectedJob, setSelectedJob] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    services.availableRiders().then(r => setRiders(r.riders || [])).catch(() => setRiders([]))
    services.listDoctype({
      doctype: 'Delivery Job',
      filters: { status: ['in', ['Pending', 'Dispatched']], rider_profile: ['is', 'not set'], driver: ['is', 'not set'] },
      fields: 'name,customer_name,status,priority,scheduled_date',
      orderBy: 'scheduled_date asc', limit: 100,
    }).then(r => setJobs(r.data || [])).catch(() => setJobs([]))
  }, [])

  const doAssign = async () => {
    if (!selectedJob) return
    setBusy(true); setMsg(null)
    try {
      await services.assignDelivery(selectedJob, rider)
      setMsg({ ok: true, text: `Assigned ${selectedJob} to ${riderName}` })
      setTimeout(onClose, 1200)
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    } finally { setBusy(false) }
  }

  return (
    <Modal open onClose={onClose} title={`Assign delivery to ${riderName}`} width="max-w-lg">
      <div className="space-y-3 p-5">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Unassigned delivery</label>
          <select value={selectedJob} onChange={e => setSelectedJob(e.target.value)} className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm">
            <option value="">Select a delivery…</option>
            {(jobs || []).map(j => (
              <option key={j.name} value={j.name}>{j.name} · {j.customer_name} · {j.status} · {j.scheduled_date}</option>
            ))}
          </select>
          {jobs && jobs.length === 0 && <p className="mt-1 text-xs text-slate-400">No unassigned pending deliveries.</p>}
        </div>
        {riders && (
          <div className="rounded-md bg-slate-50 p-2.5 text-xs text-slate-600">
            Rider availability: <span className="font-medium">{riders.find(r => r.rider === rider)?.availability_status || '—'}</span>
            {riders.find(r => r.rider === rider)?.active_job_count > 0 && (
              <span className="text-amber-600"> · {riders.find(r => r.rider === rider).active_job_count} active job(s)</span>
            )}
          </div>
        )}
        {msg && <div className={`rounded-md px-3 py-2 text-xs ${msg.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{msg.text}</div>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600">Cancel</button>
          <button onClick={doAssign} disabled={!selectedJob || busy} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40">
            {busy ? 'Assigning…' : 'Assign'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
