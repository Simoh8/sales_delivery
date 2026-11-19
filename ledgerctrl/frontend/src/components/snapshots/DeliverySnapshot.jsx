import { useEffect, useState } from 'react'
import L from 'leaflet'
import { useRef } from 'react'
import { Modal, Badge, Spinner, EmptyState, SectionTitle, Field } from '../ui'
import { services } from '../../lib/services'
import { useAuth } from '../../context/AuthContext'
import {
  fmtDate, fmtDateTime, fmtTime, fmtRelative, fmtMoney, fmtNum, fmtDuration,
} from '../../lib/format'
import { jobStatusColor, slaColor, priorityColor } from '../../lib/status'
import { Package, MapPin, User, Truck, Route as RouteIcon, Camera, FileCheck } from 'lucide-react'

export default function DeliverySnapshot({ open, jobName, onClose }) {
  const { hasRole } = useAuth()
  const [snap, setSnap] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [route, setRoute] = useState(null)
  const [showRoute, setShowRoute] = useState(false)
  const [reassignOpen, setReassignOpen] = useState(false)

  const canManage = hasRole('Delivery Manager', 'Delivery Dispatcher', 'Delivery Supervisor', 'System Manager', 'Fleet Manager')
  const isTerminal = snap?.job?.status === 'Completed' || snap?.job?.status === 'Cancelled' || snap?.job?.status === 'Failed'

  useEffect(() => {
    if (!open || !jobName) return
    setLoading(true); setError(null); setSnap(null); setRoute(null); setShowRoute(false)
    services.deliverySnapshot(jobName)
      .then(setSnap)
      .catch(e => setError(e))
      .finally(() => setLoading(false))
  }, [open, jobName])

  const loadRoute = () => {
    if (route) { setShowRoute(s => !s); return }
    services.deliveryRoute(jobName).then(r => { setRoute(r); setShowRoute(true) }).catch(() => {})
  }

  const j = snap?.job

  return (
    <Modal open={open} onClose={onClose} title={null} width="max-w-4xl">
      {loading && !snap ? (
        <div className="flex h-64 items-center justify-center"><Spinner size={22} /></div>
      ) : error ? (
        <div className="p-8 text-center text-sm text-rose-600">{error.message}</div>
      ) : snap && j ? (
        <div className="min-h-0">
          {/* header */}
          <div className="border-b border-slate-200 bg-slate-50/60 px-5 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Package size={18} className="text-slate-500" />
                  <h2 className="font-mono text-base font-bold text-slate-900">{j.name}</h2>
                  <Badge className={jobStatusColor(j.status)}>{j.status}</Badge>
                  {j.priority && j.priority !== 'Normal' && <span className={`text-xs font-semibold ${priorityColor(j.priority)}`}>{j.priority}</span>}
                  {j.sla_status && <Badge className="border-slate-200 bg-white">SLA: <span className={slaColor(j.sla_status)}>{j.sla_status}</span></Badge>}
                </div>
                <div className="mt-1 text-sm text-slate-600">{j.customer_name || j.customer}</div>
                <div className="mt-0.5 text-xs text-slate-400">
                  {snap.rider_name && <>Rider: {snap.rider_name} · </>}
                  {snap.vehicle_plate && <>Vehicle: {snap.vehicle_plate} · </>}
                  Zone: {snap.zone_name || j.delivery_zone || '—'}
                </div>
              </div>
              <div className="flex gap-1.5">
                <button onClick={loadRoute} className="flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
                  <RouteIcon size={12} /> {showRoute ? 'Hide route' : 'View route'}
                </button>
                {canManage && !isTerminal && (
                  <button onClick={() => setReassignOpen(true)} className="rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-slate-700">Reassign</button>
                )}
              </div>
            </div>

            {/* timeline strip */}
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-slate-500">
              <span>Scheduled: {fmtDate(j.scheduled_date)} {fmtTime(j.scheduled_time)}</span>
              <span>Dispatched: {fmtDateTime(j.dispatched_at)}</span>
              <span>Accepted: {fmtDateTime(j.accepted_at)}</span>
              <span>En route: {fmtDateTime(j.en_route_at)}</span>
              <span>Arrived: {fmtDateTime(j.arrived_at)}</span>
              <span>Completed: {fmtDateTime(j.completed_at || j.actual_delivery_time)}</span>
              {(j.delay_minutes || 0) > 0 && <span className="font-medium text-rose-600">{j.delay_minutes}m delayed</span>}
            </div>
          </div>

          <div className="max-h-[65vh] overflow-y-auto p-5">
            {showRoute && route && <RouteMap route={route} />}

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              {/* left: details */}
              <div className="space-y-5">
                <div>
                  <SectionTitle>Delivery details</SectionTitle>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border border-slate-200 p-4">
                    <Field label="Customer"><span className="flex items-center gap-1"><User size={11} className="text-slate-400" />{j.customer_name || j.customer}</span></Field>
                    <Field label="Type">{j.delivery_type || '—'}</Field>
                    <Field label="Batch">{j.delivery_batch ? <span className="font-mono text-xs">{j.delivery_batch}</span> : '—'}</Field>
                    <Field label="Attempts">{j.number_of_attempts ?? 0}</Field>
                    <Field label="Distance">{j.actual_distance != null ? `${fmtNum(j.actual_distance, 1)} km` : j.estimated_distance != null ? `est. ${fmtNum(j.estimated_distance, 1)} km` : '—'}</Field>
                    <Field label="Duration">{j.actual_duration != null ? fmtDuration(j.actual_duration) : '—'}</Field>
                    <Field label="Charge">{fmtMoney(j.customer_delivery_charge)}</Field>
                    <Field label="Cost">{fmtMoney(j.actual_delivery_cost)}</Field>
                    <Field label="Revenue">{fmtMoney(j.delivery_revenue)}</Field>
                    <Field label="Payment">{j.payment_status || '—'}</Field>
                  </div>
                </div>

                <div>
                  <SectionTitle>Addresses</SectionTitle>
                  <div className="space-y-2">
                    <div className="flex gap-2 rounded-lg border border-slate-200 p-3 text-sm">
                      <MapPin size={15} className="mt-0.5 shrink-0 text-sky-500" />
                      <div>
                        <div className="text-[11px] font-medium uppercase text-slate-400">Destination</div>
                        <div className="text-slate-700">{j.customer_address || '—'}</div>
                        {j.special_instructions && <div className="mt-1 text-xs text-amber-700">⚠ {j.special_instructions}</div>}
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <SectionTitle>Items ({snap.items?.length || 0})</SectionTitle>
                  {(snap.items || []).length === 0 ? <EmptyState title="No items" /> : (
                    <div className="overflow-hidden rounded-lg border border-slate-200">
                      <table className="w-full text-xs">
                        <thead><tr className="bg-slate-50 text-left text-[10px] uppercase text-slate-500">
                          <th className="px-3 py-1.5">Item</th><th className="px-3 py-1.5">Qty</th><th className="px-3 py-1.5">Rate</th><th className="px-3 py-1.5">Amount</th>
                        </tr></thead>
                        <tbody>
                          {snap.items.map((it, i) => (
                            <tr key={i} className="border-t border-slate-100">
                              <td className="px-3 py-1.5">{it.item_name || it.item_code}</td>
                              <td className="px-3 py-1.5">{it.qty} {it.uom}</td>
                              <td className="px-3 py-1.5">{fmtMoney(it.rate)}</td>
                              <td className="px-3 py-1.5">{fmtMoney(it.amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>

              {/* right: timeline + attempts + POD */}
              <div className="space-y-5">
                <div>
                  <SectionTitle>Event timeline</SectionTitle>
                  <div className="relative ml-2 space-y-2.5 border-l border-slate-200 pl-5">
                    {(snap.events || []).length === 0 && <EmptyState title="No events" />}
                    {(snap.events || []).map(e => (
                      <div key={e.name} className="timeline-dot relative">
                        <div className="text-xs font-medium text-slate-800">{e.event_type}</div>
                        <div className="text-[11px] text-slate-500">
                          {e.old_status && e.new_status ? `${e.old_status} → ` : ''}{e.new_status || e.reason || e.notes || ''}
                        </div>
                        <div className="text-[10px] text-slate-400">{fmtDateTime(e.timestamp)}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {(snap.attempts || []).length > 0 && (
                  <div>
                    <SectionTitle>Attempts</SectionTitle>
                    <div className="space-y-1.5">
                      {snap.attempts.map(a => (
                        <div key={a.name} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs">
                          <div>
                            <span className="font-medium">#{a.attempt_number}</span>
                            <span className="ml-2 text-slate-500">{fmtDateTime(a.completion_time || a.arrival_time)}</span>
                            {a.failure_reason && <div className="text-rose-600">{a.failure_reason}</div>}
                          </div>
                          <Badge className={a.attempt_status === 'Successful' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'}>{a.attempt_status}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(snap.proofs_of_delivery || []).length > 0 && (
                  <div>
                    <SectionTitle right={<FileCheck size={13} className="text-emerald-500" />}>Proof of delivery</SectionTitle>
                    {snap.proofs_of_delivery.map(p => (
                      <div key={p.name} className="rounded-lg border border-slate-200 p-3 text-xs">
                        <div className="flex justify-between">
                          <span className="font-medium">{p.name}</span>
                          <Badge className={p.otp_verification_status === 'Verified' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'}>
                            OTP {p.otp_verification_status}
                          </Badge>
                        </div>
                        <div className="mt-1 text-slate-500">
                          Received by: {p.received_by || p.recipient_name || '—'} · {fmtDateTime(p.delivery_timestamp)}
                        </div>
                        {(p.customer_signature || p.delivery_photograph) && (
                          <div className="mt-2 flex gap-2">
                            {p.customer_signature && <img src={p.customer_signature} className="h-16 rounded border border-slate-200" alt="signature" />}
                            {p.delivery_photograph && <img src={p.delivery_photograph} className="h-16 rounded border border-slate-200" alt="photo" />}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {(snap.stops || []).length > 0 && (
                  <div>
                    <SectionTitle>Stops</SectionTitle>
                    <div className="space-y-1.5">
                      {snap.stops.map(s => (
                        <div key={s.name} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs">
                          <div>
                            <span className="font-medium">#{s.stop_sequence}</span> {s.stop_type}
                            <span className="ml-2 text-slate-500">{s.customer}</span>
                          </div>
                          <Badge className={s.stop_status === 'Completed' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'}>{s.stop_status}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {reassignOpen && jobName && (
        <ReassignDialog jobName={jobName} onClose={() => setReassignOpen(false)} />
      )}
    </Modal>
  )
}

function RouteMap({ route }) {
  const ref = useRef(null)
  const mapRef = useRef(null)
  useEffect(() => {
    if (!ref.current || mapRef.current) return
    const pts = (route.points || []).map(p => [p.latitude, p.longitude])
    const map = L.map(ref.current, { zoomControl: true, attributionControl: false })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map)
    mapRef.current = map
    if (pts.length > 1) {
      L.polyline(pts, { color: '#0ea5e9', weight: 4, opacity: 0.8 }).addTo(map)
      pts.forEach((p, i) => {
        if (i === 0 || i === pts.length - 1) {
          L.circleMarker(p, { radius: 6, color: '#fff', weight: 2, fillColor: i === 0 ? '#10b981' : '#f43f5e', fillOpacity: 1 }).addTo(map)
        }
      })
      map.fitBounds(L.latLngBounds(pts).pad(0.2))
    } else {
      map.setView([0, 20], 2)
    }
    setTimeout(() => map.invalidateSize(), 50)
    return () => { map.remove(); mapRef.current = null }
  }, [route])
  return (
    <div className="mb-4">
      <div ref={ref} className="h-56 w-full rounded-lg border border-slate-200" />
      <div className="mt-1 text-[11px] text-slate-400">
        Actual GPS trail · {route.points?.length || 0} points{route.rider_position ? ' · rider live position available' : ''}
      </div>
    </div>
  )
}

function ReassignDialog({ jobName, onClose }) {
  const [riders, setRiders] = useState(null)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    services.availableRiders().then(r => setRiders(r.riders || [])).catch(() => setRiders([]))
  }, [])

  const doAssign = async () => {
    setBusy(true); setMsg(null)
    try {
      // release current assignment first (server rejects assigning an assigned job)
      try { await services.unassignDelivery(jobName, 'Reassigned via command center') } catch { /* may be unassigned */ }
      await services.assignDelivery(jobName, selected)
      setMsg({ ok: true, text: `Assigned to ${selected}` })
      setTimeout(onClose, 1000)
    } catch (e) { setMsg({ ok: false, text: e.message }) }
    finally { setBusy(false) }
  }

  return (
    <Modal open onClose={onClose} title={`Reassign ${jobName}`} width="max-w-md">
      <div className="space-y-3 p-5">
        <select value={selected} onChange={e => setSelected(e.target.value)} className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm">
          <option value="">Select rider…</option>
          {(riders || []).filter(r => r.eligible || r.availability_status === 'Available').map(r => (
            <option key={r.rider} value={r.rider}>
              {r.rider_name} · {r.availability_status}{r.license_plate ? ` · ${r.license_plate}` : ''}
            </option>
          ))}
        </select>
        {msg && <div className={`rounded-md px-3 py-2 text-xs ${msg.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{msg.text}</div>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600">Cancel</button>
          <button onClick={doAssign} disabled={!selected || busy} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40">
            {busy ? 'Assigning…' : 'Assign'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
