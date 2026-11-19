import { useEffect, useState } from 'react'
import { Modal, Badge, Spinner, EmptyState, SectionTitle, Field, KpiCard } from '../ui'
import { services } from '../../lib/services'
import {
  fmtDate, fmtDateTime, fmtRelative, fmtMoney, fmtNum,
} from '../../lib/format'
import { Truck, MapPin, Wrench, Fuel, ClipboardCheck } from 'lucide-react'

export default function VehicleSnapshot({ open, vehicleName, onClose }) {
  const [snap, setSnap] = useState(null)
  const [perf, setPerf] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!open || !vehicleName) return
    setLoading(true); setError(null); setSnap(null); setPerf(null)
    services.vehicleSnapshot(vehicleName)
      .then(setSnap)
      .catch(e => setError(e))
      .finally(() => setLoading(false))
    services.vehiclePerformance(vehicleName).then(setPerf).catch(() => setPerf(null))
  }, [open, vehicleName])

  const v = snap?.vehicle
  const s = snap?.stats_30d

  return (
    <Modal open={open} onClose={onClose} title={null} width="max-w-3xl">
      {loading && !snap ? (
        <div className="flex h-64 items-center justify-center"><Spinner size={22} /></div>
      ) : error ? (
        <div className="p-8 text-center text-sm text-rose-600">{error.message}</div>
      ) : snap && v ? (
        <div className="min-h-0">
          <div className="border-b border-slate-200 bg-slate-50/60 px-5 py-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-900 text-white"><Truck size={18} /></div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-mono text-base font-bold text-slate-900">{v.license_plate || v.name}</h2>
                    <Badge className="border-slate-200 bg-slate-50 text-slate-600">{v.vehicle_type}</Badge>
                    {snap.active_job && <Badge className="border-sky-200 bg-sky-50 text-sky-700">On delivery</Badge>}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    {[v.make, v.model].filter(Boolean).join(' ') || v.name}
                    {snap.assigned_rider_name && <> · Rider: {snap.assigned_rider_name}</>}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="max-h-[70vh] overflow-y-auto p-5">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <KpiCard label="Odometer" value={v.last_odometer != null ? `${fmtNum(v.last_odometer)} km` : '—'} />
              <KpiCard label="Deliveries (30d)" value={s?.completed_deliveries ?? 0} />
              <KpiCard label="Distance (30d)" value={`${fmtNum(s?.distance_km, 1)} km`} />
              <KpiCard label="Fuel cost (30d)" value={fmtMoney(s?.fuel_cost)} />
              <KpiCard label="Fuel efficiency" value={s?.fuel_efficiency_kmpl ? `${fmtNum(s.fuel_efficiency_kmpl, 1)} km/l` : '—'} />
              <KpiCard label="Maintenance (30d)" value={fmtMoney(s?.maintenance_cost)} />
              <KpiCard label="Utilization" value={perf?.fleet?.vehicle_utilization_rate != null ? `${fmtNum(perf.fleet.vehicle_utilization_rate, 0)}%` : '—'} />
              <KpiCard label="Cost / delivery" value={fmtMoney(perf?.vehicle?.vehicle_cost_per_successful_delivery)} />
            </div>

            <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
              <div className="space-y-5">
                <div>
                  <SectionTitle>Details</SectionTitle>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border border-slate-200 p-4">
                    <Field label="Registration">{v.license_plate || '—'}</Field>
                    <Field label="Type">{v.vehicle_type || '—'}</Field>
                    <Field label="Make / Model">{[v.make, v.model].filter(Boolean).join(' ') || '—'}</Field>
                    <Field label="Fuel type">{v.fuel_type || '—'}</Field>
                    <Field label="Chassis no">{v.chassis_no || '—'}</Field>
                    <Field label="Value">{fmtMoney(v.vehicle_value)}</Field>
                    <Field label="Acquired">{fmtDate(v.acquisition_date)}</Field>
                    <Field label="Home location">{v.location || '—'}</Field>
                  </div>
                </div>

                <div>
                  <SectionTitle>Assignment</SectionTitle>
                  <div className="rounded-lg border border-slate-200 p-4">
                    {snap.assignment ? (
                      <div className="space-y-1.5 text-sm">
                        <div className="flex justify-between"><span className="text-slate-500">Rider</span><span className="font-medium">{snap.assigned_rider_name || snap.assignment.rider || snap.assignment.employee}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500">Since</span><span>{fmtDate(snap.assignment.assignment_start)}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500">Opening odometer</span><span>{fmtNum(snap.assignment.opening_odometer)} km</span></div>
                      </div>
                    ) : <EmptyState title="Unassigned" hint="No active fleet assignment." />}
                  </div>
                </div>

                <div>
                  <SectionTitle>Location</SectionTitle>
                  <div className="rounded-lg border border-slate-200 p-4">
                    {snap.last_location?.latitude != null ? (
                      <div className="flex items-center gap-2 text-sm">
                        <MapPin size={14} className="text-sky-500" />
                        <span>{fmtNum(snap.last_location.latitude, 5)}, {fmtNum(snap.last_location.longitude, 5)}</span>
                        <span className="text-xs text-slate-400">· {fmtRelative(snap.last_location.timestamp)}</span>
                      </div>
                    ) : <EmptyState title="No GPS data" hint="No location pings recorded for this vehicle." />}
                    {snap.active_job && (
                      <div className="mt-2 text-xs text-slate-500">Active job: <span className="font-mono">{snap.active_job.name}</span> · {snap.active_job.status}</div>
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-5">
                <div>
                  <SectionTitle right={<ClipboardCheck size={13} className="text-slate-400" />}>Latest inspection</SectionTitle>
                  <div className="rounded-lg border border-slate-200 p-4">
                    {snap.latest_inspection ? (
                      <div className="space-y-1.5 text-sm">
                        <div className="flex justify-between"><span className="text-slate-500">Result</span>
                          <Badge className={snap.latest_inspection.inspection_result === 'Passed' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : snap.latest_inspection.inspection_result === 'Failed' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-amber-200 bg-amber-50 text-amber-700'}>{snap.latest_inspection.inspection_result}</Badge>
                        </div>
                        <div className="flex justify-between"><span className="text-slate-500">Date</span><span>{fmtDateTime(snap.latest_inspection.inspection_date)}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500">Type</span><span>{snap.latest_inspection.inspection_type}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500">Odometer</span><span>{fmtNum(snap.latest_inspection.odometer_reading)} km</span></div>
                        {snap.latest_inspection.defects_identified && <div className="text-xs text-rose-600">Defects: {snap.latest_inspection.defects_identified}</div>}
                      </div>
                    ) : <EmptyState title="No inspections" />}
                  </div>
                </div>

                <div>
                  <SectionTitle right={<Wrench size={13} className="text-slate-400" />}>Next service</SectionTitle>
                  <div className="rounded-lg border border-slate-200 p-4">
                    {snap.next_service ? (
                      <div className="space-y-1.5 text-sm">
                        <div className="flex justify-between"><span className="text-slate-500">Date</span><span>{fmtDate(snap.next_service.next_service_date)}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500">Odometer</span><span>{snap.next_service.next_service_odometer != null ? `${fmtNum(snap.next_service.next_service_odometer)} km` : '—'}</span></div>
                      </div>
                    ) : <EmptyState title="No service scheduled" />}
                  </div>
                </div>

                <div>
                  <SectionTitle right={<Fuel size={13} className="text-slate-400" />}>30-day operating stats</SectionTitle>
                  <div className="rounded-lg border border-slate-200 p-4">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="flex justify-between"><span className="text-slate-500">Fuel qty</span><span>{fmtNum(s?.fuel_quantity, 1)} L</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">Fuel cost</span><span>{fmtMoney(s?.fuel_cost)}</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">Maintenance</span><span>{fmtMoney(s?.maintenance_cost)}</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">Efficiency</span><span>{s?.fuel_efficiency_kmpl ? `${fmtNum(s.fuel_efficiency_kmpl, 1)} km/l` : '—'}</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
