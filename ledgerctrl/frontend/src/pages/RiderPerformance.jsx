import { useEffect, useState, useCallback } from 'react'
import { services } from '../lib/services'
import { useFilters } from '../context/FiltersContext'
import { DataTable, Spinner, ErrorState, KpiCard } from '../components/ui'
import { fmtNum, pct } from '../lib/format'

export default function RiderPerformance() {
  const { from, to, refreshTick } = useFilters()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await services.riderAnalytics(from, to)); setError(null) }
    catch (e) { setError(e) }
    finally { setLoading(false) }
  }, [from, to])

  useEffect(() => { load() }, [load, refreshTick])

  const rows = data?.leaderboard || []
  const avg = (k) => rows.length ? rows.reduce((a, r) => a + (r[k] || 0), 0) / rows.length : 0

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5">
        <h2 className="text-sm font-semibold text-slate-900">Rider Performance</h2>
        <span className="text-xs text-slate-400">{from} → {to} · score = 60% completion + 40% first-attempt</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {error ? <ErrorState error={error} onRetry={load} /> : loading ? <div className="flex justify-center py-16"><Spinner size={22} /></div> : (
          <>
            <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <KpiCard label="Riders ranked" value={rows.length} />
              <KpiCard label="Avg completion" value={pct(avg('completion_rate'))} />
              <KpiCard label="Avg first-attempt" value={pct(avg('first_attempt_success_rate'))} />
              <KpiCard label="Avg score" value={fmtNum(avg('performance_score'), 1)} />
            </div>
            <DataTable
              columns={[
                { key: 'rank', label: '#', render: (r, i) => <span className="font-bold text-slate-400">{i + 1}</span>, className: 'w-10' },
                { key: 'rider_name', label: 'Rider', render: r => <span className="font-medium">{r.rider_name || r.rider}</span> },
                { key: 'total_assigned', label: 'Assigned', className: 'text-right' },
                { key: 'completed', label: 'Completed', className: 'text-right' },
                { key: 'failed', label: 'Failed', className: 'text-right' },
                { key: 'completion_rate', label: 'Rate', render: r => pct(r.completion_rate), className: 'text-right' },
                { key: 'first_attempt_success_rate', label: '1st try', render: r => pct(r.first_attempt_success_rate), className: 'text-right' },
                { key: 'avg_delivery_duration_min', label: 'Avg time', render: r => r.avg_delivery_duration_min ? `${fmtNum(r.avg_delivery_duration_min, 0)}m` : '—', className: 'text-right' },
                { key: 'total_distance_km', label: 'Km', render: r => fmtNum(r.total_distance_km, 0), className: 'text-right' },
                { key: 'performance_score', label: 'Score', render: r => <span className="font-bold text-sky-600">{fmtNum(r.performance_score, 1)}</span>, className: 'text-right' },
              ]}
              rows={rows}
              pageSize={25}
            />
          </>
        )}
      </div>
    </div>
  )
}
