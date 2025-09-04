import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { api, setTokens, clearTokens, blacklistRefreshToken } from '../api'
import { jwtDecode } from 'jwt-decode'

const AuthContext = createContext(null)

function pickRoleFromServerOrPrev(serverRole, prev){
  if (serverRole === 'chef' || serverRole === 'customer') return serverRole
  return prev?.current_role || 'customer'
}

export function AuthProvider({ children }){
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const hasFetchedOnce = useRef(false)

  async function fetchUserAndAddressOnce(){
    if (hasFetchedOnce.current) return
    hasFetchedOnce.current = true
    try{
      const [uRes, aRes] = await Promise.all([
        api.get('/auth/api/user_details/'),
        api.get('/auth/api/address_details/').catch(()=>null)
      ])
      const base = uRes?.data || {}
      setUser(prev => {
        const role = pickRoleFromServerOrPrev(base?.current_role, prev)
        const nextBase = {
          ...prev,
          ...base,
          is_chef: Boolean(base?.is_chef),
          current_role: role,
          household_member_count: Math.max(1, Number(base?.household_member_count || 1))
        }
        return nextBase
      })
      if (aRes?.data){
        const a = aRes.data || {}
        const postal = a.input_postalcode || a.postal_code || a.postalcode || ''
        setUser(prev => ({ ...(prev||{}), address: { ...a, postalcode: postal }, postal_code: postal }))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(()=>{
    const token = localStorage.getItem('accessToken')
    if (!token){ setLoading(false); return }
    try{
      const claims = jwtDecode(token)
      setUser(prev => ({ ...(prev||{}), id: claims.user_id }))
    }catch{}
    fetchUserAndAddressOnce().catch((e)=>{ console.warn('[Auth] initial load failed', e?.response?.status); setLoading(false) })
  }, [])

  const login = async (username, password) => {
    // Use URL-encoded form to avoid CORS preflight on Content-Type
    const form = new URLSearchParams()
    form.set('username', username)
    form.set('password', password)
    const resp = await api.post('/auth/api/login/', form)
    if (resp.data?.access || resp.data?.refresh){ setTokens({ access: resp.data?.access, refresh: resp.data?.refresh }) }
    hasFetchedOnce.current = false
    await fetchUserAndAddressOnce()
    return user
  }

  const logout = async () => {
    await blacklistRefreshToken()
    clearTokens()
    setUser(null)
  }

  const register = async (payload) => {
    const body = payload && payload.user ? payload : { user: payload }
    const resp = await api.post('/auth/api/register/', body, { skipUserId: true })
    if (resp.data.access && resp.data.refresh){
      setTokens({ access: resp.data.access, refresh: resp.data.refresh })
      hasFetchedOnce.current = false
      await fetchUserAndAddressOnce()
      return user
    } else {
      await login(payload.username, payload.password)
    }
  }

  const refreshUser = async () => {
    try{
      const u = await api.get('/auth/api/user_details/')
      setUser(prev => ({
        ...(prev||{}),
        ...(u.data||{}),
        is_chef: Boolean(u.data?.is_chef),
        current_role: pickRoleFromServerOrPrev(u.data?.current_role, prev)
      }))
    }catch{}
  }

  const switchRole = async (role) => {
    const token = localStorage.getItem('accessToken')
    const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    const resp = await api.post('/auth/api/switch_role/', role ? { role } : {}, { headers })
    // Option C: backend returns authoritative user and optionally new tokens
    const payload = resp?.data || {}
    if (payload.access || payload.refresh){
      try{ setTokens({ access: payload.access, refresh: payload.refresh }) }catch{}
    }
    if (payload.user){
      setUser(prev => ({ ...(prev||{}), ...(payload.user||{}), is_chef: Boolean(payload?.user?.is_chef), current_role: pickRoleFromServerOrPrev(payload?.user?.current_role, prev) }))
      return payload?.user?.current_role || role
    }
    // Fallback if response did not include user (compat mode)
    const u = await api.get('/auth/api/user_details/')
    setUser(prev => ({ ...(prev||{}), ...(u.data||{}), is_chef: Boolean(u.data?.is_chef), current_role: pickRoleFromServerOrPrev(u.data?.current_role, prev), household_member_count: Math.max(1, Number((u.data||{}).household_member_count || 1)) }))
    return u?.data?.current_role || role
  }

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, register, refreshUser, switchRole, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(){
  return useContext(AuthContext)
}
