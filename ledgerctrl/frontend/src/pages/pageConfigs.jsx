// Column + filter configs for the generic module list pages.
// All field names verified against the LedgerCtrl/ERPNext DocType schemas.

import { slaColor } from '../lib/status'
import { Badge } from '../components/ui'

const dt = (v) => v || '—'

export const PAGE_CONFIGS = {
  deliveries: {
    title: 'Delivery Jobs',
    doctype: 'Delivery Job',
    fields: 'name,customer,customer_name,status,priority,rider_profile,vehicle,scheduled_date,scheduled_delivery_end,delivery_zone,sla_status,grand_total,number_of_attempts,delay_minutes,company,branch',
    orderBy: 'scheduled_date desc, creation desc',
    filters: [
      { key: 'status', label: 'Status', options: ['Pending', 'Dispatched', 'Accepted', 'En Route', 'Arrived', 'In Progress', 'Completed', 'Failed', 'Cancelled'] },
      { key: 'priority', label: 'Priority', options: ['Low', 'Normal', 'High', 'Urgent'] },
      { key: 'delivery_zone', label: 'Zone', link: 'Delivery Zone', linkField: 'zone_name' },
    ],
    columns: [
      { key: 'name', label: 'Job', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'customer_name', label: 'Customer', render: r => r.customer_name || r.customer },
      { key: 'status', label: 'Status', render: r => <StatusBadge v={r.status} kind="job" /> },
      { key: 'priority', label: 'Priority' },
      { key: 'rider_profile', label: 'Rider', render: r => r.rider_profile || '—' },
      { key: 'vehicle', label: 'Vehicle' },
      { key: 'scheduled_date', label: 'Scheduled', render: r => fmtD(r.scheduled_date) },
      { key: 'sla_status', label: 'SLA', render: r => <span className={slaColor(r.sla_status)}>{r.sla_status || '—'}</span> },
      { key: 'number_of_attempts', label: 'Attempts', className: 'text-right' },
      { key: 'grand_total', label: 'Total', render: r => money(r.grand_total), className: 'text-right' },
    ],
    onRow: 'delivery',
  },
  batches: {
    title: 'Delivery Batches',
    doctype: 'Delivery Batch',
    fields: 'name,batch_id,batch_date,assigned_rider,assigned_employee,assigned_vehicle,batch_status,total_jobs,completed_jobs,pending_jobs,failed_jobs,delivery_zone,company,branch,dispatch_time,completion_time',
    orderBy: 'batch_date desc, creation desc',
    filters: [
      { key: 'batch_status', label: 'Status', options: ['Draft', 'Ready', 'Dispatched', 'In Progress', 'Completed', 'Cancelled'] },
      { key: 'assigned_rider', label: 'Rider', link: 'Rider Profile', linkField: 'rider_name' },
    ],
    columns: [
      { key: 'batch_id', label: 'Batch', render: r => <span className="font-mono text-xs font-medium">{r.batch_id || r.name}</span> },
      { key: 'batch_date', label: 'Date', render: r => fmtD(r.batch_date) },
      { key: 'assigned_rider', label: 'Rider' },
      { key: 'assigned_vehicle', label: 'Vehicle' },
      { key: 'batch_status', label: 'Status', render: r => <StatusBadge v={r.batch_status} /> },
      { key: 'total_jobs', label: 'Jobs', className: 'text-right' },
      { key: 'completed_jobs', label: 'Done', className: 'text-right' },
      { key: 'failed_jobs', label: 'Failed', className: 'text-right' },
      { key: 'dispatch_time', label: 'Dispatched', render: r => fmtDT(r.dispatch_time) },
    ],
  },
  trips: {
    title: 'Delivery Trips',
    doctype: 'Delivery Trip',
    fields: 'name,driver,driver_name,vehicle,employee,status,departure_time,company',
    orderBy: 'departure_time desc, creation desc',
    filters: [
      { key: 'status', label: 'Status', options: ['Draft', 'Scheduled', 'In Transit', 'Completed', 'Cancelled'] },
    ],
    columns: [
      { key: 'name', label: 'Trip', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'driver_name', label: 'Driver', render: r => r.driver_name || r.driver },
      { key: 'vehicle', label: 'Vehicle' },
      { key: 'status', label: 'Status', render: r => <StatusBadge v={r.status} /> },
      { key: 'departure_time', label: 'Departure', render: r => fmtDT(r.departure_time) },
    ],
  },
  attempts: {
    title: 'Delivery Attempts',
    doctype: 'Delivery Attempt',
    fields: 'name,delivery_job,attempt_number,attempt_status,failure_reason,attempt_date,arrival_time,completion_time,rider,vehicle,gps_latitude,gps_longitude',
    orderBy: 'attempt_date desc, creation desc',
    filters: [
      { key: 'attempt_status', label: 'Outcome', options: ['Successful', 'Failed', 'Customer Unavailable', 'Rescheduled'] },
    ],
    columns: [
      { key: 'name', label: 'Attempt', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'delivery_job', label: 'Job', render: r => <span className="font-mono text-xs">{r.delivery_job}</span> },
      { key: 'attempt_number', label: '#', className: 'text-right' },
      { key: 'attempt_status', label: 'Outcome', render: r => <StatusBadge v={r.attempt_status} kind="attempt" /> },
      { key: 'rider', label: 'Rider' },
      { key: 'vehicle', label: 'Vehicle' },
      { key: 'failure_reason', label: 'Reason', render: r => <span className="text-xs text-slate-500">{r.failure_reason || '—'}</span> },
      { key: 'completion_time', label: 'Completed', render: r => fmtDT(r.completion_time) },
    ],
  },
  exceptions: {
    title: 'Delivery Exceptions',
    doctype: 'Delivery Job',
    fields: 'name,customer_name,status,priority,rider_profile,vehicle,scheduled_date,delay_minutes,number_of_attempts,delivery_zone,sla_status',
    filters: { status: 'Failed' },
    orderBy: 'modified desc',
    columns: [
      { key: 'name', label: 'Job', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'customer_name', label: 'Customer' },
      { key: 'priority', label: 'Priority' },
      { key: 'rider_profile', label: 'Rider' },
      { key: 'number_of_attempts', label: 'Attempts', className: 'text-right' },
      { key: 'delay_minutes', label: 'Delay', render: r => r.delay_minutes ? `${r.delay_minutes}m` : '—', className: 'text-right' },
      { key: 'delivery_zone', label: 'Zone' },
    ],
    onRow: 'delivery',
  },
  shifts: {
    title: 'Rider Shifts',
    doctype: 'Rider Shift',
    fields: 'name,rider,shift_date,shift_start,shift_end,actual_clock_in,actual_clock_out,shift_status,total_working_hours,total_deliveries,completed_deliveries,failed_deliveries,total_distance_travelled',
    orderBy: 'shift_date desc, creation desc',
    filters: [
      { key: 'shift_status', label: 'Status', options: ['Scheduled', 'Active', 'Completed', 'Cancelled'] },
      { key: 'rider', label: 'Rider', link: 'Rider Profile', linkField: 'rider_name' },
    ],
    columns: [
      { key: 'name', label: 'Shift', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'rider', label: 'Rider' },
      { key: 'shift_date', label: 'Date', render: r => fmtD(r.shift_date) },
      { key: 'actual_clock_in', label: 'Clock in', render: r => fmtDT(r.actual_clock_in) },
      { key: 'actual_clock_out', label: 'Clock out', render: r => fmtDT(r.actual_clock_out) },
      { key: 'shift_status', label: 'Status', render: r => <StatusBadge v={r.shift_status} /> },
      { key: 'total_working_hours', label: 'Hours', render: r => r.total_working_hours != null ? `${fmtNum(r.total_working_hours, 1)}h` : '—', className: 'text-right' },
      { key: 'completed_deliveries', label: 'Done', className: 'text-right' },
      { key: 'total_distance_travelled', label: 'Km', render: r => fmtNum(r.total_distance_travelled, 0), className: 'text-right' },
    ],
    onRow: 'rider',
  },
  earnings: {
    title: 'Rider Earnings',
    doctype: 'Delivery Expense',
    fields: 'name,rider,delivery_job,vehicle,expense_date,expense_type,amount,expense_status,expense_claim,description',
    orderBy: 'expense_date desc, creation desc',
    filters: [
      { key: 'expense_status', label: 'Status', options: ['Draft', 'Submitted', 'Approved', 'Reimbursed', 'Cancelled'] },
      { key: 'expense_type', label: 'Type', options: ['Fuel', 'Parking', 'Toll', 'Loading', 'Maintenance', 'Other'] },
      { key: 'rider', label: 'Rider', link: 'Rider Profile', linkField: 'rider_name' },
    ],
    columns: [
      { key: 'name', label: 'Expense', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'rider', label: 'Rider' },
      { key: 'expense_type', label: 'Type' },
      { key: 'amount', label: 'Amount', render: r => money(r.amount), className: 'text-right' },
      { key: 'expense_status', label: 'Status', render: r => <StatusBadge v={r.expense_status} /> },
      { key: 'expense_date', label: 'Date', render: r => fmtD(r.expense_date) },
      { key: 'expense_claim', label: 'Claim', render: r => r.expense_claim || '—' },
    ],
  },
  assignments: {
    title: 'Fleet Assignments',
    doctype: 'Fleet Assignment',
    fields: 'name,rider,employee,vehicle,assignment_start,assignment_end,assignment_status,opening_odometer,closing_odometer,assigned_by',
    orderBy: 'assignment_start desc, creation desc',
    filters: [
      { key: 'assignment_status', label: 'Status', options: ['Active', 'Completed', 'Cancelled'] },
    ],
    columns: [
      { key: 'name', label: 'Assignment', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'rider', label: 'Rider' },
      { key: 'employee', label: 'Employee' },
      { key: 'vehicle', label: 'Vehicle' },
      { key: 'assignment_start', label: 'Start', render: r => fmtD(r.assignment_start) },
      { key: 'assignment_end', label: 'End', render: r => fmtD(r.assignment_end) },
      { key: 'assignment_status', label: 'Status', render: r => <StatusBadge v={r.assignment_status} /> },
    ],
    onRow: 'vehicle',
  },
  inspections: {
    title: 'Vehicle Inspections',
    doctype: 'Vehicle Inspection',
    fields: 'name,vehicle,rider,inspection_date,inspection_type,inspection_result,odometer_reading,fuel_level,defects_identified,inspected_by',
    orderBy: 'inspection_date desc, creation desc',
    filters: [
      { key: 'inspection_result', label: 'Result', options: ['Passed', 'Failed', 'Requires Attention'] },
      { key: 'inspection_type', label: 'Type', options: ['Pre-Trip', 'Post-Trip', 'Routine'] },
    ],
    columns: [
      { key: 'name', label: 'Inspection', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'vehicle', label: 'Vehicle' },
      { key: 'rider', label: 'Rider' },
      { key: 'inspection_type', label: 'Type' },
      { key: 'inspection_result', label: 'Result', render: r => <StatusBadge v={r.inspection_result} kind="inspection" /> },
      { key: 'odometer_reading', label: 'Odometer', render: r => r.odometer_reading != null ? `${fmtNum(r.odometer_reading)} km` : '—', className: 'text-right' },
      { key: 'inspection_date', label: 'Date', render: r => fmtDT(r.inspection_date) },
    ],
  },
  fuel: {
    title: 'Fuel Management',
    doctype: 'Fuel Log',
    fields: 'name,vehicle,rider,fuel_date,fuel_type,quantity,unit_price,total_cost,odometer_reading,fuel_station,payment_method,consumption_kmpl,flag_reason',
    orderBy: 'fuel_date desc, creation desc',
    filters: [
      { key: 'vehicle', label: 'Vehicle', link: 'Vehicle', linkField: 'license_plate' },
      { key: 'fuel_type', label: 'Fuel', options: ['Petrol', 'Diesel', 'Electric', 'LPG', 'Other'] },
    ],
    columns: [
      { key: 'name', label: 'Log', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'vehicle', label: 'Vehicle' },
      { key: 'rider', label: 'Rider' },
      { key: 'fuel_date', label: 'Date', render: r => fmtD(r.fuel_date) },
      { key: 'fuel_type', label: 'Type' },
      { key: 'quantity', label: 'Qty', render: r => `${fmtNum(r.quantity, 1)} L`, className: 'text-right' },
      { key: 'total_cost', label: 'Cost', render: r => money(r.total_cost), className: 'text-right' },
      { key: 'consumption_kmpl', label: 'km/L', render: r => fmtNum(r.consumption_kmpl, 1), className: 'text-right' },
    ],
  },
  maintenance: {
    title: 'Maintenance',
    doctype: 'Vehicle Maintenance Record',
    fields: 'name,vehicle,maintenance_type,maintenance_date,description,total_cost,next_service_date,next_service_odometer,status,service_provider',
    orderBy: 'maintenance_date desc, creation desc',
    filters: [
      { key: 'status', label: 'Status', options: ['Open', 'In Progress', 'Completed', 'Cancelled'] },
      { key: 'maintenance_type', label: 'Type', options: ['Service', 'Repair', 'Inspection', 'Tyre', 'Body Work', 'Other'] },
    ],
    columns: [
      { key: 'name', label: 'Record', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'vehicle', label: 'Vehicle' },
      { key: 'maintenance_type', label: 'Type' },
      { key: 'description', label: 'Description', render: r => <span className="text-xs text-slate-500">{r.description || '—'}</span> },
      { key: 'total_cost', label: 'Cost', render: r => money(r.total_cost), className: 'text-right' },
      { key: 'maintenance_date', label: 'Date', render: r => fmtD(r.maintenance_date) },
      { key: 'next_service_date', label: 'Next service', render: r => fmtD(r.next_service_date) },
      { key: 'status', label: 'Status', render: r => <StatusBadge v={r.status} /> },
    ],
  },
  zones: {
    title: 'Delivery Zones',
    doctype: 'Delivery Zone',
    fields: 'name,zone_name,zone_code,company,branch,status,latitude,longitude,radius,default_delivery_charge,default_delivery_sla',
    orderBy: 'zone_name asc',
    filters: [
      { key: 'status', label: 'Status', options: ['Active', 'Inactive'] },
    ],
    columns: [
      { key: 'zone_name', label: 'Zone', render: r => <span className="font-medium">{r.zone_name || r.name}</span> },
      { key: 'zone_code', label: 'Code' },
      { key: 'company', label: 'Company' },
      { key: 'branch', label: 'Branch' },
      { key: 'status', label: 'Status', render: r => <StatusBadge v={r.status} /> },
      { key: 'latitude', label: 'Lat', render: r => fmtNum(r.latitude, 4), className: 'text-right' },
      { key: 'longitude', label: 'Lng', render: r => fmtNum(r.longitude, 4), className: 'text-right' },
      { key: 'radius', label: 'Radius', render: r => r.radius ? `${fmtNum(r.radius, 1)} km` : '—', className: 'text-right' },
      { key: 'default_delivery_charge', label: 'Charge', render: r => money(r.default_delivery_charge), className: 'text-right' },
    ],
  },
  hubs: {
    title: 'Delivery Hubs',
    doctype: 'Delivery Zone',
    fields: 'name,zone_name,zone_code,company,branch,status,latitude,longitude,radius,description',
    orderBy: 'zone_name asc',
    filters: [
      { key: 'status', label: 'Status', options: ['Active', 'Inactive'] },
    ],
    columns: [
      { key: 'zone_name', label: 'Hub / Zone', render: r => <span className="font-medium">{r.zone_name || r.name}</span> },
      { key: 'zone_code', label: 'Code' },
      { key: 'company', label: 'Company' },
      { key: 'status', label: 'Status', render: r => <StatusBadge v={r.status} /> },
      { key: 'latitude', label: 'Lat', render: r => fmtNum(r.latitude, 4), className: 'text-right' },
      { key: 'longitude', label: 'Lng', render: r => fmtNum(r.longitude, 4), className: 'text-right' },
      { key: 'description', label: 'Notes', render: r => <span className="text-xs text-slate-500">{r.description || '—'}</span> },
    ],
  },
  expenses: {
    title: 'Delivery Expenses',
    doctype: 'Delivery Expense',
    fields: 'name,rider,delivery_job,delivery_batch,vehicle,expense_date,expense_type,amount,description,expense_status,expense_claim',
    orderBy: 'expense_date desc, creation desc',
    filters: [
      { key: 'expense_status', label: 'Status', options: ['Draft', 'Submitted', 'Approved', 'Reimbursed', 'Cancelled'] },
      { key: 'expense_type', label: 'Type', options: ['Fuel', 'Parking', 'Toll', 'Loading', 'Maintenance', 'Other'] },
    ],
    columns: [
      { key: 'name', label: 'Expense', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'rider', label: 'Rider' },
      { key: 'delivery_job', label: 'Job', render: r => <span className="font-mono text-xs">{r.delivery_job || '—'}</span> },
      { key: 'expense_type', label: 'Type' },
      { key: 'amount', label: 'Amount', render: r => money(r.amount), className: 'text-right' },
      { key: 'expense_status', label: 'Status', render: r => <StatusBadge v={r.expense_status} /> },
      { key: 'expense_date', label: 'Date', render: r => fmtD(r.expense_date) },
    ],
  },
  costs: {
    title: 'Delivery Costs',
    doctype: 'Delivery Job',
    fields: 'name,customer_name,status,scheduled_date,rider_profile,vehicle,customer_delivery_charge,actual_delivery_cost,delivery_revenue,cod_expected,cod_collected,grand_total,payment_status',
    orderBy: 'scheduled_date desc, creation desc',
    filters: [
      { key: 'status', label: 'Status', options: ['Pending', 'Dispatched', 'Accepted', 'En Route', 'Arrived', 'In Progress', 'Completed', 'Failed', 'Cancelled'] },
    ],
    columns: [
      { key: 'name', label: 'Job', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'customer_name', label: 'Customer' },
      { key: 'status', label: 'Status', render: r => <StatusBadge v={r.status} kind="job" /> },
      { key: 'rider_profile', label: 'Rider' },
      { key: 'customer_delivery_charge', label: 'Charge', render: r => money(r.customer_delivery_charge), className: 'text-right' },
      { key: 'actual_delivery_cost', label: 'Cost', render: r => money(r.actual_delivery_cost), className: 'text-right' },
      { key: 'delivery_revenue', label: 'Revenue', render: r => money(r.delivery_revenue), className: 'text-right' },
      { key: 'payment_status', label: 'Payment' },
    ],
    onRow: 'delivery',
  },
  profitability: {
    title: 'Delivery Profitability',
    doctype: 'Delivery Job',
    fields: 'name,customer_name,status,scheduled_date,rider_profile,vehicle,customer_delivery_charge,actual_delivery_cost,delivery_revenue,grand_total,payment_status,delivery_zone',
    orderBy: 'scheduled_date desc, creation desc',
    filters: [
      { key: 'status', label: 'Status', options: ['Completed', 'Failed', 'Cancelled', 'In Progress', 'Pending'] },
    ],
    columns: [
      { key: 'name', label: 'Job', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'customer_name', label: 'Customer' },
      { key: 'status', label: 'Status', render: r => <StatusBadge v={r.status} kind="job" /> },
      { key: 'delivery_zone', label: 'Zone' },
      { key: 'rider_profile', label: 'Rider' },
      { key: 'customer_delivery_charge', label: 'Charge', render: r => money(r.customer_delivery_charge), className: 'text-right' },
      { key: 'actual_delivery_cost', label: 'Cost', render: r => money(r.actual_delivery_cost), className: 'text-right' },
      { key: 'delivery_revenue', label: 'Margin', render: r => <Margin value={r.delivery_revenue ?? (r.customer_delivery_charge || 0) - (r.actual_delivery_cost || 0)} />, className: 'text-right' },
    ],
    onRow: 'delivery',
  },
  slas: {
    title: 'Delivery SLAs',
    doctype: 'Delivery SLA',
    fields: 'name,sla_name,delivery_type,maximum_delivery_duration,expected_pickup_duration,expected_delivery_duration,grace_period,priority,active',
    orderBy: 'sla_name asc',
    columns: [
      { key: 'name', label: 'SLA', render: r => <span className="font-mono text-xs font-medium">{r.name}</span> },
      { key: 'sla_name', label: 'Name' },
      { key: 'delivery_type', label: 'Type' },
      { key: 'maximum_delivery_duration', label: 'Max duration', render: r => r.maximum_delivery_duration ? `${fmtNum(r.maximum_delivery_duration)}m` : '—', className: 'text-right' },
      { key: 'expected_pickup_duration', label: 'Pickup', render: r => r.expected_pickup_duration ? `${fmtNum(r.expected_pickup_duration)}m` : '—', className: 'text-right' },
      { key: 'expected_delivery_duration', label: 'Delivery', render: r => r.expected_delivery_duration ? `${fmtNum(r.expected_delivery_duration)}m` : '—', className: 'text-right' },
      { key: 'grace_period', label: 'Grace', render: r => r.grace_period ? `${fmtNum(r.grace_period)}m` : '—', className: 'text-right' },
      { key: 'priority', label: 'Priority' },
      { key: 'active', label: 'Active', render: r => r.active ? <Badge className="border-emerald-200 bg-emerald-50 text-emerald-700">Active</Badge> : <Badge className="border-slate-200 bg-slate-50 text-slate-500">Inactive</Badge> },
    ],
  },
  settings: {
    title: 'Delivery Settings',
    doctype: 'Delivery Settings',
    fields: 'require_otp,require_signature,require_photograph,require_recipient_confirmation,allow_multiple_active_deliveries,allow_overlapping_shifts,allow_multiple_active_vehicle_assignments,maintenance_reminder_days,document_expiry_alert_days,sla_breach_alert_hours',
    view: 'settings',
  },
  configuration: {
    title: 'Delivery Configuration',
    doctype: 'Delivery Settings',
    fields: 'require_otp,require_signature,require_photograph,require_recipient_confirmation,allow_multiple_active_deliveries,allow_overlapping_shifts,allow_multiple_active_vehicle_assignments,maintenance_reminder_days,document_expiry_alert_days,sla_breach_alert_hours',
    view: 'settings',
  },
}

function fmtD(v) { return v ? String(v).slice(0, 10) : '—' }
function fmtDT(v) {
  if (!v) return '—'
  const d = new Date(String(v).replace(' ', 'T'))
  return isNaN(d) ? String(v) : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function fmtNum(v, d = 0) { return v == null ? '—' : Number(v).toLocaleString(undefined, { maximumFractionDigits: d }) }
function money(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  return isNaN(n) ? String(v) : n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function Margin({ value }) {
  const n = Number(value)
  const cls = isNaN(n) ? 'text-slate-500' : n >= 0 ? 'text-emerald-600 font-medium' : 'text-rose-600 font-medium'
  return <span className={cls}>{money(value)}</span>
}
function StatusBadge({ v, kind }) {
  if (!v) return <span className="text-slate-400">—</span>
  const map = {
    job: {
      Pending: 'border-slate-200 bg-slate-50 text-slate-600', Dispatched: 'border-sky-200 bg-sky-50 text-sky-700',
      Accepted: 'border-indigo-200 bg-indigo-50 text-indigo-700', 'En Route': 'border-blue-200 bg-blue-50 text-blue-700',
      Arrived: 'border-cyan-200 bg-cyan-50 text-cyan-700', 'In Progress': 'border-teal-200 bg-teal-50 text-teal-700',
      Completed: 'border-emerald-200 bg-emerald-50 text-emerald-700', Failed: 'border-rose-200 bg-rose-50 text-rose-700',
      Cancelled: 'border-slate-200 bg-slate-100 text-slate-500',
    },
    attempt: {
      Successful: 'border-emerald-200 bg-emerald-50 text-emerald-700',
      Failed: 'border-rose-200 bg-rose-50 text-rose-700',
      'Customer Unavailable': 'border-amber-200 bg-amber-50 text-amber-700',
      Rescheduled: 'border-sky-200 bg-sky-50 text-sky-700',
    },
    inspection: {
      Passed: 'border-emerald-200 bg-emerald-50 text-emerald-700',
      Failed: 'border-rose-200 bg-rose-50 text-rose-700',
      'Requires Attention': 'border-amber-200 bg-amber-50 text-amber-700',
    },
  }
  const cls = (kind && map[kind]?.[v]) || 'border-slate-200 bg-slate-50 text-slate-600'
  return <span className={`inline-flex rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${cls}`}>{v}</span>
}
