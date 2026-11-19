import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/layout/Layout'
import CommandCenter from './pages/CommandCenter'
import Analytics from './pages/Analytics'
import Dispatch from './pages/Dispatch'
import LiveMapPage from './pages/LiveMapPage'
import Riders from './pages/Riders'
import Fleet from './pages/Fleet'
import RiderPerformance from './pages/RiderPerformance'
import ReportsPage from './pages/Reports'
import GenericList from './pages/GenericList'
import Login from './pages/Login'

function RequireAuth({ children }) {
  const { isAuthed } = useAuth()
  if (!isAuthed) return <Navigate to="/login" replace />
  return children
}

const L = ({ children }) => <RequireAuth><Layout>{children}</Layout></RequireAuth>

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<L><CommandCenter /></L>} />
      <Route path="/analytics" element={<L><Analytics /></L>} />
      <Route path="/deliveries" element={<L><GenericList configKey="deliveries" /></L>} />
      <Route path="/dispatch" element={<L><Dispatch /></L>} />
      <Route path="/batches" element={<L><GenericList configKey="batches" /></L>} />
      <Route path="/trips" element={<L><GenericList configKey="trips" /></L>} />
      <Route path="/attempts" element={<L><GenericList configKey="attempts" /></L>} />
      <Route path="/exceptions" element={<L><GenericList configKey="exceptions" /></L>} />
      <Route path="/riders" element={<L><Riders /></L>} />
      <Route path="/shifts" element={<L><GenericList configKey="shifts" /></L>} />
      <Route path="/rider-performance" element={<L><RiderPerformance /></L>} />
      <Route path="/earnings" element={<L><GenericList configKey="earnings" /></L>} />
      <Route path="/vehicles" element={<L><Fleet /></L>} />
      <Route path="/fleet-assignments" element={<L><GenericList configKey="assignments" /></L>} />
      <Route path="/inspections" element={<L><GenericList configKey="inspections" /></L>} />
      <Route path="/fuel" element={<L><GenericList configKey="fuel" /></L>} />
      <Route path="/maintenance" element={<L><GenericList configKey="maintenance" /></L>} />
      <Route path="/map" element={<L><LiveMapPage /></L>} />
      <Route path="/zones" element={<L><GenericList configKey="zones" /></L>} />
      <Route path="/hubs" element={<L><GenericList configKey="hubs" /></L>} />
      <Route path="/expenses" element={<L><GenericList configKey="expenses" /></L>} />
      <Route path="/costs" element={<L><GenericList configKey="costs" /></L>} />
      <Route path="/profitability" element={<L><GenericList configKey="profitability" /></L>} />
      <Route path="/reports" element={<L><ReportsPage kind="delivery" /></L>} />
      <Route path="/rider-reports" element={<L><ReportsPage kind="rider" /></L>} />
      <Route path="/fleet-reports" element={<L><ReportsPage kind="fleet" /></L>} />
      <Route path="/settings" element={<L><GenericList configKey="settings" /></L>} />
      <Route path="/slas" element={<L><GenericList configKey="slas" /></L>} />
      <Route path="/configuration" element={<L><GenericList configKey="configuration" /></L>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
