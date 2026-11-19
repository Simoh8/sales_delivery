import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, BarChart3, Package, KanbanSquare, Layers, Route, TriangleAlert,
  Bike, Clock, TrendingUp, Wallet, Truck, Link2, ClipboardCheck, Fuel, Wrench,
  MapPin, Map, Hexagon, Receipt, Coins, PiggyBank, FileText, UserCheck, Settings,
  PanelLeftClose, PanelLeftOpen, Boxes,
} from 'lucide-react'
import { useState } from 'react'

const NAV = [
  {
    label: 'OVERVIEW',
    items: [
      { to: '/', label: 'Command Center', icon: LayoutDashboard, end: true },
      { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    ],
  },
  {
    label: 'DELIVERY OPERATIONS',
    items: [
      { to: '/deliveries', label: 'Delivery Jobs', icon: Package },
      { to: '/dispatch', label: 'Dispatch Board', icon: KanbanSquare },
      { to: '/batches', label: 'Delivery Batches', icon: Layers },
      { to: '/trips', label: 'Delivery Trips', icon: Route },
      { to: '/attempts', label: 'Delivery Attempts', icon: ClipboardCheck },
      { to: '/exceptions', label: 'Delivery Exceptions', icon: TriangleAlert },
    ],
  },
  {
    label: 'PEOPLE',
    items: [
      { to: '/riders', label: 'Riders', icon: Bike },
      { to: '/shifts', label: 'Rider Shifts', icon: Clock },
      { to: '/rider-performance', label: 'Rider Performance', icon: TrendingUp },
      { to: '/earnings', label: 'Rider Earnings', icon: Wallet },
    ],
  },
  {
    label: 'FLEET',
    items: [
      { to: '/vehicles', label: 'Vehicles', icon: Truck },
      { to: '/fleet-assignments', label: 'Fleet Assignments', icon: Link2 },
      { to: '/inspections', label: 'Vehicle Inspections', icon: ClipboardCheck },
      { to: '/fuel', label: 'Fuel Management', icon: Fuel },
      { to: '/maintenance', label: 'Maintenance', icon: Wrench },
    ],
  },
  {
    label: 'LOCATIONS',
    items: [
      { to: '/map', label: 'Live Map', icon: Map },
      { to: '/zones', label: 'Delivery Zones', icon: Hexagon },
      { to: '/hubs', label: 'Delivery Hubs', icon: MapPin },
    ],
  },
  {
    label: 'FINANCIALS',
    items: [
      { to: '/expenses', label: 'Delivery Expenses', icon: Receipt },
      { to: '/costs', label: 'Delivery Costs', icon: Coins },
      { to: '/profitability', label: 'Delivery Profitability', icon: PiggyBank },
    ],
  },
  {
    label: 'REPORTS',
    items: [
      { to: '/reports', label: 'Delivery Reports', icon: FileText },
      { to: '/rider-reports', label: 'Rider Reports', icon: UserCheck },
      { to: '/fleet-reports', label: 'Fleet Reports', icon: Boxes },
    ],
  },
  {
    label: 'SETTINGS',
    items: [
      { to: '/settings', label: 'Delivery Settings', icon: Settings },
      { to: '/slas', label: 'Delivery SLAs', icon: Clock },
      { to: '/configuration', label: 'Delivery Configuration', icon: Settings },
    ],
  },
]

export default function Sidebar({ collapsed, onToggle }) {
  const [hovered, setHovered] = useState(null)
  return (
    <aside
      className={`flex h-full flex-col border-r border-slate-200 bg-white transition-[width] duration-200 ${collapsed ? 'w-[60px]' : 'w-[228px]'}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white">
          <Truck size={16} />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="truncate text-[13px] font-bold tracking-tight text-slate-900">LedgerCtrl</div>
            <div className="truncate text-[10px] font-medium uppercase tracking-wider text-slate-400">Fleet Command</div>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV.map(group => (
          <div key={group.label} className="mb-4">
            {!collapsed && (
              <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400">
                {group.label}
              </div>
            )}
            {collapsed && <div className="mx-2 mb-1 border-t border-slate-100" />}
            <div className="space-y-0.5">
              {group.items.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  title={collapsed ? item.label : undefined}
                  className={({ isActive }) =>
                    `group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] font-medium transition-colors ${
                      isActive
                        ? 'bg-sky-50 text-sky-700'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    } ${collapsed ? 'justify-center' : ''}`
                  }
                >
                  <item.icon size={16} className="shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <button
        onClick={onToggle}
        className="flex h-10 items-center justify-center border-t border-slate-200 text-slate-400 hover:bg-slate-50 hover:text-slate-600"
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
      </button>
    </aside>
  )
}
