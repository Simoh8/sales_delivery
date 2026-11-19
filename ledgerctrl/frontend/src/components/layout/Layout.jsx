import { useState, useEffect } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import { useFilters } from '../../context/FiltersContext'

export default function Layout({ children }) {
  const [collapsed, setCollapsed] = useState(false)
  const [lastSync, setLastSync] = useState(null)
  const { refreshTick } = useFilters()

  useEffect(() => {
    setLastSync(new Date().toLocaleTimeString())
  }, [refreshTick])

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header lastSync={lastSync} />
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  )
}
