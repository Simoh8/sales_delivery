import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { services } from '../lib/services'
import { getStoredUser, setSession, clearSession, getRefreshToken } from '../lib/api'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessionChecked, setSessionChecked] = useState(false)
  const ssoTried = useRef(false)

  // SSO: if the browser already has an authenticated Frappe session (e.g. the
  // user is logged into the desk), exchange it for JWT tokens and skip the
  // password prompt. Runs once per page load; explicit logout won't re-trigger.
  useEffect(() => {
    if (ssoTried.current) return
    ssoTried.current = true
    if (getStoredUser()) {
      setSessionChecked(true)
      return
    }
    ;(async () => {
      try {
        const res = await services.sessionLogin()
        const data = res?.data || res
        if (data?.access_token) {
          setSession(data, {
            email: data.email,
            full_name: data.full_name,
            roles: data.roles || [],
          })
          setUser({ email: data.email, full_name: data.full_name, roles: data.roles || [] })
        }
      } catch { /* no desk session -> show login form */ }
      finally { setSessionChecked(true) }
    })()
  }, [])

  const login = useCallback(async (usr, passwd) => {
    setLoading(true); setError(null)
    try {
      const res = await services.login(usr, passwd)
      const data = res?.data || res
      if (!data?.access_token) throw new Error(res?.message || 'Login failed')
      setSession(data, {
        email: data.email || usr,
        full_name: data.full_name || usr,
        roles: data.roles || [],
      })
      setUser({ email: data.email || usr, full_name: data.full_name || usr, roles: data.roles || [] })
      return true
    } catch (e) {
      setError(e.message)
      return false
    } finally { setLoading(false) }
  }, [])

  const logout = useCallback(async () => {
    try { await services.logout(getRefreshToken()) } catch { /* ignore */ }
    clearSession()
    setUser(null)
  }, [])

  const hasRole = useCallback((...roles) => {
    if (!user) return false
    if (user.roles?.includes('System Manager')) return true
    return roles.some(r => user.roles?.includes(r))
  }, [user])

  return (
    <AuthCtx.Provider value={{ user, loading, error, login, logout, hasRole, isAuthed: !!user?.email, sessionChecked }}>
      {sessionChecked ? children : null}
    </AuthCtx.Provider>
  )
}

export function useAuth() { return useContext(AuthCtx) }
