// Shared status → color maps and badge helpers.

export const JOB_STATUS_COLORS = {
  Pending: 'bg-slate-100 text-slate-700 border-slate-200',
  Dispatched: 'bg-sky-50 text-sky-700 border-sky-200',
  Accepted: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  'En Route': 'bg-blue-50 text-blue-700 border-blue-200',
  Arrived: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  'In Progress': 'bg-teal-50 text-teal-700 border-teal-200',
  Completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Failed: 'bg-rose-50 text-rose-700 border-rose-200',
  Cancelled: 'bg-slate-100 text-slate-500 border-slate-200',
}

export const RIDER_STATUS_COLORS = {
  Available: 'bg-emerald-500',
  'On Delivery': 'bg-blue-500',
  Busy: 'bg-amber-500',
  'On Break': 'bg-violet-500',
  Offline: 'bg-slate-400',
  Delayed: 'bg-rose-500',
  Stale: 'bg-orange-500',
  Unavailable: 'bg-slate-500',
}

export const AVAILABILITY_COLORS = {
  Available: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Busy: 'bg-amber-50 text-amber-700 border-amber-200',
  'On Break': 'bg-violet-50 text-violet-700 border-violet-200',
  Offline: 'bg-slate-100 text-slate-600 border-slate-200',
  Unavailable: 'bg-slate-100 text-slate-500 border-slate-200',
}

export const PRIORITY_COLORS = {
  Low: 'text-slate-500',
  Normal: 'text-slate-700',
  High: 'text-amber-600',
  Urgent: 'text-rose-600',
}

export const SLA_COLORS = {
  'On Track': 'text-emerald-600',
  'At Risk': 'text-amber-600',
  Breached: 'text-rose-600',
  Met: 'text-emerald-600',
  'No SLA': 'text-slate-400',
}

export function jobStatusColor(s) { return JOB_STATUS_COLORS[s] || 'bg-slate-100 text-slate-600 border-slate-200' }
export function riderStatusColor(s) { return RIDER_STATUS_COLORS[s] || 'bg-slate-400' }
export function availabilityColor(s) { return AVAILABILITY_COLORS[s] || AVAILABILITY_COLORS.Offline }
export function priorityColor(s) { return PRIORITY_COLORS[s] || 'text-slate-700' }
export function slaColor(s) { return SLA_COLORS[s] || 'text-slate-500' }
