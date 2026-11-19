import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Search, RefreshCw, Bell, ChevronDown, LogOut, User, Building2 } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useFilters } from '../../context/FiltersContext'
import { services } from '../../lib/services'
import { Select } from '../ui'

const TITLES = {
  '/': 'Command Center',
  '/analytics': 'Analytics',
  '/deliveries': 'Delivery Jobs',
  '/dispatch': 'Dispatch Board',
  '/batches': 'Delivery Batches',
  '/trips': 'Delivery Trips',
  '/attempts': 'Delivery Attempts',
  '/exceptions': 'Delivery Exceptions',
  '/riders': 'Riders',
  '/shifts': 'Rider Shifts',
  '/rider-performance': 'Rider Performance',
  '/earnings': 'Rider Earnings',
  '/vehicles': 'Vehicles',
  '/fleet-assignments': 'Fleet Assignments',
  '/inspections': 'Vehicle Inspections',
  '/fuel': 'Fuel Management',
  '/maintenance': 'Maintenance',
  '/map': 'Live Map',
  '/zones': 'Delivery Zones',
  '/hubs': 'Delivery Hubs',
  '/expenses': 'Delivery Expenses',
  '/costs': 'Delivery Costs',
  '/profitability': 'Delivery Profitability',
  '/reports': 'Delivery Reports',
  '/rider-reports': 'Rider Reports',
  '/fleet-reports': 'Fleet Reports',
  '/settings': 'Delivery Settings',
  '/slas': 'Delivery SLAs',
  '/configuration': 'Delivery Configuration',
}

const PRESETS = [
  { value: 'today', label: 'Today' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'custom', label: 'Custom' },
]

export default function Header({ lastSync }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const f = useFilters()
  const [q, setQ] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [companies, setCompanies] = useState([])
  const [syncing, setSyncing] = useState(false)

  const title = TITLES[pathname] || 'LedgerCtrl'

  useEffect(() => {
    services.listDoctype({ doctype: 'Company', fields: 'name,company_name,abbr', limit: 100 })
      .then(r => setCompanies(r.data || []))
      .catch(() => {})
  }, [])

  const doSearch = (e) => {
    e.preventDefault()
    if (q.trim()) navigate(`/deliveries?q=${encodeURIComponent(q.trim())}`)
  }

  const doRefresh = () => {
    setSyncing(true)
    f.refresh()
    setTimeout(() => setSyncing(false), 800)
  }

  return (
    <header className="flex h-14 items-center gap-3 border-b border-slate-200 bg-white px-4">
      <h1 className="text-[15px] font-semibold text-slate-900">{title}</h1>

      <form onSubmit={doSearch} className="relative ml-4 hidden w-64 md:block">
        <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Search deliveries, riders, jobs…"
          className="h-8 w-full rounded-md border border-slate-200 bg-slate-50 pl-8 pr-3 text-xs outline-none focus:border-sky-400 focus:bg-white"
        />
      </form>

      <div className="ml-auto flex items-center gap-2">
        <Select value={f.preset} onChange={f.setPreset} options={PRESETS} className="w-32" />
        {f.preset === 'custom' && (
          <>
            <input type="date" value={f.from} onChange={e => f.setCustom(e.target.value, f.to)} className="h-8 rounded-md border border-slate-200 px-2 text-xs" />
            <input type="date" value={f.to} onChange={e => f.setCustom(f.from, e.target.value)} className="h-8 rounded-md border border-slate-200 px-2 text-xs" />
          </>
        )}

        <div className="hidden items-center gap-1.5 lg:flex">
          <Building2 size={13} className="text-slate-400" />
          <Select
            value={f.company}
            onChange={f.setCompany}
            options={companies.map(c => ({ value: c.name, label: c.company_name || c.name }))}
            placeholder="All companies"
            className="w-36"
          />
        </div>

        <button
          onClick={doRefresh}
          title="Refresh data"
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
        >
          <RefreshCw size={15} className={syncing ? 'animate-spin' : ''} />
        </button>

        <div className="hidden items-center gap-1.5 text-[11px] text-slate-400 xl:flex" title={lastSync ? `Last sync: ${lastSync}` : ''}>
          <span className={`h-1.5 w-1.5 rounded-full ${lastSync ? 'bg-emerald-500' : 'bg-slate-300'}`} />
          {lastSync ? `Synced ${lastSync}` : 'Not synced'}
        </div>

        <button className="relative rounded-md p-1.5 text-slate-500 hover:bg-slate-100" title="Notifications">
          <Bell size={15} />
          <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-rose-500" />
        </button>

        <div className="relative">
          <button
            onClick={() => setMenuOpen(o => !o)}
            className="flex items-center gap-2 rounded-md px-1.5 py-1 hover:bg-slate-100"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 text-[11px] font-semibold text-white">
              {(user?.full_name || user?.email || '?').slice(0, 1).toUpperCase()}
            </div>
            <div className="hidden text-left md:block">
              <div className="max-w-[120px] truncate text-xs font-medium text-slate-800">{user?.full_name || user?.email}</div>
              <div className="text-[10px] text-slate-400">{(user?.roles || []).slice(0, 2).join(', ')}</div>
            </div>
            <ChevronDown size={13} className="text-slate-400" />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 z-50 mt-1 w-52 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                <div className="border-b border-slate-100 px-3 py-2">
                  <div className="text-xs font-medium text-slate-800">{user?.full_name || user?.email}</div>
                  <div className="text-[11px] text-slate-400">{user?.email}</div>
                </div>
                <button onClick={logout} className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-rose-600 hover:bg-rose-50">
                  <LogOut size={13} /> Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
