import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Truck, Loader2 } from 'lucide-react'

export default function Login() {
  const { login, isAuthed, error } = useAuth()
  const [usr, setUsr] = useState('')
  const [passwd, setPasswd] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  if (isAuthed) return <Navigate to="/" replace />

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    const ok = await login(usr.trim(), passwd)
    setBusy(false)
    if (ok) navigate('/')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900 text-white">
            <Truck size={22} />
          </div>
          <h1 className="text-xl font-bold text-slate-900">LedgerCtrl Fleet Command</h1>
          <p className="mt-1 text-sm text-slate-500">Delivery operations workspace</p>
        </div>
        <form onSubmit={submit} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <label className="mb-1 block text-xs font-medium text-slate-600">Email / Username</label>
          <input
            value={usr} onChange={e => setUsr(e.target.value)} required autoFocus
            className="mb-4 h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-sky-400"
            placeholder="you@company.com"
          />
          <label className="mb-1 block text-xs font-medium text-slate-600">Password</label>
          <input
            type="password" value={passwd} onChange={e => setPasswd(e.target.value)} required
            className="mb-5 h-10 w-full rounded-md border border-slate-200 px-3 text-sm outline-none focus:border-sky-400"
            placeholder="••••••••"
          />
          {error && <div className="mb-4 rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</div>}
          <button
            type="submit" disabled={busy}
            className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-900 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
          >
            {busy && <Loader2 size={15} className="animate-spin" />}
            Sign in
          </button>
          <p className="mt-4 text-center text-[11px] text-slate-400">
            Requires a Frappe account with Delivery / Fleet manager roles.
          </p>
        </form>
      </div>
    </div>
  )
}
