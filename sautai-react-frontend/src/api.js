import axios from 'axios'
import { jwtDecode } from 'jwt-decode'

// Base URL
const isDev = import.meta.env.DEV
// Prefer relative paths in both dev and prod unless explicitly overridden by VITE_API_BASE
// This ensures the same origin (Nginx) proxies API routes to Django, avoiding CORS/method issues
const API_BASE = (import.meta.env.VITE_API_BASE || '')
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

async function tryRefresh(payload, withCreds){
  return axios.post(`${API_BASE}${REFRESH_URL}`, payload, { withCredentials: withCreds })
}

export async function refreshAccessToken(){
  if (!USE_REFRESH_COOKIE && !refreshToken) throw new Error('No refresh token')
  if (isRefreshing){
    return new Promise((resolve, reject)=> queue.push({resolve, reject}))
  }
  isRefreshing = true
  try{
    // Primary attempt
    let resp
    try{
      const payload = USE_REFRESH_COOKIE ? {} : { refresh: refreshToken }
      resp = await tryRefresh(payload, USE_REFRESH_COOKIE)
    }catch(primaryErr){
      // Fallback if cookie-mode failed and we still have a stored refresh
      const stored = localStorage.getItem('refreshToken')
      if (USE_REFRESH_COOKIE && stored){
        try{
          resp = await tryRefresh({ refresh: stored }, false)
        }catch(secondaryErr){
          // Surface minimal debug to help diagnose
          console.warn('[api] refresh failed (cookie and header modes)', secondaryErr?.response?.status)
          throw secondaryErr
        }
      }else{
        console.warn('[api] refresh failed', primaryErr?.response?.status)
        throw primaryErr
      }
    }

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
  // Securely attach user_id to every request unless explicitly skipped or token endpoints
  try{
    const skip = (config?.skipUserId === true)
      || (config?.headers?.['X-Skip-UserId'] === true)
      || (config?.headers?.['X-Skip-UserId'] === 'true')
    const isTokenCall = isRefreshCall || (config.url || '').includes(BLACKLIST_URL)
    if (!skip && !isTokenCall && accessToken){
      let userId
      try{ const claims = jwtDecode(accessToken); userId = claims?.user_id }catch{}
      if (userId){
        // GET → params; others → body
        const method = (config.method || 'get').toLowerCase()
        if (method === 'get' || method === 'delete'){
          config.params = config.params || {}
          if (config.params.user_id == null) config.params.user_id = userId
        } else {
          if (config.data instanceof FormData){
            if (!config.data.has('user_id')) config.data.append('user_id', userId)
          } else if (config.data instanceof URLSearchParams){
            if (!config.data.has('user_id')) config.data.append('user_id', userId)
          } else if (typeof config.data === 'object' && config.data !== null){
            if (config.data.user_id == null) config.data.user_id = userId
          } else if (config.data == null) {
            config.data = { user_id: userId }
          }
        }
      }
    }
  }catch{
    // non-fatal; continue
  }
  return config
})

api.interceptors.response.use(
  (res)=>res,
  async (error) => {
    try{
      const status = error?.response?.status
      const payload = error?.response?.data
      const msg = buildErrorMessage(payload, 'An unexpected error occurred. Please try again.', status)
      window.dispatchEvent(new CustomEvent('global-toast', { detail: { text: msg, tone:'error' } }))
    }catch{}
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

function stripHtml(input){
  try{ return String(input||'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim() }catch{ return String(input||'') }
}

function firstString(val){
  if (!val) return ''
  if (typeof val === 'string') return val
  if (Array.isArray(val)) return firstString(val[0])
  if (typeof val === 'object'){
    // DRF error dicts often { field: ["msg"] }
    const k = Object.keys(val)[0]
    return firstString(val[k]) || JSON.stringify(val)
  }
  return String(val)
}

export function buildErrorMessage(data, fallback='An unexpected error occurred. Please try again.', status){
  try{
    // Only surface explicit string values from 'message' or 'error'.
    const safeFallback = typeof fallback === 'string' && fallback.trim() ? fallback : 'An unexpected error occurred. Please try again.'
    let core = ''
    if (!data){
      core = ''
    } else if (typeof data === 'string'){
      core = stripHtml(data)
    } else if (typeof data === 'object'){
      const fromMessage = typeof data.message === 'string' ? data.message : ''
      const fromError = typeof data.error === 'string' ? data.error : ''
      core = stripHtml(fromMessage || fromError)
    }
    // Do not include status codes or any other details; keep message minimal.
    return (core && core.trim()) ? core.trim() : safeFallback
  }catch{ return 'An unexpected error occurred. Please try again.' }
}

export async function blacklistRefreshToken(){
  try{
    if (USE_REFRESH_COOKIE){
      await axios.post(`${API_BASE}${BLACKLIST_URL}`, {}, { withCredentials: true })
    }else{
      const refresh = localStorage.getItem('refreshToken')
      if (refresh){ await axios.post(`${API_BASE}${BLACKLIST_URL}`, { refresh }) }
    }
  }catch{
    // ignore
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

// Stripe Connect helpers
export const stripe = {
  async getStatus(){
    return api.get('/meals/api/stripe-account-status/')
  },
  async createOrContinue(){
    return api.post('/meals/api/stripe-account-link/', {})
  },
  async regenerate(){
    return api.post('/meals/api/regenerate-stripe-link/', {})
  },
  async refreshSession(accountId){
    return api.get(`/meals/stripe-refresh/${encodeURIComponent(accountId)}/`)
  },
  async returnStatus(accountId){
    return api.get(`/meals/stripe-return/${encodeURIComponent(accountId)}/`)
  },
  async bankGuidance(){
    return api.get('/meals/api/bank-account-guidance/')
  },
  async fixRestricted(){
    return api.post('/meals/api/fix-restricted-account/', {})
  }
}
