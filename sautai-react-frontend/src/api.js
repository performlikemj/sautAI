import axios from 'axios'
import { jwtDecode } from 'jwt-decode'

// Base URL
const isDev = import.meta.env.DEV
const API_BASE = (import.meta.env.VITE_API_BASE || (isDev ? '' : 'http://localhost:8000'))
const REFRESH_URL = '/auth/api/token/refresh/'
const BLACKLIST_URL = '/auth/api/token/blacklist/'
const USE_REFRESH_COOKIE = String(import.meta.env.VITE_USE_REFRESH_COOKIE || 'false') === 'true'

let accessToken = localStorage.getItem('accessToken') || null
let refreshToken = USE_REFRESH_COOKIE ? null : (localStorage.getItem('refreshToken') || null)

export function setTokens(tokens = {}){
  if (tokens.access){ accessToken = tokens.access; localStorage.setItem('accessToken', tokens.access) }
  if (!USE_REFRESH_COOKIE && tokens.refresh){ refreshToken = tokens.refresh; localStorage.setItem('refreshToken', tokens.refresh) }
}
export function clearTokens(){
  accessToken = null
  if (!USE_REFRESH_COOKIE) refreshToken = null
  localStorage.removeItem('accessToken')
  if (!USE_REFRESH_COOKIE) localStorage.removeItem('refreshToken')
}

function willExpireSoon(token, withinSeconds = 30){
  try{
    const { exp } = jwtDecode(token)
    if (!exp) return true
    return (exp*1000 - Date.now()) < (withinSeconds * 1000)
  }catch{ return true }
}

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: USE_REFRESH_COOKIE
})

let isRefreshing = false
let queue = []

export async function refreshAccessToken(){
  if (!USE_REFRESH_COOKIE && !refreshToken) throw new Error('No refresh token')
  if (isRefreshing){
    return new Promise((resolve, reject)=> queue.push({resolve, reject}))
  }
  isRefreshing = true
  try{
    const payload = USE_REFRESH_COOKIE ? {} : { refresh: refreshToken }
    const resp = await axios.post(`${API_BASE}${REFRESH_URL}`, payload, { withCredentials: USE_REFRESH_COOKIE })
    const newAccess = resp.data?.access
    if (!newAccess) throw new Error('No access token in refresh response')
    setTokens({ access: newAccess })
    queue.forEach(p => p.resolve(newAccess))
    queue = []
    return newAccess
  } catch (e){
    queue.forEach(p => p.reject(e))
    queue = []
    clearTokens()
    throw e
  } finally {
    isRefreshing = false
  }
}

api.interceptors.request.use(async (config) => {
  const isRefreshCall = (config.url || '').includes(REFRESH_URL)
  if (accessToken && !isRefreshCall){
    if (willExpireSoon(accessToken) && (USE_REFRESH_COOKIE || refreshToken)){
      try{ await refreshAccessToken() }catch{ /* allow 401 handler to retry */ }
    }
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (res)=>res,
  async (error) => {
    const original = error.config || {}
    const status = error?.response?.status
    const isRefreshCall = (original.url || '').includes(REFRESH_URL)

    if (status === 401 && !original._retry && !isRefreshCall){
      original._retry = true
      try{
        const newAccess = await refreshAccessToken()
        original.headers = original.headers || {}
        original.headers.Authorization = `Bearer ${newAccess}`
        return api(original)
      }catch(e){
        clearTokens()
        window.location.href = '/login'
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  }
)

export async function blacklistRefreshToken(){
  try{
    if (USE_REFRESH_COOKIE){
      await axios.post(`${API_BASE}${BLACKLIST_URL}`, {}, { withCredentials: true })
    }else{
      const refresh = localStorage.getItem('refreshToken')
      if (refresh){ await axios.post(`${API_BASE}${BLACKLIST_URL}`, { refresh }) }
    }
  }catch{
    // ignore; proceed with local cleanup
  }
}

export function newIdempotencyKey(){
  try{
    if (crypto && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  }catch{}
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random()*16|0, v = c === 'x' ? r : (r&0x3|0x8)
    return v.toString(16)
  })
}
