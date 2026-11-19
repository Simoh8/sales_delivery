import { useEffect, useState, useCallback } from 'react'
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { services } from '../lib/services'
import { useFilters } from '../context/FiltersContext'
import { KpiCard, Spinner, ErrorState, DataTable, Badge } from '../components/ui'
import { fmtMoney, fmtNum, fmtDuration, pct } from '../lib/format'
import { jobStatusColor, slaColor } from '../lib/status'
import { useNavigate } from 'react-router-dom'

const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6', '#64748b', '#14b8a6', '#f97316']

export default function Analytics() {
  const { from, to, company, branch, refreshTick } = useFilters()
  const [tab, setTab] = useState('executive')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      let res
      if (tab === 'executive') res = await services.deliveryAnalytics(from, to, { company, branch })
      else if (tab === 'riders') res = await services.riderAnalytics(from, to, { company, branch })
      else if (tab === 'fleet') res = await services.fleetAnalytics(from, to, { company, branch })
      else res = await services.geographicAnalytics(from, to, { company, branch })
      setData(res)
    } catch (e) { setError(e) }
    finally { setLoading(false) }
  }, [tab, from, to, company, branch])

  useEffect(() => { load() }, [load, refreshTick])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-1 border-b border-slate-200 bg-white px-4 py-2">
        {[['executive', 'Executive'], ['riders', 'Riders'], ['fleet', 'Fleet'], ['geo', 'Geographic']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium ${tab === k ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
            {l}
          </button>
        ))}
        <span className="ml-auto text-[11px] text-slate-400">{from} → {to}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {(() => {
          if (loading) return <div className="flex h-64 items-center justify-center"><Spinner size={24} /></div>
          if (error) return <ErrorState error={error} onRetry={load} />
          if (tab === 'executive') return <Executive data={data} />
          if (tab === 'riders') return <Riders data={data} />
          if (tab === 'fleet') return <Fleet data={data} />
          return <Geo data={data} />
        })()}
      </div>
    </div>
  )
}

function Executive({ data }) {
  const k = data?.kpis || {}
  const trends = (data?.trends || []).map(t => ({ ...t, name: t.period }))
  const statusData = (data?.status_distribution || []).map(s => ({ name: s.status, value: s.cnt }))
  const slaData = (data?.sla_compliance || []).map(s => ({ name: s.sla_status, value: s.cnt }))
  const eff = data?.efficiency || {}

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        <KpiCard label="Total deliveries" value={k.total_delivery_jobs ?? 0} />
        <KpiCard label="Completion rate" value={pct(k.delivery_success_rate)} />
        <KpiCard label="First-attempt success" value={pct(k.first_attempt_success_rate)} />
        <KpiCard label="On-time rate" value={pct(k.on_time_delivery_rate)} />
        <KpiCard label="Avg delivery time" value={fmtDuration(k.average_delivery_duration_min)} />
        <KpiCard label="Avg delivery cost" value={fmtMoney(k.average_delivery_cost)} />
        <KpiCard label="Delivery revenue" value={fmtMoney(k.total_delivery_revenue)} />
        <KpiCard label="Delivery expenses" value={fmtMoney(k.total_delivery_expenses)} />
        <KpiCard label="Contribution" value={fmtMoney(k.delivery_contribution)} />
        <KpiCard label="Failed" value={k.failed_deliveries ?? 0} />
        <KpiCard label="Pending" value={k.pending_deliveries ?? 0} />
        <KpiCard label="In transit" value={k.in_transit_deliveries ?? 0} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <ChartCard title="Daily delivery trend" className="xl:col-span-2">
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="completed" name="Completed" stroke="#10b981" fill="#10b981" fillOpacity={0.15} />
              <Area type="monotone" dataKey="failed" name="Failed" stroke="#f43f5e" fill="#f43f5e" fillOpacity={0.1} />
              <Area type="monotone" dataKey="total" name="Total" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.08} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Status distribution">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard title="SLA compliance">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={slaData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Jobs" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 text-[13px] font-semibold text-slate-800">Operational efficiency</div>
          <div className="grid grid-cols-2 gap-2">
            <EffItem label="Assign → accept" value={fmtDuration(eff.avg_assignment_acceptance_min)} />
            <EffItem label="Rider arrival" value={fmtDuration(eff.avg_rider_arrival_min)} />
            <EffItem label="Pickup duration" value={fmtDuration(eff.avg_pickup_duration_min)} />
            <EffItem label="Delivery duration" value={fmtDuration(eff.avg_delivery_duration_min)} />
            <EffItem label="Customer wait" value={fmtDuration(eff.avg_customer_waiting_min)} />
            <EffItem label="Failed rate" value={pct(eff.failed_delivery_rate)} />
            <EffItem label="Multi-attempt rate" value={pct(eff.multi_attempt_rate)} />
            <EffItem label="SLA breaches" value={eff.sla_breach_count ?? 0} />
            <EffItem label="Avg jobs/batch" value={fmtNum(eff.avg_jobs_per_batch, 1)} />
            <EffItem label="Stops/trip" value={fmtNum(eff.avg_stops_per_trip, 1)} />
          </div>
        </div>
      </div>
    </div>
  )
}

function EffItem({ label, value }) {
  return (
    <div className="rounded-md bg-slate-50 px-2.5 py-2">
      <div className="text-[10px] font-medium uppercase text-slate-400">{label}</div>
      <div className="text-sm font-semibold text-slate-800">{value ?? '—'}</div>
    </div>
  )
}

function Riders({ data }) {
  const rows = data?.leaderboard || []
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <KpiCard label="Active riders" value={rows.length} />
        <KpiCard label="Total completed" value={rows.reduce((a, r) => a + (r.completed || 0), 0)} />
        <KpiCard label="Avg score" value={rows.length ? fmtNum(rows.reduce((a, r) => a + (r.performance_score || 0), 0) / rows.length, 1) : '—'} />
        <KpiCard label="Top performer" value={rows[0]?.rider_name || '—'} />
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard title="Rider leaderboard (performance score)">
          <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 34)}>
            <BarChart data={[...rows].reverse()} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="rider_name" width={110} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="performance_score" name="Score" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <div>
          <DataTable
            columns={[
              { key: 'rider_name', label: 'Rider' },
              { key: 'completed', label: 'Done', className: 'text-right' },
              { key: 'completion_rate', label: 'Rate', render: r => pct(r.completion_rate), className: 'text-right' },
              { key: 'first_attempt_success_rate', label: '1st try', render: r => pct(r.first_attempt_success_rate), className: 'text-right' },
              { key: 'avg_delivery_duration_min', label: 'Avg time', render: r => fmtDuration(r.avg_delivery_duration_min), className: 'text-right' },
              { key: 'total_distance_km', label: 'Km', render: r => fmtNum(r.total_distance_km, 0), className: 'text-right' },
              { key: 'performance_score', label: 'Score', render: r => <span className="font-semibold">{fmtNum(r.performance_score, 1)}</span>, className: 'text-right' },
            ]}
            rows={rows}
            pageSize={15}
          />
        </div>
      </div>
    </div>
  )
}

function Fleet({ data }) {
  const f = data?.fleet || {}
  const byVehicle = data?.by_vehicle || []
  const fuelTrends = (data?.fuel_trends || []).map(t => ({ ...t, name: t.period }))
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
        <KpiCard label="Registered vehicles" value={f.total_registered_vehicles ?? 0} />
        <KpiCard label="Active" value={f.active_vehicles ?? 0} />
        <KpiCard label="On delivery" value={f.vehicles_on_delivery ?? 0} />
        <KpiCard label="Utilization" value={pct(f.vehicle_utilization_rate)} />
        <KpiCard label="Distance" value={`${fmtNum(f.total_distance_km, 0)} km`} />
        <KpiCard label="Fuel consumption" value={`${fmtNum(f.total_fuel_consumption, 0)} L`} />
        <KpiCard label="Fuel expenses" value={fmtMoney(f.total_fuel_expenses)} />
        <KpiCard label="Maintenance" value={fmtMoney(f.maintenance_expenses)} />
        <KpiCard label="Cost / km" value={fmtMoney(f.fuel_cost_per_km)} />
        <KpiCard label="Cost / delivery" value={fmtMoney(f.vehicle_cost_per_successful_delivery)} />
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard title="Fuel expenditure trend">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={fuelTrends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="cost" name="Cost" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <div>
          <DataTable
            columns={[
              { key: 'license_plate', label: 'Vehicle', render: r => r.license_plate || r.vehicle },
              { key: 'vehicle_type', label: 'Type' },
              { key: 'deliveries', label: 'Deliveries', className: 'text-right' },
              { key: 'distance_km', label: 'Km', render: r => fmtNum(r.distance_km, 0), className: 'text-right' },
              { key: 'fuel_cost', label: 'Fuel', render: r => fmtMoney(r.fuel_cost), className: 'text-right' },
              { key: 'maintenance_cost', label: 'Maint.', render: r => fmtMoney(r.maintenance_cost), className: 'text-right' },
            ]}
            rows={byVehicle}
            pageSize={15}
          />
        </div>
      </div>
    </div>
  )
}

function Geo({ data }) {
  const zones = data?.zones || []
  const hotspots = data?.hotspots || []
  const riders = data?.rider_locations || []
  const zoneChart = zones.map(z => ({ name: z.zone_name || z.zone, total: z.total, completed: z.completed, failed: z.failed }))
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard title="Deliveries by zone">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={zoneChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="completed" name="Completed" fill="#10b981" radius={[3, 3, 0, 0]} />
              <Bar dataKey="failed" name="Failed" fill="#f43f5e" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <div>
          <DataTable
            columns={[
              { key: 'zone_name', label: 'Zone', render: r => r.zone_name || r.zone },
              { key: 'total', label: 'Total', className: 'text-right' },
              { key: 'completed', label: 'Done', className: 'text-right' },
              { key: 'failed', label: 'Failed', className: 'text-right' },
              { key: 'avg_duration_min', label: 'Avg time', render: r => fmtDuration(r.avg_duration_min), className: 'text-right' },
            ]}
            rows={zones}
            pageSize={15}
          />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div>
          <div className="mb-2 text-[13px] font-semibold text-slate-800">Delivery hotspots (completed)</div>
          <DataTable
            columns={[
              { key: 'lat', label: 'Latitude', render: r => fmtNum(r.lat, 3), className: 'text-right' },
              { key: 'lng', label: 'Longitude', render: r => fmtNum(r.lng, 3), className: 'text-right' },
              { key: 'cnt', label: 'Deliveries', className: 'text-right' },
            ]}
            rows={hotspots}
            pageSize={10}
          />
        </div>
        <div>
          <div className="mb-2 text-[13px] font-semibold text-slate-800">Rider locations ({riders.length})</div>
          <DataTable
            columns={[
              { key: 'rider_name', label: 'Rider', render: r => r.rider_name || r.rider },
              { key: 'availability_status', label: 'Status', render: r => <Badge className="border-slate-200 bg-slate-50 text-slate-600">{r.availability_status}</Badge> },
              { key: 'lat', label: 'Lat', render: r => fmtNum(r.lat, 4), className: 'text-right' },
              { key: 'lng', label: 'Lng', render: r => fmtNum(r.lng, 4), className: 'text-right' },
            ]}
            rows={riders}
            pageSize={10}
          />
        </div>
      </div>
    </div>
  )
}

function ChartCard({ title, children, className = '' }) {
  return (
    <div className={`rounded-lg border border-slate-200 bg-white p-4 ${className}`}>
      <div className="mb-2 text-[13px] font-semibold text-slate-800">{title}</div>
      {children}
    </div>
  )
}
