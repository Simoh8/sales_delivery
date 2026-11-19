import { FileText, ExternalLink } from 'lucide-react'
import { EmptyState } from '../components/ui'

// Catalog of the Query Reports shipped with LedgerCtrl. Reports execute in
// ERPNext Desk (they require a desk session); this page surfaces them for
// quick access and documents what each covers.
const REPORTS = {
  delivery: [
    ['Delivery Job Register', 'Register of all delivery jobs with status, rider and timing.'],
    ['Delivery Summary Report', 'Aggregated delivery counts and outcomes by period.'],
    ['Delivery SLA Report', 'SLA compliance — met vs breached deliveries.'],
    ['Delivery Attempt Report', 'All delivery attempts with outcomes and failure reasons.'],
    ['Delivery Failure Analysis', 'Analysis of failed deliveries by reason, rider and zone.'],
    ['Delivery Expense Report', 'Delivery expenses by type, rider and status.'],
    ['Delivery Profitability Report', 'Revenue, cost and margin per delivery.'],
    ['Delivery Zone Performance Report', 'Performance metrics grouped by delivery zone.'],
  ],
  rider: [
    ['Rider Performance Report', 'Per-rider delivery counts, success rates and durations.'],
    ['Rider Shift Report', 'Shift attendance, working hours and delivery stats.'],
    ['Rider Attendance Productivity Report', 'Productivity vs attendance per rider.'],
  ],
  fleet: [
    ['Fleet Utilization Report', 'Vehicle utilization, distance and delivery counts.'],
    ['Fuel Consumption Report', 'Fuel quantity, cost and efficiency per vehicle.'],
    ['Vehicle Maintenance Report', 'Maintenance records, costs and upcoming service.'],
    ['Vehicle Operating Cost Report', 'Total operating cost per vehicle.'],
  ],
}

export default function ReportsPage({ kind = 'delivery' }) {
  const items = REPORTS[kind] || []
  const title = { delivery: 'Delivery Reports', rider: 'Rider Reports', fleet: 'Fleet Reports' }[kind]
  return (
    <div className="h-full overflow-y-auto">
      <div className="border-b border-slate-200 bg-white px-4 py-2.5">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        <p className="text-xs text-slate-400">
          Query Reports execute inside ERPNext Desk. Open Desk to run them with filters and export.
        </p>
      </div>
      <div className="grid max-w-4xl grid-cols-1 gap-2 p-4 sm:grid-cols-2">
        {items.map(([name, desc]) => (
          <div key={name} className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4">
            <div className="rounded-md bg-slate-100 p-2 text-slate-500"><FileText size={15} /></div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-slate-800">{name}</div>
              <div className="mt-0.5 text-xs text-slate-500">{desc}</div>
              <a
                href={`/app/query-report/${encodeURIComponent(name.toLowerCase().replace(/ /g, '-'))}`}
                target="_blank" rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-sky-600 hover:underline"
              >
                Open in Desk <ExternalLink size={11} />
              </a>
            </div>
          </div>
        ))}
        {items.length === 0 && <EmptyState title="No reports" />}
      </div>
    </div>
  )
}
