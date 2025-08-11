import React, { createContext, useContext, useEffect, useState } from 'react'
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

  useEffect(()=>{
    const token = localStorage.getItem('accessToken')
    if (!token){ setLoading(false); return }
    try{
      const claims = jwtDecode(token)
      setUser(prev => ({ ...(prev||{}), id: claims.user_id }))
    }catch{}
    api.get('/auth/api/user_details/')
      .then(async (res) => {
        const base = res.data || {}
        setUser(prev => {
          const role = pickRoleFromServerOrPrev(base?.current_role, prev)
          const nextBase = { ...prev, ...base, is_chef: Boolean(base?.is_chef), current_role: role }
          return nextBase
        })
        try{
          const addr = await api.get('/auth/api/address_details/')
          const a = addr.data || {}
          const postal = a.input_postalcode || a.postal_code || a.postalcode || ''
          setUser(prev => ({ ...(prev||{}), address: { ...a, postalcode: postal }, postal_code: postal }))
        }catch{}
      })
      .catch((e)=>{ console.warn('[Auth] user_details failed', e?.response?.status) })
      .finally(()=>setLoading(false))
  }, [])

  const login = async (username, password) => {
    const resp = await api.post('/auth/api/login/', { username, password })
    if (resp.data?.access || resp.data?.refresh){ setTokens({ access: resp.data?.access, refresh: resp.data?.refresh }) }
    const u = await api.get('/auth/api/user_details/')
    setUser(prev => ({ ...(prev||{}), ...(u.data||{}), is_chef: Boolean(u.data?.is_chef), current_role: pickRoleFromServerOrPrev(u.data?.current_role, prev) }))
    try{
      const addr = await api.get('/auth/api/address_details/')
      const a = addr.data || {}
      const postal = a.input_postalcode || a.postal_code || a.postalcode || ''
      setUser(prev => ({ ...(prev||{}), address: { ...a, postalcode: postal }, postal_code: postal }))
    }catch{}
    return u.data
  }

  const logout = async () => {
    await blacklistRefreshToken()
    clearTokens()
    setUser(null)
  }

  const register = async (payload) => {
    const resp = await api.post('/auth/api/register/', payload)
    if (resp.data.access && resp.data.refresh){
      setTokens({ access: resp.data.access, refresh: resp.data.refresh })
      const u = await api.get('/auth/api/user_details/')
      setUser(prev => ({ ...(prev||{}), ...(u.data||{}), is_chef: Boolean(u.data?.is_chef), current_role: pickRoleFromServerOrPrev(u.data?.current_role, prev) }))
      try{
        const addr = await api.get('/auth/api/address_details/')
        const a = addr.data || {}
        const postal = a.input_postalcode || a.postal_code || a.postalcode || ''
        setUser(prev => ({ ...(prev||{}), address: { ...a, postalcode: postal }, postal_code: postal }))
      }catch{}
      return u.data
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
    console.log('[Auth] switchRole → /auth/api/switch_role/', { role, hasAccess: Boolean(token), headersPreview: { Authorization: `${headers.Authorization.slice(0, 18)}…` } })
    const resp = await api.post('/auth/api/switch_role/', { role }, { headers })
    console.log('[Auth] switchRole ←', { status: resp?.status })
    setUser(prev => ({ ...(prev||{}), current_role: role }))
    setTimeout(()=>{ refreshUser() }, 500)
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
