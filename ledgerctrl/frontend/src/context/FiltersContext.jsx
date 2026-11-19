import { createContext, useContext, useState, useCallback, useMemo } from 'react'
import { todayStr, daysAgo } from '../lib/format'

const FiltersCtx = createContext(null)

export function FiltersProvider({ children }) {
  const [preset, setPreset] = useState('today')
  const [from, setFrom] = useState(todayStr())
  const [to, setTo] = useState(todayStr())
  const [company, setCompany] = useState('')
  const [branch, setBranch] = useState('')
  const [refreshTick, setRefreshTick] = useState(0)

  const applyPreset = useCallback((p) => {
    setPreset(p)
    const t = todayStr()
    if (p === 'today') { setFrom(t); setTo(t) }
    else if (p === '7d') { setFrom(daysAgo(6)); setTo(t) }
    else if (p === '30d') { setFrom(daysAgo(29)); setTo(t) }
    else if (p === '90d') { setFrom(daysAgo(89)); setTo(t) }
    // 'custom' leaves values untouched
  }, [])

  const setCustom = useCallback((f, t) => {
    setPreset('custom'); setFrom(f); setTo(t)
  }, [])

  const refresh = useCallback(() => setRefreshTick(x => x + 1), [])

  const value = useMemo(() => ({
    preset, from, to, company, branch, refreshTick,
    setPreset: applyPreset, setCustom, setCompany, setBranch, refresh,
  }), [preset, from, to, company, branch, refreshTick, applyPreset, setCustom, refresh])

  return <FiltersCtx.Provider value={value}>{children}</FiltersCtx.Provider>
}

export function useFilters() { return useContext(FiltersCtx) }
