import React, { useEffect, useState, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Link, useSearchParams } from 'react-router-dom'
import { api, newIdempotencyKey, refreshAccessToken } from '../api'
import InstacartButton from '../components/InstacartButton.jsx'
import { codeFromCountryName } from '../utils/geo.js'
import Listbox from '../components/Listbox.jsx'
import { EventSourcePolyfill } from 'event-source-polyfill'
import { useAuth } from '../context/AuthContext.jsx'

function startOfWeek(d){
  const x = new Date(d); const day = x.getDay() // 0 Sun
  const diff = (day === 0 ? -6 : 1) - day // Monday as start
  x.setDate(x.getDate()+diff)
  x.setHours(0,0,0,0)
  return x
}
function fmtISO(d){ return fmtYMD(d) }
function fmtLong(d){
  try{ return new Date(d).toLocaleDateString(undefined, { year:'numeric', month:'long', day:'numeric' }) }
  catch{ return fmtISO(d) }
}
function fmtYMD(d){
  const y = d.getFullYear()
  const m = String(d.getMonth()+1).padStart(2,'0')
  const day = String(d.getDate()).padStart(2,'0')
  return `${y}-${m}-${day}`
}

export default function MealPlans(){
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialWeek = useMemo(()=>{
    const qs = searchParams.get('week_start')
    if (qs){
      try{ return startOfWeek(new Date(qs + 'T00:00:00')) }catch{}
    }
    return startOfWeek(new Date())
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const [weekStart, setWeekStart] = useState(initialWeek)
  const [longDate, setLongDate] = useState(false)
  const [plan, setPlan] = useState(null)
  const [mealPlanId, setMealPlanId] = useState(null)
  const [isApproved, setIsApproved] = useState(null)
  const [prepPreference, setPrepPreference] = useState('daily')
  const [approving, setApproving] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [chefMeals, setChefMeals] = useState([])
  const [tab, setTab] = useState('overview')
  const [addingPantry, setAddingPantry] = useState(false)
  const [headerToasts, setHeaderToasts] = useState([]) // {id, text, tone, closing}
  const [hasPendingOrders, setHasPendingOrders] = useState(false)
  const [verifyingPaymentOrderId, setVerifyingPaymentOrderId] = useState(null)
  const [quickHealth, setQuickHealth] = useState(false)
  const [qaOpen, setQaOpen] = useState(false)
  const qaRef = useRef(null)
  const esRef = useRef(null)
  const [streaming, setStreaming] = useState(false)
  const streamingRef = useRef(false)
  const [progressPct, setProgressPct] = useState(0)
  const fallbackRef = useRef(null)
  const pollRef = useRef(null)
  const completeRef = useRef(null)
  const generationTimeoutRef = useRef(null)
  const expectedSlotsRef = useRef(21) // fallback expected number of slots (7 days * 3 meals)
  const [focusSlot, setFocusSlot] = useState(null) // { day, type }
  const [slotPanel, setSlotPanel] = useState(null) // { day, type }
  const [slotAlts, setSlotAlts] = useState([])
  const [slotAltId, setSlotAltId] = useState('')
  const [slotLoading, setSlotLoading] = useState(false)
  // Instacart state
  const [instacartUrl, setInstacartUrl] = useState(null)
  const [instacartHasChefMeals, setInstacartHasChefMeals] = useState(false)
  const [instacartError, setInstacartError] = useState(null)
  const [instacartTriedForPlan, setInstacartTriedForPlan] = useState(null) // mealPlanId used when we last attempted
  // If an empty-slot panel is open and that slot becomes filled (SSE/poll), switch to edit view
  useEffect(()=>{
    if (!slotPanel) return
    try{
      const mealsArr = Array.isArray(plan?.meals) ? plan.meals : (plan?.meal_plan_meals || [])
      const exists = (mealsArr||[]).find(x => (x.day||x.day_of_week)===slotPanel.day && (x.meal_type||x.type)===slotPanel.type)
      if (exists){
        setSlotPanel(null)
        setSelectedSlot({ day: slotPanel.day, meal: exists, rect: null })
      }
    }catch{}
  }, [plan, slotPanel?.day, slotPanel?.type])
  // Auto-load alternatives when opening the empty-slot panel
  useEffect(()=>{
    if (!slotPanel) return
    let cancelled = false
    const load = async ()=>{
      setSlotLoading(true)
      try{
        const payload = { week_start_date: fmtYMD(weekStart), day: slotPanel.day, meal_type: slotPanel.type }
        const r = await api.post('/meals/api/suggest_alternatives_for_slot/', payload)
        if (cancelled) return
        const alts = Array.isArray(r?.data?.alternatives) ? r.data.alternatives : []
        setSlotAlts(alts)
        setSlotAltId(alts[0] ? `${alts[0].is_chef_meal?'c':'u'}:${alts[0].meal_id}` : '')
      }catch{
        if (!cancelled){ setSlotAlts([]); setSlotAltId('') }
      }finally{
        if (!cancelled) setSlotLoading(false)
      }
    }
    load()
    return ()=>{ cancelled = true }
  }, [slotPanel?.day, slotPanel?.type, weekStart])

  const log = useMemo(() => (
    () => {}
  ), [])

  //

  // Normalize a user-provided country value to ISO-2 when possible
  function normalizeCountryIso2(input){
    try{
      let raw = String(input||'').trim()
      if (!raw) return ''
      if (raw.length === 2) return raw.toUpperCase()
      const lower = raw.toLowerCase()
      if (lower.includes('united states')) return 'US'
      if (lower.includes('u.s.a') || lower.includes('u.s.') || lower === 'usa') return 'US'
      if (lower.includes('canada')) return 'CA'
      // Try our lookup table as a fallback
      const mapped = codeFromCountryName(raw)
      if (mapped) return mapped
      // Last resort: strip punctuation and retry common patterns
      const cleaned = lower.replace(/[^a-z\s]/g,' ').replace(/\s+/g,' ').trim()
      if (cleaned === 'united states' || cleaned === 'united states of america') return 'US'
      if (cleaned === 'canada') return 'CA'
      return raw.toUpperCase()
    }catch{ return '' }
  }

  useEffect(()=>{
    
  }, [log])

  // Keep URL in sync with the selected week for refresh/share
  useEffect(()=>{
    try{
      const ymd = fmtYMD(weekStart)
      const sp = new URLSearchParams(searchParams)
      if (sp.get('week_start') !== ymd){
        sp.set('week_start', ymd)
        setSearchParams(sp, { replace: true })
      }
    }catch{}
  }, [weekStart, searchParams, setSearchParams])

  // Close quick actions on outside click / ESC
  useEffect(()=>{
    if (!qaOpen) return
    const onDocClick = (e)=>{ if (qaRef.current && !qaRef.current.contains(e.target)) setQaOpen(false) }
    const onKey = (e)=>{ if (e.key === 'Escape') setQaOpen(false) }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return ()=>{ document.removeEventListener('mousedown', onDocClick); document.removeEventListener('keydown', onKey) }
  }, [qaOpen])

  const pushHeaderToast = (text, tone='success') => {
    const id = Math.random().toString(36).slice(2)
    setHeaderToasts(prev => [...prev, { id, text, tone, closing:false }])
    setTimeout(()=>{
      setHeaderToasts(prev => prev.map(t => t.id === id ? { ...t, closing:true } : t))
      setTimeout(()=> setHeaderToasts(prev => prev.filter(t => t.id !== id)), 260)
    }, 3800)
  }

  const fetchPlan = async (options={})=>{
    const { silent=false, preserveOnMissing=false } = options || {}
    if (!silent) { setLoading(true); setError(null) }
    try{
      const params = { week_start_date: fmtYMD(weekStart) }
      const resp = await api.get(`/meals/api/meal_plans/`, { params })
      const data = resp.data
      // Normalize various backend shapes to a single plan object with meals
      let normalized = null
      if (Array.isArray(data)) {
        // Try to match requested week_start_date
        normalized = data.find(p => p?.week_start_date === params.week_start_date) || data[0] || null
      } else if (data && Array.isArray(data.meal_plans)) {
        normalized = data.meal_plans.find(p => p?.week_start_date === params.week_start_date) || data.meal_plans[0] || null
      } else if (data && Array.isArray(data.results)) {
        normalized = data.results.find(p => p?.week_start_date === params.week_start_date) || data.results[0] || null
      } else if (data && data.meals) {
        normalized = data
      }
      if (normalized){
        setPlan(normalized)
        const id = (normalized||{}).id
        setMealPlanId(id||null)
        
        if (id){
          try{
            const details = await api.get(`/meals/api/meal_plans/${id}/`)
            const appr = Boolean(details?.data?.is_approved)
            setIsApproved(appr)
            
            if (details?.data?.meal_prep_preference){ setPrepPreference(details.data.meal_prep_preference) }
          }catch{ setIsApproved(null) }
        } else {
          setIsApproved(null)
        }
      } else {
        // During streaming or when explicitly preserving, do not clear UI state on missing
        if (!(preserveOnMissing || streamingRef.current)){
          setError('No plan found. Generate one below.')
          setPlan(null)
          setIsApproved(null)
          setMealPlanId(null)
        }
      }
    }catch(e){
      const status = e?.response?.status
      if (status === 401){
        window.location.href = '/login'
      }
      // During streaming or when explicitly preserving, do not surface missing as fatal
      if (!(preserveOnMissing || streamingRef.current)){
        setError('No plan found. Generate one below.')
        setPlan(null)
        setIsApproved(null)
        setMealPlanId(null)
      }
    }finally{ if (!silent) setLoading(false) }
  }

  // Auto-generate Instacart link for eligible users (US/CA with postal code) when a plan is loaded
  useEffect(()=>{
    try{
      const rawCountry = user?.address?.country || ''
      const country = normalizeCountryIso2(rawCountry)
      const postal = String(user?.postal_code || user?.address?.postalcode || '').trim()
      const eligible = (country === 'US' || country === 'CA') && Boolean(postal)
      
      if (!eligible || !mealPlanId){
        setInstacartUrl(null)
        setInstacartHasChefMeals(false)
        setInstacartError(null)
        
        return
      }
      if (instacartTriedForPlan === mealPlanId){
        return
      }
      setInstacartTriedForPlan(mealPlanId)
      ;(async ()=>{
        try{
          const resp = await api.post('/meals/api/generate-instacart-link/', { meal_plan_id: mealPlanId })
          const data = resp?.data || {}
          if (data.status !== 'success'){
            const msg = String(data.message || '')
            if (msg.includes('No eligible grocery items')){
              setInstacartError('Your plan contains only chef-created meals, so there’s nothing to send to Instacart.')
            } else {
              setInstacartError('Could not generate Instacart link.')
            }
            setInstacartUrl(null)
            setInstacartHasChefMeals(Boolean(data.has_chef_meals))
            return
          }
          if (data.has_chef_meals){
            setInstacartHasChefMeals(true)
          } else {
            setInstacartHasChefMeals(false)
          }
          if (data.instacart_url){
            setInstacartUrl(String(data.instacart_url))
            setInstacartError(null)
          } else {
            setInstacartUrl(null)
          }
        }catch(e){
          setInstacartError('Could not generate Instacart link.')
          setInstacartUrl(null)
        }
      })()
    }catch{}
  }, [mealPlanId, user?.address?.country, user?.postal_code, user?.address?.postalcode])

  // Lightweight poll to surface pending orders CTA
  useEffect(()=>{
    let alive = true
    const tick = async ()=>{
      try{
        const resp = await api.get('/meals/api/chef-meal-orders/', { params: { limit: 5 } })
        const rows = Array.isArray(resp?.data?.results) ? resp.data.results : (Array.isArray(resp?.data) ? resp.data : [])
        const pending = (rows||[]).some(r => !r.is_paid && (r.status === 'placed' || r.status === 'pending'))
        if (alive) setHasPendingOrders(Boolean(pending && !verifyingPaymentOrderId))
      }catch{ if (alive) setHasPendingOrders(false) }
    }
    tick()
    const id = setInterval(tick, 20000)
    return ()=>{ alive = false; clearInterval(id) }
  }, [verifyingPaymentOrderId])

  // Detect returning from Stripe Checkout via session_id or generic payment=success and show Orders
  useEffect(()=>{
    try{
      const sid = searchParams.get('session_id')
      
      const paid = searchParams.get('payment') === 'success'
      if (sid || paid){
        pushHeaderToast('Payment completed. Updating orders…', 'success')
        setTab('orders')
        try{ if (sid) localStorage.setItem('lastCheckoutSessionId', String(sid)) }catch{}
        const lastId = localStorage.getItem('lastPaymentOrderId')
        if (lastId){ setVerifyingPaymentOrderId(lastId); pollOrderPayment(lastId, sid) }
      }
    }catch{}
  }, [searchParams])

  // Poll a specific parent Order.id for paid/confirmed state
  const pollOrderPayment = async (orderId, sessionId=null)=>{
    try{
      const maxAttempts = 20
      
      for (let i=0; i<maxAttempts; i++){
        try{
          const params = (i === 0 && sessionId) ? { session_id: sessionId } : {}
          const resp = await api.get(`/meals/api/order-payment-status/${orderId}/`, { params })
          
          const data = resp?.data || {}
          const paid = Boolean(data?.is_paid)
          const status = String(data?.status || '').toLowerCase()
          const sessionStatus = String(data?.session_status || '').toLowerCase()
          const confirmed = ['confirmed','completed'].includes(status)
          if (paid || confirmed){
            try{ onOrdersReload() }catch{}
            pushHeaderToast('Payment confirmed.', 'success')
            localStorage.removeItem('lastPaymentOrderId')
            try{ localStorage.removeItem('lastCheckoutSessionId') }catch{}
            setVerifyingPaymentOrderId(null)
            return
          }
          // If session is not open and not paid, expose Try again (we'll let UI offer Pay again)
          if (sessionStatus && sessionStatus !== 'open'){
            break
          }
        }catch{}
        await new Promise(r => setTimeout(r, 1500))
      }
      // Timed out or session closed without payment
      pushHeaderToast('Payment not confirmed yet. You may need to try again.', 'error')
      setVerifyingPaymentOrderId(null)
      try{ localStorage.removeItem('lastPaymentOrderId') }catch{}
    }catch{}
  }

  const onOrdersReload = ()=>{
    try{ window.dispatchEvent(new CustomEvent('orders-reload')) }catch{}
  }

  const fetchChefMeals = async ()=>{
    // If user has no postal code, skip requests and surface hint
    if (!user?.postal_code && !(user?.address && user.address.postalcode)){
      log('fetchChefMeals skipped: missing postal code', { userPostal: user?.postal_code, addrPostal: user?.address?.postalcode })
      setChefMeals([])
      return
    }
    try{
      const params = { week_start_date: fmtYMD(weekStart), page_size: 50 }
      

      const resp = await api.get(`/meals/api/chef-meals-by-postal-code/`, { params })
      const data = resp?.data
      let list = []
      if (Array.isArray(data)) list = data
      else if (Array.isArray(data?.results)) list = data.results
      else if (Array.isArray(data?.data?.meals)) list = data.data.meals
      else if (Array.isArray(data?.meals)) list = data.meals
      else if (Array.isArray(data?.data)) list = data.data
      else if (data) list = data
      
      setChefMeals(Array.isArray(list) ? list : [])
    }catch(e){
      // Show a friendly hint if backend indicates missing postal code
      setChefMeals([])
      const detail = e?.response?.data?.code || e?.response?.data?.detail || ''
      try{ console.warn('[MealPlans] fetchChefMeals error', { status: e?.response?.status, data: e?.response?.data, detail }) }catch{}
      if (e?.response?.status === 400 || e?.response?.status === 422){
        console.warn('Chef meals request issue:', e?.response?.data)
        pushHeaderToast('Chef meals unavailable. Please set your postal code in Profile. Redirecting…', 'error')
        window.location.href = '/profile'
      }
    }
  }

  useEffect(()=>{
    
    fetchPlan(); fetchChefMeals()
  }, [weekStart])

  const shiftWeek = (delta)=>{
    const d = new Date(weekStart); d.setDate(d.getDate()+delta*7); const next = startOfWeek(d); setWeekStart(next)
    
  }

  const generatePlan = async ()=>{
    // Prevent generating a new plan if one already exists for the selected week
    if (mealPlanId && (plan?.week_start_date === fmtYMD(weekStart))){
      pushHeaderToast('A meal plan already exists for this week.', 'error')
      return
    }
    try{ esRef.current && esRef.current.close() }catch{}
    setError(null)
    setStreaming(true)
    streamingRef.current = true
    setProgressPct(0)
    setPlan(prev => prev && prev.week_start_date === fmtYMD(weekStart) ? prev : ({ id:null, week_start_date: fmtYMD(weekStart), meals: [] }))
    // proactively refresh the token to avoid 401 during initial connect
    try{ await refreshAccessToken() }catch{}
    const token = localStorage.getItem('accessToken')
    const openSSE = () => {
      const isDev = import.meta.env.DEV === true
      const apiBase = isDev ? '' : (import.meta.env.VITE_API_BASE || '')
      const url = `${apiBase}/meals/api/meal_plans/stream?week_start_date=${fmtYMD(weekStart)}`
      
      const es = token
        ? new EventSourcePolyfill(url, {
            headers: { Authorization: `Bearer ${token}` },
            withCredentials: false,
            heartbeatTimeout: 90000
          })
        : new EventSource(url)
      esRef.current = es
      return es
    }
    const es = openSSE()
    // simple fallback: do a one-off reconcile if nothing arrived soon
    try{ clearTimeout(fallbackRef.current) }catch{}
    // Soft reconcile after a delay without disrupting the in-progress client view
    fallbackRef.current = setTimeout(()=>{ if (esRef.current) fetchPlan({ silent:true, preserveOnMissing:true }) }, 12000)
    es.onopen = ()=> {}
    es.onerror = ()=> {}
    esRef.current.addEventListener('progress', (e)=>{
      try{ const { pct } = JSON.parse(e.data||'{}'); if (typeof pct === 'number') setProgressPct(pct) }catch{}
    })
    esRef.current.addEventListener('progress_update', (e)=>{
      try{ const { pct } = JSON.parse(e.data||'{}'); if (typeof pct === 'number') setProgressPct(pct) }catch{}
    })
    esRef.current.addEventListener('meal_added', (e)=>{
      try{
        const payload = JSON.parse(e.data||'{}')
        const m = payload.meal_plan_meal || payload
        if (!m) return
        setPlan(prev => {
          const current = prev || { id: mealPlanId, week_start_date: fmtYMD(weekStart), meals: [] }
          const list = Array.isArray(current.meals) ? [...current.meals] : (current.meal_plan_meals ? [...current.meal_plan_meals] : [])
          const mid = m.meal_plan_meal_id || m.id
          const idx = list.findIndex(x => (x.meal_plan_meal_id||x.id) === mid)
          if (idx >= 0) list[idx] = { ...list[idx], ...m }
          else list.push(m)
          return { ...current, meals: list }
        })
      }catch{}
    })
    esRef.current.addEventListener('meal', (e)=>{
      // fallback alias if backend emits 'meal'
      try{
        const m = JSON.parse(e.data||'{}')
        if (!m) return
        setPlan(prev => {
          const current = prev || { id: mealPlanId, week_start_date: fmtYMD(weekStart), meals: [] }
          const list = Array.isArray(current.meals) ? [...current.meals] : (current.meal_plan_meals ? [...current.meal_plan_meals] : [])
          const mid = m.meal_plan_meal_id || m.id
          const idx = list.findIndex(x => (x.meal_plan_meal_id||x.id) === mid)
          if (idx >= 0) list[idx] = { ...list[idx], ...m }
          else list.push(m)
          return { ...current, meals: list }
        })
      }catch{}
    })
    esRef.current.addEventListener('message', (e)=>{
      // default event; support {type, data}
      try{
        const msg = JSON.parse(e.data||'{}')
        if (msg && msg.type === 'progress' && typeof msg.pct === 'number') setProgressPct(msg.pct)
        if (msg && msg.type === 'meal_added' && msg.meal_plan_meal){
          const m = msg.meal_plan_meal
          setPlan(prev => {
            const current = prev || { id: mealPlanId, week_start_date: fmtYMD(weekStart), meals: [] }
            const list = Array.isArray(current.meals) ? [...current.meals] : (current.meal_plan_meals ? [...current.meal_plan_meals] : [])
            const mid = m.meal_plan_meal_id || m.id
            const idx = list.findIndex(x => (x.meal_plan_meal_id||x.id) === mid)
            if (idx >= 0) list[idx] = { ...list[idx], ...m }
            else list.push(m)
            return { ...current, meals: list }
          })
        }
        if (msg && (msg.type === 'done' || msg.done === true)){
          setProgressPct(100)
          setStreaming(false)
          try{ es.close() }catch{}
          esRef.current = null
          try{ clearTimeout(fallbackRef.current) }catch{}
          try{ clearInterval(pollRef.current) }catch{}
          fetchPlan()
        }
      }catch{}
    })
    esRef.current.addEventListener('done', async ()=>{
      setProgressPct(100)
      setStreaming(false)
      try{ es.close() }catch{}
      esRef.current = null
      try{ clearTimeout(fallbackRef.current) }catch{}
      try{ clearInterval(pollRef.current) }catch{}
      try{ clearTimeout(generationTimeoutRef.current) }catch{}
      await fetchPlan()
    })
    esRef.current.addEventListener('error', async ()=>{
      // Network/SSE hiccup: close the stream, keep streaming state true, and rely on polling
      try{ es.close() }catch{}
      esRef.current = null
      try{ clearTimeout(fallbackRef.current) }catch{}
      // Do NOT clear pollRef or toggle streaming here; keep button disabled and progress visible
      // Optionally nudge a silent reconcile without clearing UI if nothing arrives soon
      setTimeout(()=>{ if (streaming) fetchPlan({ silent:true, preserveOnMissing:true }) }, 3000)
    })

    // Fallback progressive polling if SSE events do not arrive
    try{ clearInterval(pollRef.current) }catch{}
    pollRef.current = setInterval(async ()=>{
      if (!streamingRef.current) return
      try{
        const params = { week_start_date: fmtYMD(weekStart) }
        const resp = await api.get('/meals/api/meal_plans/', { params })
        const data = resp.data
        let normalized = null
        if (Array.isArray(data)) normalized = data.find(p => p?.week_start_date === params.week_start_date) || data[0] || null
        else if (data && Array.isArray(data.meal_plans)) normalized = data.meal_plans.find(p => p?.week_start_date === params.week_start_date) || data.meal_plans[0] || null
        else if (data && Array.isArray(data.results)) normalized = data.results.find(p => p?.week_start_date === params.week_start_date) || data.results[0] || null
        else if (data && data.meals) normalized = data
        const incoming = normalized ? (Array.isArray(normalized.meals) ? normalized.meals : (Array.isArray(normalized.meal_plan_meals) ? normalized.meal_plan_meals : [])) : []
        if (normalized && incoming.length>0){
          setPlan(prev => {
            const current = prev || { id: normalized.id || null, week_start_date: fmtYMD(weekStart), meals: [] }
            const merged = [...(current.meals||[])]
            incoming.forEach(m => {
              const mid = m.meal_plan_meal_id || m.id
              const idx = merged.findIndex(x => (x.meal_plan_meal_id||x.id) === mid)
              if (idx>=0) { merged[idx] = { ...merged[idx], ...m } } else { merged.push(m) }
            })
            // rough progress if backend isn't emitting pct
            const pct = Math.min(100, Math.round((merged.length/expectedSlotsRef.current)*100))
            setProgressPct(pct)
            return { ...current, id: normalized.id || current.id, meals: merged }
          })
        }
      }catch(err){ }
    }, 1500)

    // Safety watchdog: keep UI in generating state for up to ~20 minutes, then finalize
    try{ clearTimeout(generationTimeoutRef.current) }catch{}
    generationTimeoutRef.current = setTimeout(async ()=>{
      if (!streaming) return
      setStreaming(false)
      try{ esRef.current && esRef.current.close() }catch{}
      esRef.current = null
      try{ clearTimeout(fallbackRef.current) }catch{}
      try{ clearInterval(pollRef.current) }catch{}
      try{ await fetchPlan() }catch{}
    }, 20 * 60 * 1000)
  }

  // Cleanup SSE on unmount and when week changes
  useEffect(()=>{ return ()=> { try{ esRef.current && esRef.current.close() }catch{} try{ clearTimeout(fallbackRef.current) }catch{} try{ clearInterval(pollRef.current) }catch{} try{ clearTimeout(completeRef.current) }catch{} try{ clearTimeout(generationTimeoutRef.current) }catch{} } }, [])
  useEffect(()=>{ try{ esRef.current && esRef.current.close() }catch{} esRef.current=null; setStreaming(false); setProgressPct(0); try{ clearTimeout(fallbackRef.current) }catch{} try{ clearInterval(pollRef.current) }catch{} try{ clearTimeout(generationTimeoutRef.current) }catch{} }, [weekStart])

  // Fallback: if backend never emits a final "done" event but progress reaches 100%,
  // finalize the stream shortly after to unblock the UI.
  useEffect(()=>{
    if (!streaming) return
    if (progressPct >= 100){
      try{ clearTimeout(completeRef.current) }catch{}
      completeRef.current = setTimeout(async ()=>{
        setStreaming(false)
        try{ esRef.current && esRef.current.close() }catch{}
        esRef.current = null
        try{ clearTimeout(fallbackRef.current) }catch{}
        try{ clearInterval(pollRef.current) }catch{}
        try{ await fetchPlan() }catch{}
      }, 1500)
    } else {
      try{ clearTimeout(completeRef.current) }catch{}
    }
  }, [progressPct, streaming])

  // Keep a live ref of streaming state to avoid stale-closure decisions in async handlers
  useEffect(()=>{ streamingRef.current = streaming }, [streaming])

  // Whether a plan already exists for the currently selected week
  const planExistsForWeek = Boolean(mealPlanId && plan && (plan.week_start_date === fmtYMD(weekStart)))

  return (
    <div className="page-plans">
      <div className="plans-header card" role="group" aria-label="Meal plan controls">
        <div className="left">
          <h2 style={{margin:'0 0 .25rem'}}>Meal Plans</h2>
          <div className="sub">Week of{' '}
            <button
              type="button"
              className="btn-link date-swap"
              title="Toggle date format"
              aria-label="Toggle date format"
              onClick={()=> setLongDate(v=>!v)}
            >
              <strong>{longDate ? fmtLong(weekStart) : fmtISO(weekStart)}</strong>
            </button>
          </div>
          <div className="jump-week" style={{marginTop:'.4rem', display:'inline-flex', alignItems:'center', gap:'.35rem'}}>
            <input id="jump-week" type="date" className="input" style={{width:150, padding:'.45rem .6rem'}} value={fmtYMD(weekStart)} onChange={(e)=>{
              try{ const d = new Date(e.target.value + 'T00:00:00'); setWeekStart(startOfWeek(d)) }catch{}
            }} />
          </div>
        </div>
        <div className="right">
          <div className="controls">
            <button className="btn btn-outline" onClick={()=>shiftWeek(-1)}>← Prev Week</button>
            <button className="btn btn-outline" onClick={()=>shiftWeek(1)}>Next Week →</button>
            <button
              className="btn btn-primary"
              onClick={generatePlan}
              disabled={streaming || planExistsForWeek}
              title={planExistsForWeek ? 'A meal plan already exists for this week. Change the week to generate a new one.' : 'Generate a new meal plan for this week'}
            >
              {streaming ? 'Generating…' : (
                planExistsForWeek ? (
                  <span style={{display:'inline-flex', alignItems:'center', gap:'.4rem'}}>
                    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <span>Generated</span>
                  </span>
                ) : 'Generate'
              )}
            </button>
          </div>
          <div className="tabs">
            <button className={`tab ${tab==='overview'?'active':''}`} onClick={()=>{ log('tab→overview'); setTab('overview') }}>Overview</button>
            <button className={`tab ${tab==='chefs'?'active':''}`} onClick={()=>{ log('tab→chefs'); setTab('chefs') }}>Chef Meals</button>
            <button className={`tab ${tab==='orders'?'active':''}`} onClick={()=>{ log('tab→orders'); setTab('orders') }}>Orders</button>
            <div className="menu-wrap" ref={qaRef}>
              <button
                className="btn btn-outline"
                aria-haspopup="menu"
                aria-expanded={qaOpen}
                onClick={()=> setQaOpen(v=>!v)}
              >
                Quick actions ▾
              </button>
              {qaOpen && (
                <div className="menu-pop" role="menu" aria-label="Quick actions">
                  <button className="menu-item" role="menuitem" onClick={()=> { setAddingPantry(true); setQaOpen(false) }}>Add Pantry Item</button>
                  <button className="menu-item" role="menuitem" onClick={()=> { setQuickHealth(true); setQaOpen(false) }}>Quick Log Health</button>
                  <div className="menu-divider" aria-hidden />
                  <Link className="menu-item" role="menuitem" to="/health" onClick={()=> setQaOpen(false)}>Open Health page →</Link>
          </div>
              )}
        </div>
      </div>
        </div>
      </div>
      {streaming && (
        <div className="container" style={{paddingTop:0}}>
          <div className="progress-row" aria-live="polite">
            <div className="progressbar" aria-label="Meal plan generation progress"><span style={{width: `${progressPct}%`}} /></div>
            <div>{progressPct}%</div>
          </div>
        </div>
      )}

      {/* Approval banner */}
      {isApproved === false && (
        <div className="card approval-card">
          <div className="approval-row">
            <div className="left">
              <div className="label">Meal prep preference</div>
              <div className="seg-control" role="group" aria-label="Meal prep preference">
                <button className={`seg ${prepPreference==='daily'?'active':''}`} onClick={()=> setPrepPreference('daily')}>Daily</button>
                <button className={`seg ${prepPreference==='one_day_prep'?'active':''}`} onClick={()=> setPrepPreference('one_day_prep')}>Bulk (one-day)</button>
              </div>
            </div>
            <div className="right">
              <button className="btn btn-primary" disabled={approving || !mealPlanId} onClick={async ()=>{
                if (!mealPlanId) return
                setApproving(true)
                try{
                  await api.post('/meals/api/approve_meal_plan/', { meal_plan_id: mealPlanId, meal_prep_preference: prepPreference })
                  setIsApproved(true)
                }catch(e){ pushHeaderToast('Approval failed. Please try again.', 'error') } finally { setApproving(false) }
              }}>{approving?'Approving…':'Approve meal plan'}</button>
            </div>
          </div>
          <div className="muted" style={{marginTop:'.25rem'}}>Chef-created meals may still require payment.</div>
        </div>
      )}

      {/* Post-approval helper to guide ordering flow */}
      {isApproved === true && (
        <div className="card" style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:'.5rem', flexWrap:'wrap'}}>
          <div className="muted">Your plan is approved. Browse and order available chef meals in your area.</div>
          <div style={{display:'flex', gap:'.5rem', alignItems:'center'}}>
            <button className="btn btn-outline" onClick={()=> setTab('orders')}>
              {verifyingPaymentOrderId ? 'Verifying payment…' : (hasPendingOrders ? 'View Pending Orders' : 'Orders')}
            </button>
            <button className="btn btn-primary" onClick={()=> setTab('chefs')}>Browse Chef Meals →</button>
            {(()=>{
              try{
                const rawCountry = user?.address?.country || ''
                const country = normalizeCountryIso2(rawCountry)
                const postal = String(user?.postal_code || user?.address?.postalcode || '').trim()
                const eligible = (country === 'US' || country === 'CA') && Boolean(postal)
                if (!eligible || !instacartUrl || instacartError) return null
                
                return (
                  <InstacartButton url={instacartUrl} text="Get Ingredients" />
                )
              }catch{ return null }
            })()}
          </div>
          {instacartHasChefMeals && (
            <div className="muted" style={{width:'100%'}}>
              Note: Chef-created meals are ordered from chefs and are not included in the Instacart list.
            </div>
          )}
        </div>
      )}

      {/* Instacart CTA section (US/CA only), only if not already shown inline above */}
      {(()=>{
        try{
          const rawCountry = user?.address?.country || ''
          const country = normalizeCountryIso2(rawCountry)
          const postal = String(user?.postal_code || user?.address?.postalcode || '').trim()
          const eligible = (country === 'US' || country === 'CA') && Boolean(postal)
          if (!eligible) return null
          if (isApproved !== true) return null
          const inlineShown = Boolean(isApproved === true && instacartUrl && !instacartError)
          if (inlineShown) return instacartError ? (
            <div className="card" style={{display:'grid', gap:'.5rem'}}>
              <div className="card" style={{borderColor:'#d9534f', marginBottom:'.5rem'}}>
                {instacartError}
              </div>
              <div style={{display:'flex', gap:'.5rem'}}>
                <button className="btn btn-outline" onClick={()=> setTab('chefs')}>View Chef Meals</button>
                <button className="btn btn-primary" onClick={()=> setTab('overview')}>Add Meals</button>
              </div>
            </div>
          ) : null
          return (
            <div className="card" style={{display:'grid', gap:'.5rem'}}>
              {instacartHasChefMeals && (
                <div className="callout" style={{marginBottom:'.25rem'}}>
                  <div className="icon" aria-hidden>ℹ️</div>
                  <div>Note: Chef-created meals are ordered from chefs and are not included in the Instacart list.</div>
                </div>
              )}
              {instacartError ? (
                <div>
                  <div className="card" style={{borderColor:'#d9534f', marginBottom:'.5rem'}}>
                    {instacartError}
                  </div>
                  <div style={{display:'flex', gap:'.5rem'}}>
                    <button className="btn btn-outline" onClick={()=> setTab('chefs')}>View Chef Meals</button>
                    <button className="btn btn-primary" onClick={()=> setTab('overview')}>Add Meals</button>
                  </div>
                </div>
              ) : (
                <div style={{textAlign:'center'}}>
                  <InstacartButton url={instacartUrl} text="Get Ingredients" />
                </div>
              )}
            </div>
          )
        }catch{ return null }
      })()}

      {loading && <div className="card">Loading…</div>}
      {!streaming && error && <div className="card" style={{borderColor:'#d9534f'}}>{error}</div>}

      {tab==='overview' && (
        <Overview
          plan={plan}
          weekStart={weekStart}
          chefMeals={chefMeals}
          isApproved={isApproved}
          mealPlanId={mealPlanId}
          onChange={()=>{ fetchPlan() }}
          onReplaceChef={()=> setTab('chefs')}
        />
      )}

      {tab==='chefs' && (
        user?.postal_code || (user?.address && user.address.postalcode) ? (
          <ChefMeals chefMeals={chefMeals} weekStart={weekStart} onChange={()=>{ fetchPlan(); fetchChefMeals() }} onNotify={pushHeaderToast} />
        ) : (
          <div className="card">Please set your postal code in your Profile to view chef meals near you.</div>
        )
      )}

      {tab==='orders' && (
        <OrdersTab onNotify={pushHeaderToast} verifyingOrderId={verifyingPaymentOrderId} setVerifyingOrderId={setVerifyingPaymentOrderId} onPollRequest={pollOrderPayment} />
      )}

      {/* Add Pantry Drawer */}
      {addingPantry && (
        <AddPantryDrawer
          open={addingPantry}
          onClose={()=> setAddingPantry(false)}
          onSuccess={(name)=> { pushHeaderToast(`Added "${name}" to your pantry.`, 'success'); setAddingPantry(false) }}
          onError={(msg)=> pushHeaderToast(msg || 'Failed to add pantry item.', 'error')}
        />
      )}

      {/* Quick Health Drawer */}
      {quickHealth && (
        <QuickHealthDrawer
          open={quickHealth}
          onClose={()=> setQuickHealth(false)}
          onSuccess={()=> { pushHeaderToast('Health metrics saved', 'success'); setQuickHealth(false) }}
          onError={(msg)=> pushHeaderToast(msg || 'Failed to save metrics', 'error')}
        />
      )}

      {/* Header-scoped toasts */}
      <ToastOverlay toasts={headerToasts} />
    </div>
  )
}

function OrdersTab({ onNotify, verifyingOrderId, setVerifyingOrderId, onPollRequest }){
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [orders, setOrders] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [cancelOrderId, setCancelOrderId] = useState(null)
  const [cancelReason, setCancelReason] = useState('')
  const [cancelSubmitting, setCancelSubmitting] = useState(false)

  // If we have a stored lastPaymentOrderId but verification wasn't started, start it
  useEffect(()=>{
    try{
      const last = localStorage.getItem('lastPaymentOrderId')
      const sid = localStorage.getItem('lastCheckoutSessionId') || null
      if (last && !verifyingOrderId){
        setVerifyingOrderId(last)
        onPollRequest && onPollRequest(last, sid)
      }
    }catch{}
  }, [])

  const reload = async (opts={})=>{
    const { silent=false } = opts
    if (!silent) { setLoading(true); setError(null) }
    try{
      const resp = await api.get('/meals/api/chef-meal-orders/', { params: { page, page_size: 10 } })
      const data = resp?.data
      const rows = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
      setOrders(rows)
      const tp = Number(data?.total_pages || 1)
      setTotalPages(tp)
    }catch(e){ if (!silent){ setError('Failed to load orders') } }
    finally{ if (!silent) setLoading(false) }
  }

  useEffect(()=>{ reload() }, [page])

  // Auto-refresh when window/tab gains focus after returning from Stripe
  useEffect(()=>{
    const onFocus = ()=> reload({ silent:true })
    window.addEventListener('focus', onFocus)
    return ()=> window.removeEventListener('focus', onFocus)
  }, [])

  // Short polling after mount to catch recent payments
  useEffect(()=>{
    let count = 0
    const id = setInterval(()=>{
      reload({ silent:true }); count += 1; if (count >= 24) clearInterval(id) // ~2 minutes at 5s
    }, 5000)
    return ()=> clearInterval(id)
  }, [])

  // Listen for external reload triggers (e.g., after payment confirmed)
  useEffect(()=>{
    const h = ()=> reload({ silent:true })
    window.addEventListener('orders-reload', h)
    return ()=> window.removeEventListener('orders-reload', h)
  }, [])

  const pay = async (orderId)=>{
    try{
      // Immediately mark verifying to guard against double-clicks
      try{ setVerifyingOrderId(String(orderId)) }catch{}
      // Guard: if we have a saved session_id for this order, try to reuse/finalize first
      let sid = null
      try{ sid = localStorage.getItem('lastCheckoutSessionId') || null }catch{}
      // Pre-check status first (Stripe-first)
      const resp = await api.get(`/meals/api/order-payment-status/${orderId}/`, { params: sid ? { session_id: sid } : {} })
      const s = resp?.data || {}
      if (s?.is_paid){
        onNotify && onNotify('Order already paid.', 'success')
        try{ localStorage.removeItem('lastPaymentOrderId'); localStorage.removeItem('lastCheckoutSessionId') }catch{}
        reload({ silent:true })
        setVerifyingOrderId(null)
        return
      }
      if (s?.session_status === 'open' && s?.session_url){
        try{
          localStorage.setItem('lastPaymentOrderId', String(orderId))
          if (s?.session_id) localStorage.setItem('lastCheckoutSessionId', String(s.session_id))
          setVerifyingOrderId(String(orderId))
        }catch{}
        window.location.href = s.session_url
        return
      }
      // Store for post-return polling and create a new session
      try{ localStorage.setItem('lastPaymentOrderId', String(orderId)); setVerifyingOrderId(String(orderId)) }catch{}
      const make = await api.post(`/meals/api/process-chef-meal-payment/${orderId}/`)
      const url = make?.data?.session_url || (make?.data?.data && make.data.data.session_url)
      const newSid = make?.data?.session_id || (make?.data?.data && make.data.data.session_id)
      try{ if (newSid) localStorage.setItem('lastCheckoutSessionId', String(newSid)) }catch{}
      if (url){ window.location.href = url }
      else { onNotify && onNotify('Payment link not available.', 'error') }
    }catch(e){
      const status = e?.response?.status
      if (status === 404){ onNotify && onNotify("We couldn't find your order.", 'error') }
      else { onNotify && onNotify('Failed to initiate payment.', 'error') }
      try{ setVerifyingOrderId(null) }catch{}
    }
  }

  const resend = async (orderId)=>{
    try{
      await api.post(`/meals/api/resend-payment-link/${orderId}/`)
      onNotify && onNotify('Payment link resent.', 'success')
    }catch{ onNotify && onNotify('Failed to resend link.', 'error') }
  }

  const cancel = async (orderId, reason)=>{
    try{
      await api.post(`/meals/api/chef-meal-orders/${orderId}/cancel/`, { reason })
      onNotify && onNotify('Order canceled.', 'success')
      setOrders(prev => prev.filter(o => o.id !== orderId))
    }catch{ onNotify && onNotify('Failed to cancel order.', 'error') }
  }

  if (loading) return <div className="card">Loading orders…</div>
  if (error) return <div className="card" style={{borderColor:'#d9534f'}}>{error}</div>
  if (!orders || orders.length===0) return <div className="card">No orders yet. <button className="btn btn-link" onClick={()=> reload()}>Refresh</button></div>

  return (
    <div>
      <div className="card" style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <div className="muted">Manage your chef meal orders.</div>
        <button className="btn btn-outline btn-sm" onClick={()=> reload()}>Refresh</button>
      </div>
      <div className="grid grid-2">
        {(() => {
          const groups = new Map()
          ;(orders||[]).forEach(o => {
            const parentId = o?.order || o?.order_id || (o?.order && o.order.id) || 'ungrouped'
            if (!groups.has(parentId)) groups.set(parentId, [])
            groups.get(parentId).push(o)
          })
          return Array.from(groups.entries()).map(([parentId, items]) => {
            const unpaid = items.some(i => !i?.is_paid)
            const verifying = parentId && String(parentId) === String(verifyingOrderId||'')
            return (
              <div key={String(parentId)} className="card">
                <h3 style={{marginTop:0}}>Chef meal {items.length>1?'orders':'order'}</h3>
                <ul style={{margin:'0 0 .5rem 1rem', padding:0}}>
                  {items.map(i => (
                    <li key={i.id} style={{marginBottom:'.25rem', listStyle:'disc'}}>
                      <span>{i.meal_event_details?.meal_name || i.meal_name}</span>
                      <span className="muted"> — {i.meal_event_details?.event_date} {i.meal_event_details?.event_time}</span>
                      <span> • Qty {i.quantity}</span>
                      {i.total_price ? <span> • ${i.total_price}</span> : null}
                      {i.status && <span> • {i.status}</span>}
                      {i.status !== 'canceled' && (
                        <button className="btn btn-outline btn-sm" style={{marginLeft:'.5rem'}} onClick={()=> { setCancelOrderId(i.id); setCancelReason('') }}>
                          Cancel item
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                <div style={{display:'flex', gap:'.5rem', flexWrap:'wrap'}}>
                  {unpaid && (parentId !== 'ungrouped') && (
                    <button className="btn btn-primary" onClick={()=> !verifying && pay(parentId)} disabled={verifying}>
                      {verifying ? 'Verifying payment…' : 'Pay now'}
                    </button>
                  )}
                  {unpaid && (parentId !== 'ungrouped') && (
                    <button className="btn btn-outline" onClick={()=> !verifying && resend(parentId)} disabled={verifying}>Resend payment link</button>
                  )}
                  {verifying && (
                    <button className="btn btn-outline" onClick={()=> onPollRequest && onPollRequest(parentId)}>Re-check now</button>
                  )}
                </div>
              </div>
            )
          })
        })()}
      </div>
      <div className="card" style={{display:'flex', alignItems:'center', justifyContent:'center', gap:'.5rem'}}>
        <button className="btn btn-outline btn-sm" disabled={page<=1} onClick={()=> setPage(p=> Math.max(1, p-1))}>← Prev</button>
        <div className="muted" style={{minWidth:80, textAlign:'center'}}>{page} / {totalPages}</div>
        <button className="btn btn-outline btn-sm" disabled={page>=totalPages} onClick={()=> setPage(p=> Math.min(totalPages, p+1))}>Next →</button>
      </div>

      {cancelOrderId && (
        <div className="card" role="dialog" aria-label="Cancel order" style={{position:'fixed', left:'50%', top:'20%', transform:'translateX(-50%)', zIndex:1000, maxWidth:520, width:'90%'}}>
          <h3 style={{marginTop:0}}>Cancel Order Item</h3>
          <label className="label" htmlFor="cancel-reason">Reason for cancellation</label>
          <textarea id="cancel-reason" className="textarea" rows={3} placeholder="e.g., scheduling conflict, no longer needed" value={cancelReason} onChange={e=> setCancelReason(e.target.value)} />
          <div className="actions-row" style={{marginTop:'.5rem'}}>
            <button className="btn btn-outline" onClick={()=> { setCancelOrderId(null); setCancelReason('') }} disabled={cancelSubmitting}>Back</button>
            <button className="btn btn-danger" onClick={async ()=>{
              const reason = (cancelReason||'').trim()
              if (!reason){ onNotify && onNotify('Please provide a reason.', 'error'); return }
              setCancelSubmitting(true)
              try{ await cancel(cancelOrderId, reason); setCancelOrderId(null); setCancelReason('') }
              finally{ setCancelSubmitting(false) }
            }} disabled={cancelSubmitting}>Confirm cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}

function groupByDay(meals){
  const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
  const out = {}; days.forEach(d=> out[d]=[])
  ;(meals||[]).forEach(m => {
    const d = m.day || m.date_label || m.day_of_week || 'Unknown'
    out[d] = out[d] || []
    out[d].push(m)
  })
  return out
}

function Overview({ plan, weekStart, chefMeals, isApproved, mealPlanId, onChange, onReplaceChef }){
  const [selectedSlot, setSelectedSlot] = useState(null) // { day, meal, rect }
  const [working, setWorking] = useState(false)
  const [error, setError] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [updatePreview, setUpdatePreview] = useState(null) // {old_meal, new_meal, ...}
  const [replacingId, setReplacingId] = useState(null)
  const [expandedDescIds, setExpandedDescIds] = useState(()=> new Set())
  const [reviewing, setReviewing] = useState(null) // { id, name }
  const [reviewScore, setReviewScore] = useState(5)
  const [reviewComment, setReviewComment] = useState('')
  const [reviewSubmitting, setReviewSubmitting] = useState(false)
  const [updatedIds, setUpdatedIds] = useState(()=> new Set())
  const [toasts, setToasts] = useState([]) // {id, text, tone, closing}
  const [promptHint, setPromptHint] = useState(false)
  // Empty-slot replacement panel state
  const [slotPanel, setSlotPanel] = useState(null) // { day, type }
  const [slotAlts, setSlotAlts] = useState([])
  const [slotAltId, setSlotAltId] = useState('')
  const [slotLoading, setSlotLoading] = useState(false)
  const [slotPosting, setSlotPosting] = useState(false)

  const todayISO = fmtYMD(new Date())
  function dayIsPast(dayName){
    try{
      const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
      const offset = map[String(dayName)] ?? 0
      const d = new Date(weekStart); d.setDate(d.getDate()+offset)
      return fmtYMD(d) < todayISO
    }catch{ return false }
  }

  async function openSlotPanel(day, type){
    try{
      const key = `${day}|${type}`
      // If a meal now occupies this slot, open edit instead of add panel
      const existing = mealBySlot && mealBySlot[key]
      if (existing){
        setSelectedSlot({ day, meal: existing, rect: null })
        return
      }
    }catch{}
    setSlotPanel({ day, type })
    setSlotLoading(true); setSlotAlts([]); setSlotAltId('')
    try{
      const payload = { week_start_date: fmtYMD(weekStart), day, meal_type: type }
      const r = await api.post('/meals/api/suggest_alternatives_for_slot/', payload)
      const alts = Array.isArray(r?.data?.alternatives) ? r.data.alternatives : []
      // Merge in chef meals that match this day/type
      const dateIso = dayToDateString(weekStart, day)
      const typeNorm = String(type||'').toLowerCase()
      const chefAlts = (chefMeals||[]).flatMap(cm => {
        try{
          const cmType = String(cm.meal_type || cm.type || '').toLowerCase()
          if (cmType && typeNorm && cmType !== typeNorm) return []
          if (cm.available_dates && typeof cm.available_dates === 'object'){
            const info = cm.available_dates[dateIso]
            if (!info) return []
            const eventId = info?.event_id || info?.id || cm.event_id || cm.id
            if (!eventId) return []
            return [{ is_chef_meal:true, meal_id:eventId, name: cm.name || cm.meal_name, chef: cm.chef || cm.chef_name, start_date: dateIso }]
          }
          if (cm.date){
            try{
              const matches = String(cm.date).slice(0,10) === dateIso
              if (!matches) return []
              const eventId = cm.event_id || cm.id
              if (!eventId) return []
              return [{ is_chef_meal:true, meal_id:eventId, name: cm.name || cm.meal_name, chef: cm.chef || cm.chef_name, start_date: dateIso }]
            }catch{ return [] }
          }
        }catch{ return [] }
        return []
      })
      const merged = [...alts]
      chefAlts.forEach(a => { if (!merged.some(x => String(x.meal_id) === String(a.meal_id))) merged.push(a) })
      setSlotAlts(merged)
      setSlotAltId(merged[0] ? `${merged[0].is_chef_meal?'c':'u'}:${merged[0].meal_id}` : '')
    }catch{ setSlotAlts([]); setSlotAltId('') } finally { setSlotLoading(false) }
  }

  const pushToast = (text, tone='error')=>{
    const id = Math.random().toString(36).slice(2)
    setToasts(prev => [...prev, { id, text, tone, closing:false }])
    setTimeout(()=> {
      // trigger fade-out
      setToasts(prev => prev.map(t => t.id === id ? { ...t, closing:true } : t))
      // remove after transition
      setTimeout(()=> setToasts(prev => prev.filter(t => t.id !== id)), 260)
    }, 3800)
  }

  // simple event bridge so RightEditPanel can open review drawer without prop drilling
  useEffect(()=>{
    const handler = (e)=>{
      const detail = e.detail || {}
      if (detail.id) setReviewing({ id: detail.id, name: detail.name || 'Meal' })
    }
    window.addEventListener('open-review', handler)
    return ()=> window.removeEventListener('open-review', handler)
  }, [])

  // Reset rating/comment when opening the review drawer
  useEffect(()=>{
    if (reviewing){
      setReviewScore(5)
      setReviewComment('')
    }
  }, [reviewing])
  if (!plan) return <div className="card">No plan available for this week.</div>
  const meals = Array.isArray(plan?.meals) ? plan.meals : (plan?.meal_plan_meals || [])
  const grouped = groupByDay(meals || [])
  const dayOrder = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
  const typeOrder = ['Breakfast','Lunch','Dinner']
  const flatRows = Object.keys(grouped).flatMap(day => (grouped[day]||[]).map(m => ({ ...m, __day: day })))
    .sort((a,b)=> dayOrder.indexOf(a.__day) - dayOrder.indexOf(b.__day)
      || typeOrder.indexOf((a.meal_type||a.type)) - typeOrder.indexOf((b.meal_type||b.type)))

  // Build a map of existing slots to detect missing ones
  const existingSlots = new Set((flatRows||[]).map(r => `${r.__day}|${r.type||r.meal_type}`))
  const allSlots = []
  dayOrder.forEach(day => {
    typeOrder.forEach(t => { allSlots.push({ day, type: t }) })
  })
  const mealBySlot = {}
  ;(flatRows||[]).forEach(r => { mealBySlot[`${r.__day}|${r.type||r.meal_type}`] = r })
  const combinedRows = allSlots.map(s => {
    const key = `${s.day}|${s.type}`
    const m = mealBySlot[key]
    return m ? { kind:'meal', m } : { kind:'placeholder', s }
  })

  // Keep the open edit panel in sync with the latest plan data
  // When the plan refreshes after an update, replace the meal in selectedSlot
  // with the corresponding fresh meal object from the new plan so the panel UI updates
  useEffect(()=>{
    try{
      if (!selectedSlot) return
      const currentId = selectedSlot?.meal?.meal_plan_meal_id || selectedSlot?.meal?.id
      if (!currentId) return
      const updated = (meals||[]).find(x => (x.meal_plan_meal_id || x.id) === currentId)
      if (!updated) return
      // Replace only the meal payload; preserve slot metadata and rect
      setSelectedSlot(prev => prev ? ({ ...prev, meal: { ...updated } }) : prev)
    }catch{}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meals, selectedSlot?.meal?.meal_plan_meal_id, selectedSlot?.meal?.id])

  const toggleDesc = (rowId)=>{
    setExpandedDescIds(prev => {
      const next = new Set(prev)
      if (next.has(rowId)) next.delete(rowId); else next.add(rowId)
      return next
    })
  }

  const jumpToSlot = (day, mealType)=>{
    const target = (meals||[]).find(x => (x.day||x.day_of_week)===day && (x.meal_type||x.type)===mealType)
    if (target){
      setSelectedSlot({ day, meal: target, rect: null })
      const rowId = target.meal_plan_meal_id || target.id || target.meal?.id
      if (rowId){
        const el = document.getElementById(`row-${rowId}`)
        el?.scrollIntoView({ behavior:'smooth', block:'center' })
      }
    }
  }

  const onSelect = async (day, meal, ev) => {
    try{
      const r = ev?.currentTarget?.getBoundingClientRect?.()
      const rect = r ? { top: r.top + window.scrollY, left: r.left + window.scrollX, right: r.right + window.scrollX, bottom: r.bottom + window.scrollY, width: r.width } : null
      setSelectedSlot({ day, meal, rect })
      // If plan is approved, offer review for all meals; if not approved, only show review if this meal has been reviewed before
      try{
        if (meal?.meal?.id || meal?.meal_id || meal?.id){
          const mealId = meal.meal?.id || meal.meal_id || meal.id
          // fetch existing reviews for this meal; if exists or plan approved, allow review button
          const resp = await api.get(`/reviews/api/meal/${mealId}/reviews/`)
          const hasAnyReviews = Array.isArray(resp.data) && resp.data.length > 0
          // Attach flags on meal object
          meal.__hasReviews = hasAnyReviews
          meal.__canReview = Boolean(isApproved || hasAnyReviews)
          // Force re-render so RightEditPanel sees updated flag
          setSelectedSlot(prev => prev ? ({ ...prev, meal: { ...meal } }) : prev)
        }
      }catch{ /* non-blocking */ }
    }catch{
      setSelectedSlot({ day, meal, rect: null })
    }
  }

  async function deleteMeal(meal){
    setWorking(true); setError(null)
    try{
      const id = meal.meal_plan_meal_id || meal.id
      await api.delete('/meals/api/remove_meal_from_plan/', { data: { meal_plan_meal_ids: [id] } })
      onChange && onChange()
      setSelectedSlot(null)
    }catch(e){ pushToast('Unable to delete meal.', 'error') } finally { setWorking(false) }
  }

  function dayToDateString(weekStartDate, dayName){
    const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
    const offset = map[dayName] ?? 0
    const d = new Date(weekStartDate)
    d.setDate(d.getDate()+offset)
    return fmtYMD(d)
  }

  async function modifyMeal(meal){

    pushToast('Applying changes…', 'info')
    setWorking(true); setError(null); setUpdatePreview(null)
    setReplacingId(meal.meal_plan_meal_id || meal.id)
    try{
      const mealPlanMealId = meal.meal_plan_meal_id || meal.id
      const mealDate = dayToDateString(weekStart, meal.day || meal.day_of_week)
      // Send arrays; user_id will be attached by the request interceptor
      const resp = await api.post('/meals/api/update_meals_with_prompt/', {
        prompt,
        meal_plan_meal_ids: [mealPlanMealId],
        meal_dates: [mealDate],
      })
      const updates = resp?.data?.updates || []
      if (updates.length > 0){
        setUpdatePreview(updates[0])
        pushToast('Update submitted', 'success')
      } else {
        setUpdatePreview({ none: true })
        pushToast('No changes were needed', 'info')
      }
      // Mark row as updated (temporary chip)
      setUpdatedIds(prev => {
        const next = new Set(prev); next.add(mealPlanMealId); return next
      })
      setTimeout(()=>{
        setUpdatedIds(prev => { const next = new Set(prev); next.delete(mealPlanMealId); return next })
      }, 2500)
      onChange && onChange()
    }catch(e){
      const status = e?.response?.status
      const data = e?.response?.data
      let msg = 'Unable to apply changes.'
      if (data){
        if (typeof data === 'string') msg = data
        else if (data.error) msg = data.error
        else if (data.message) msg = data.message
      }
      setError(null)
      pushToast(msg, 'error')
    } finally { setWorking(false); setReplacingId(null) }
  }

  async function replaceWithAlternative(meal, alternative){
    setWorking(true); setError(null)
    const mealPlanMealId = meal.meal_plan_meal_id || meal.id
    setReplacingId(mealPlanMealId)
    try{
      const mpmId = mealPlanMealId
      const payload = alternative.is_chef_meal
        ? { meal_plan_meal_id: mpmId, chef_meal_id: alternative.meal_id }
        : { meal_plan_meal_id: mpmId, new_meal_id: alternative.meal_id }
      await api.put('/meals/api/replace_meal_plan_meal/', payload)
      // Mark row as updated
      setUpdatedIds(prev => { const next = new Set(prev); next.add(mealPlanMealId); return next })
      setTimeout(()=> setUpdatedIds(prev => { const next = new Set(prev); next.delete(mealPlanMealId); return next }), 2500)
      onChange && onChange()
      setSelectedSlot(null)
    }catch(e){
      const msg = e?.response?.data?.error || e?.response?.data?.detail || 'Unable to replace meal.'
      pushToast(msg, 'error')
    }finally{
      setWorking(false); setReplacingId(null)
    }
  }

  return (
    <div className="card" style={{padding:0}}>
      <table className="plans-table">
        <thead>
          <tr>
            <th>Day</th>
            <th>Meal</th>
            <th>Name</th>
            <th>Description</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {combinedRows.map((row, idx) => {
            if (row.kind === 'meal'){
              const m = row.m
            const day = m.__day
            const type = m.type || m.meal_type
            const title = m.name || m.meal?.name
            const desc = m.meal?.description || m.description || ''
              const id = m.meal_plan_meal_id || m.id || m.meal?.id || `${day}-${idx}`
            const replacing = replacingId === (m.meal_plan_meal_id || m.id)
            const isChefMeal = Boolean(
              m.is_chef_meal || m.meal?.is_chef_meal || m.source === 'chef' || m.meal?.source === 'chef' ||
              m.meal?.chef || m.meal?.chef_name || m.chef || m.chef_name
            )
            return (
              <tr key={id} id={`row-${id}`} className={`${replacing ? 'replacing' : ''} ${isChefMeal ? 'chef-meal-row' : ''}`.trim()}>
                <td className="col-day">{day}</td>
                <td className="col-type">{type}</td>
                <td className="col-name">
                  <span>{title}</span>
                  {isChefMeal && <span className="chip small" style={{marginLeft:'.35rem'}}>Chef</span>}
                  <button
                    className="btn-link"
                    style={{marginLeft:'.35rem'}}
                    onClick={(e)=>{
                      e.stopPropagation()
                      const mealName = title || 'this meal'
                      const mealId = (m?.meal && (m.meal.id || m.meal.meal_id)) || m?.meal_id || m?.id || ''
                      const q = `Can you tell me more about ${mealName}?`
                      const url = `/chat?topic=${encodeURIComponent(mealName)}&meal_id=${encodeURIComponent(mealId)}&q=${encodeURIComponent(q)}`
                      window.open(url,'_self')
                    }}
                  >Ask</button>
                </td>
                <td className="col-desc" title={desc}>
                  <div className={`desc-clamp ${expandedDescIds.has(id)?'expanded':''}`}>{desc}</div>
                  {desc && (
                    <button className="btn-link" onClick={(ev)=>{ ev.stopPropagation(); toggleDesc(id) }}>
                      {expandedDescIds.has(id) ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </td>
                <td className="col-actions">
                    {dayIsPast(day) ? (
                      <span className="muted">Past</span>
                    ) : replacing ? (
                    <div className="updating-chip"><span className="spinner" /> Updating…</div>
                  ) : updatedIds.has(id) ? (
                    <div className="updated-chip">Updated</div>
                  ) : (
                    <button className="btn btn-outline btn-sm" onClick={(ev)=> { ev.stopPropagation(); onSelect(day, m) }}>Edit</button>
                  )}
                  </td>
                </tr>
              )
            }
            const s = row.s
            return (
            <tr key={`ph-${s.day}-${s.type}-${idx}`} className="placeholder-row">
                <td className="col-day">{s.day}</td>
                <td className="col-type">{s.type}</td>
                <td className="placeholder-cell" colSpan={3}>
                  <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:'.75rem'}}>
                    {dayIsPast(s.day) ? (
                      <div>No meal was planned for this day.</div>
                    ) : (
                      <>
                        <div style={{display:'flex', alignItems:'center', gap:'.6rem'}}>
                          <span>No meal yet. Select a replacement or generate one for this slot.</span>
                        </div>
                        <div style={{display:'flex', gap:'.5rem'}}>
                          <button className="btn btn-outline btn-sm" onClick={()=> openSlotPanel(s.day, s.type)}>Find replacement</button>
                        </div>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {typeof slotPanel !== 'undefined' && slotPanel && (
        <>
          <div className="right-panel-overlay" onClick={()=> { setSlotPanel(null); setSlotAlts([]); setSlotAltId('') }} />
          <aside className="right-panel" role="dialog" aria-label={`Add meal for ${slotPanel.day} ${slotPanel.type}`}>
            <div className="right-panel-head">
              <div className="slot-title">Add meal — {slotPanel.day} {slotPanel.type}</div>
              <button className="icon-btn" aria-label="Close" onClick={()=> { setSlotPanel(null); setSlotAlts([]); setSlotAltId('') }}>✕</button>
            </div>
            <div className="right-panel-body">
              <div className="label">Alternatives</div>
      {slotLoading && <div className="muted">Loading suggestions…</div>}
              {!slotLoading && slotAlts.length === 0 && (
        <div className="muted" style={{marginBottom:'.5rem'}}>No alternatives yet.</div>
              )}
              {slotAlts.length > 0 && (
                <select className="select" value={slotAltId} onChange={e=> setSlotAltId(e.target.value)}>
                  {slotAlts.map(a => {
                    const label = a.is_chef_meal
                      ? `${a.chef ? `Chef ${a.chef}` : 'Chef'} — ${a.name}${a.start_date ? ` — ${new Date(a.start_date).toLocaleDateString()} (Available)` : ''}`
                      : `${a.name}`
                    return <option key={`${a.is_chef_meal?'c':'u'}-${a.meal_id}`} value={`${a.is_chef_meal?'c':'u'}:${a.meal_id}`}>{label}</option>
                  })}
                </select>
              )}
              <div className="actions-row" style={{marginTop:'.5rem'}}>
                <button className="btn btn-outline" onClick={async ()=>{
                  // Use backend suggest_alternatives_for_slot exclusively
                  setSlotLoading(true)
                  try{
                    const payload = { week_start_date: fmtYMD(weekStart), day: slotPanel.day, meal_type: slotPanel.type }
                    const r = await api.post('/meals/api/suggest_alternatives_for_slot/', payload)
                    const alts = Array.isArray(r?.data?.alternatives) ? r.data.alternatives : []
                    const dateIso = dayToDateString(weekStart, slotPanel.day)
                    const typeNorm = String(slotPanel.type||'').toLowerCase()
                    const chefAlts = (chefMeals||[]).flatMap(cm => {
                      try{
                        const cmType = String(cm.meal_type || cm.type || '').toLowerCase()
                        if (cmType && typeNorm && cmType !== typeNorm) return []
                        if (cm.available_dates && typeof cm.available_dates === 'object'){
                          const info = cm.available_dates[dateIso]
                          if (!info) return []
                          const eventId = info?.event_id || info?.id || cm.event_id || cm.id
                          if (!eventId) return []
                          return [{ is_chef_meal:true, meal_id:eventId, name: cm.name || cm.meal_name, chef: cm.chef || cm.chef_name, start_date: dateIso }]
                        }
                        if (cm.date){
                          try{
                            const matches = String(cm.date).slice(0,10) === dateIso
                            if (!matches) return []
                            const eventId = cm.event_id || cm.id
                            if (!eventId) return []
                            return [{ is_chef_meal:true, meal_id:eventId, name: cm.name || cm.meal_name, chef: cm.chef || cm.chef_name, start_date: dateIso }]
                          }catch{ return [] }
                        }
                      }catch{ return [] }
                      return []
                    })
                    const merged = [...alts]
                    chefAlts.forEach(a => { if (!merged.some(x => String(x.meal_id) === String(a.meal_id))) merged.push(a) })
                    setSlotAlts(merged)
                    setSlotAltId(merged[0] ? `${merged[0].is_chef_meal?'c':'u'}:${merged[0].meal_id}` : '')
                  }catch{ setSlotAlts([]); setSlotAltId('') } finally { setSlotLoading(false) }
                }}>Refresh</button>
                {(()=>{
                  const occupied = Boolean(mealBySlot && mealBySlot[`${slotPanel.day}|${slotPanel.type}`])
                  return (
                    <button className="btn btn-primary" disabled={!slotAltId || occupied || slotPosting} onClick={async ()=>{
                      // If this slot just became occupied, switch to edit
                      const current = mealBySlot && mealBySlot[`${slotPanel.day}|${slotPanel.type}`]
                      if (current){ setSlotPanel(null); setSelectedSlot({ day: slotPanel.day, meal: current, rect: null }); return }
                  const chosen = (slotAlts||[]).find(a => `${a.is_chef_meal?'c':'u'}:${a.meal_id}` === slotAltId)
                  if (!chosen) return
                  try{
                        setSlotPosting(true)
                    // show transient spinner on the placeholder line by reusing updating chip via local flag
                    const payload = { week_start_date: fmtYMD(weekStart), day: slotPanel.day, meal_type: slotPanel.type }
                    if (chosen.is_chef_meal) payload.chef_meal_id = chosen.meal_id; else payload.new_meal_id = chosen.meal_id
                    let resp
                    try{
                          const idem = newIdempotencyKey && newIdempotencyKey()
                          // Avoid custom headers to prevent CORS preflight failures; include key in body if needed
                          resp = await api.post('/meals/api/fill_meal_slot/', idem ? { ...payload, idempotency_key: idem } : payload)
                    }catch(e){
                      // Fallback for older server: try add_meal_slot
                          try{
                            const idem2 = newIdempotencyKey && newIdempotencyKey()
                            resp = await api.post('/meals/api/add_meal_slot/', idem2 ? { ...payload, idempotency_key: idem2 } : payload)
                          }catch(e2){ throw (e2 || e) }
                    }
                    const created = resp?.data?.meal_plan_meal
                        // Always refresh via parent so state is single-sourced
                        onChange && onChange()
                        // Optional chip/scroll with returned id once data is present
                        if (created){
                          const newId = created.meal_plan_meal_id || created.id
                          if (newId){
                            setUpdatedIds(prev => { const next = new Set(prev); next.add(newId); return next })
                            setTimeout(()=>{
                              setUpdatedIds(prev => { const next = new Set(prev); next.delete(newId); return next })
                            }, 2500)
                            setTimeout(()=>{
                              try{ document.getElementById(`row-${newId}`)?.scrollIntoView({ behavior:'smooth', block:'center' }) }catch{}
                            }, 400)
                          }
                        }
                    setSlotPanel(null); setSlotAlts([]); setSlotAltId('')
                  }catch(e){
                    const msg = e?.response?.data?.detail || e?.response?.data?.error || e?.response?.data?.errors || e?.message || 'Failed to add meal to this slot.'
                    pushToast(msg, 'error')
                  }
                      finally { setSlotPosting(false) }
                    }}>{slotPosting ? 'Adding…' : 'Add to plan'}</button>
                  )
                })()}
              </div>
              <div className="muted" style={{marginTop:'.35rem'}}>Chef meals are prioritized when available for this day and meal type.</div>
            </div>
          </aside>
        </>
      )}
      {/* Review drawer */}
      {reviewing && (
        <>
          <div className="right-panel-overlay" onClick={()=> setReviewing(null)} />
          <aside className="right-panel" role="dialog" aria-label={`Review ${reviewing.name}`} style={{zIndex:50}}>
            <div className="right-panel-head">
              <div className="slot-title">Rate "{reviewing.name}"</div>
              <button className="icon-btn" onClick={()=> setReviewing(null)}>✕</button>
            </div>
            <div className="right-panel-body">
              <label className="label">Rating</label>
              <div style={{display:'flex', gap:'.35rem', alignItems:'center', marginBottom:'.6rem'}}>
                {[1,2,3,4,5].map(n => (
                  <button key={n} className={`star ${reviewScore>=n?'on':''}`} onClick={()=> setReviewScore(n)} aria-label={`${n} star${n>1?'s':''}`}>★</button>
                ))}
              </div>
              <label className="label">Comment (optional)</label>
              <textarea className="textarea" rows={3} value={reviewComment} onChange={e=> setReviewComment(e.target.value)} placeholder="Share what you liked or ideas to improve…" style={{marginBottom:'.6rem'}} />
              <button className="btn btn-primary" disabled={reviewSubmitting} onClick={async ()=>{
                setReviewSubmitting(true)
                try{
                  await api.post(`/reviews/api/meal/${reviewing.id}/review/`, { rating: reviewScore, comment: reviewComment, meal_plan_id: mealPlanId })
                  setReviewing(null)
                }catch{ pushToast('Failed to submit review', 'error') } finally { setReviewSubmitting(false) }
              }}>{reviewSubmitting?'Submitting…':'Submit Review'}</button>
              <div className="muted" style={{marginTop:'.5rem'}}>Tap a star and press Submit Review. You can update your rating later.</div>
            </div>
          </aside>
        </>
      )}
      {selectedSlot && (
        <RightEditPanel
          open={Boolean(selectedSlot)}
          slot={selectedSlot}
          meal={selectedSlot.meal}
          weekStart={weekStart}
          mealPlanId={mealPlanId}
          chefMeals={chefMeals}
          prompt={prompt}
          setPrompt={setPrompt}
          promptHint={promptHint}
          clearPromptHint={()=> setPromptHint(false)}
          working={working}
          error={error}
          updatePreview={updatePreview}
          onJumpToSlot={jumpToSlot}
          onClose={()=> { setSelectedSlot(null); setUpdatePreview(null) }}
          onDelete={()=> deleteMeal(selectedSlot.meal)}
          onApply={()=> modifyMeal(selectedSlot.meal)}
          onRefresh={()=>{ fetchPlan() }}
          onReplaceChef={()=> { setSelectedSlot(null); onReplaceChef && onReplaceChef() }}
          onReplaceAlt={(alt)=> replaceWithAlternative(selectedSlot.meal, alt)}
        />
      )}
      <ToastOverlay toasts={toasts} />
    </div>
  )
}

function ToastOverlay({ toasts }){
  if (!toasts || toasts.length===0) return null
  return createPortal(
    <div className="toast-container" role="status" aria-live="polite">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.tone} ${t.closing?'closing':''}`}>{t.text}</div>
      ))}
    </div>,
    document.body
  )
}

function RightEditPanel({ open, slot, meal, weekStart, mealPlanId, chefMeals, prompt, setPrompt, promptHint, clearPromptHint, working, error, updatePreview, onClose, onDelete, onApply, onReplaceChef, onJumpToSlot, onRefresh, onReplaceAlt }){
  if (!open || !meal) return null
  const mealType = meal.type || meal.meal_type
  const mealTitle = meal.name || meal.meal?.name
  // If we have a preview of the update with a new name, reflect it in the header immediately
  const effectiveTitle = (!working && updatePreview && !updatePreview.none && (updatePreview.new_meal?.name || updatePreview.new_meal?.meal?.name)) || mealTitle
  const dayName = meal.day || meal.day_of_week
  const dayOptions = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
  const typeOptions = ['Breakfast','Lunch','Dinner']
  const [newDay, setNewDay] = useState(dayName)
  const [newType, setNewType] = useState(mealType)
  const [altMealId, setAltMealId] = useState('')
  const [alts, setAlts] = useState(null) // { meal_plan_meal_id, alternatives: [] }
  const [altsLoading, setAltsLoading] = useState(false)
  const [altsError, setAltsError] = useState(null)
  const [replacingAltId, setReplacingAltId] = useState(null)
  const [altSelectedId, setAltSelectedId] = useState('')
  const [instOpen, setInstOpen] = useState(false)
  const [instLoading, setInstLoading] = useState(false)
  const [instError, setInstError] = useState(null)
  const [instructions, setInstructions] = useState(null) // raw payload
  const [instFetchedAt, setInstFetchedAt] = useState(null) // Date
  const [instClamp, setInstClamp] = useState(true)
  const [instSteps, setInstSteps] = useState([]) // normalized steps [{step_number, description, duration_min}]
  const [chefQtyByEvent, setChefQtyByEvent] = useState({})
  const [chefNotesByEvent, setChefNotesByEvent] = useState({})
  const [chefOrderingId, setChefOrderingId] = useState(null)
  const [chefNotesOpen, setChefNotesOpen] = useState(()=> new Set())
  const [chefOptIndex, setChefOptIndex] = useState(0)

  function parseMinutes(text){
    try{
      if (!text) return null
      const m = String(text).match(/(\d+(?:\.\d+)?)\s*(?:min|minute)/i)
      if (m) return Math.round(parseFloat(m[1]))
    }catch{}
    return null
  }

  function normalizeSteps(raw){
    if (!raw) return []
    let obj = raw
    try{
      if (typeof raw === 'string'){ obj = JSON.parse(raw) }
    }catch{}
    // If wrapper has { steps: [...] }
    if (Array.isArray(obj?.steps)){
      return obj.steps.map((s, i)=> ({
        step_number: s.step_number ?? i+1,
        description: s.description || String(s),
        duration_min: parseMinutes(s.duration)
      }))
    }
    // If raw is already array
    if (Array.isArray(obj)){
      return obj.map((s, i)=> ({
        step_number: s.step_number ?? i+1,
        description: s.description || String(s),
        duration_min: parseMinutes(s.duration)
      }))
    }
    return []
  }

  async function generateAndFetchInstructions(mealPlanMealId, doGenerate=true){
    setInstLoading(true); setInstError(null); setInstClamp(true)
    try{
      if (doGenerate){
        try{ await api.post('/meals/api/generate_cooking_instructions/', { meal_plan_meal_ids: [mealPlanMealId] }) }catch{ /* continue to poll */ }
      }
      // Poll until steps are ready (up to ~30s)
      let got = null
      for (let attempt=0; attempt<30; attempt++){
        try{
          const resp = await api.get('/meals/api/fetch_instructions/', { params: { meal_plan_meal_ids: String(mealPlanMealId) } })
          const list = Array.isArray(resp?.data?.instructions) ? resp.data.instructions : []
          const match = list.find(x => (x.meal_plan_meal_id||x.id) === mealPlanMealId) || list[0] || null
          if (match){
            const steps = normalizeSteps(match.steps || match.instructions || match)
            if (steps && steps.length>0){
              got = match
              setInstructions(match)
              setInstSteps(steps)
              setInstFetchedAt(new Date())
              break
            }
          }
        }catch{}
        await new Promise(r => setTimeout(r, 1000))
      }
      // If timed out without steps, leave empty state; UI will continue to show spinner until timeout ends
      if (!got){ setInstructions(null); setInstSteps([]) }
    }catch(e){
      setInstError(e?.response?.data?.error || e?.message || 'Unable to load instructions')
    }finally{ setInstLoading(false) }
  }

  // Determine if a matching chef meal exists: same meal type and same date as this slot
  let canReplaceWithChef = false
  let chefOptions = []
  try{
    if (Array.isArray(chefMeals) && chefMeals.length){
      const typeNorm = String(mealType || '').toLowerCase()
      const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
      const offset = map[String(meal.day || meal.day_of_week)] ?? 0
      const slotDate = new Date(weekStart)
      slotDate.setDate(slotDate.getDate()+offset)
      const iso = fmtYMD(slotDate)
      const matches = chefMeals.some(cm => {
        const cmType = String(cm.meal_type || cm.type || '').toLowerCase()
        if (cmType && typeNorm && cmType !== typeNorm) return false
        if (cm.available_dates && typeof cm.available_dates === 'object') return Boolean(cm.available_dates[iso])
        if (cm.date){ try{ return String(cm.date).slice(0,10) === iso }catch{ return false } }
        return false
      })
      canReplaceWithChef = matches
      // Build explicit options list to display names/chefs
      chefOptions = (chefMeals||[]).flatMap(cm => {
        try{
          const cmType = String(cm.meal_type || cm.type || '').toLowerCase()
          if (cmType && typeNorm && cmType !== typeNorm) return []
          if (cm.available_dates && typeof cm.available_dates === 'object'){
            const info = cm.available_dates[iso]
            if (!info) return []
            const eventId = info?.event_id || info?.id || cm.event_id || cm.id
            if (!eventId) return []
            return [{ eventId, name: cm.name || cm.meal_name, chef: cm.chef_name || cm.chef, time: info?.event_time, price: info?.price }]
          }
          if (cm.date){
            try{
              const same = String(cm.date).slice(0,10) === iso
              if (!same) return []
              const eventId = cm.event_id || cm.id
              if (!eventId) return []
              return [{ eventId, name: cm.name || cm.meal_name, chef: cm.chef_name || cm.chef, time: (new Date(cm.date)).toLocaleTimeString?.() }]
            }catch{ return [] }
          }
        }catch{ return [] }
        return []
      })
    }
  }catch{}

  // Keep current index within bounds when options change
  useEffect(()=>{
    setChefOptIndex(i => {
      if (!Array.isArray(chefOptions) || chefOptions.length===0) return 0
      return Math.min(i, Math.max(0, chefOptions.length-1))
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chefMeals, weekStart, meal?.day, meal?.day_of_week, meal?.type, meal?.meal_type])

  function dayToDateString(weekStartDate, day){
    const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
    const offset = map[day] ?? 0
    const d = new Date(weekStartDate)
    d.setDate(d.getDate()+offset)
    const y = d.getFullYear(); const m = String(d.getMonth()+1).padStart(2,'0'); const dd = String(d.getDate()).padStart(2,'0')
    return `${y}-${m}-${dd}`
  }

  useEffect(()=>{
    // fetch alternatives when panel opens or target meal changes
    if (!open || !meal) return
    const load = async ()=>{
      setAltsLoading(true); setAltsError(null)
      try{
        const mpmId = meal.meal_plan_meal_id || meal.id
        const dateIso = dayToDateString(weekStart, meal.day || meal.day_of_week)
        // Existing meal edit: keep original alternatives endpoint
        const resp = await api.post('/meals/api/suggest_meal_alternatives/', {
          meal_plan_meal_ids: [mpmId],
          meal_dates: [dateIso]
        })
        const group = Array.isArray(resp?.data?.alternatives) ? (resp.data.alternatives[0] || null) : null
        setAlts(group)
      }catch(e){
        const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || 'Failed to load alternatives'
        setAltsError(msg)
      }finally{ setAltsLoading(false) }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, meal?.meal_plan_meal_id, meal?.id])

  useEffect(()=>{
    if (alts && Array.isArray(alts.alternatives) && alts.alternatives.length>0){
      setAltSelectedId(String(alts.alternatives[0].meal_id))
    } else {
      setAltSelectedId('')
    }
  }, [alts])

  return (
    <>
      <div className="right-panel-overlay" onClick={onClose} />
      <aside className="right-panel" role="dialog" aria-label={`Edit ${effectiveTitle}`}>
        <div className="right-panel-head">
          <div className="slot-title">Edit "{effectiveTitle}"</div>
          <button className="icon-btn" aria-label="Close" onClick={onClose}>✕</button>
        </div>
        <div className="right-panel-body">
          {instLoading && (
            <div className="updating-banner" style={{marginBottom:'.6rem'}}>
              <span className="spinner" /> Fetching instructions…
            </div>
          )}
          {/* Cooking instructions – compact row under title */}
          {(()=>{
            const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
            const offset = map[String(meal.day || meal.day_of_week)] ?? 0
            const dt = new Date(weekStart); dt.setDate(dt.getDate()+offset)
            const mealISO = fmtYMD(dt)
            const todayISO = fmtYMD(new Date())
            const isPast = mealISO < todayISO
            const ctaLabel = instOpen ? 'Hide' : 'View instructions'
            const disabled = instLoading || isPast
            return (
              <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'.35rem'}}>
                <div className="muted" title={isPast? 'Past meals may not have instructions available': undefined}>Cooking instructions {isPast && <span className="muted">(past)</span>}</div>
                <button
                  className="btn-link"
                  aria-expanded={instOpen}
                  onClick={async ()=>{
                    if (disabled) return
                    if (!instOpen){
                      setInstOpen(true)
                      const id = meal.meal_plan_meal_id || meal.id
                      // Show row-level updating state similar to Apply flow
                      setWorking(true); setReplacingId(id)
                      await generateAndFetchInstructions(id, !instructions)
                      setWorking(false); setReplacingId(null)
                    } else {
                      // Toggle close
                      setInstOpen(false)
                    }
                  }}
                  disabled={disabled}
                >{instLoading ? 'Loading…' : ctaLabel}</button>
              </div>
            )
          })()}
          {instOpen && (
            <div className="card" style={{marginBottom:'.5rem'}}>
              {instError && <div className="muted" style={{color:'#d9534f'}}>{instError}</div>}
              {!instructions && !instError && (
                <div>
                  <div className="muted" style={{marginBottom:'.4rem', display:'flex', alignItems:'center', gap:'.4rem'}}>
                    {instLoading && <span className="spinner" />}
                    <span>Not available yet.</span>
                  </div>
                  <button className="btn btn-primary" disabled={instLoading} onClick={async ()=>{
                    const id = meal.meal_plan_meal_id || meal.id
                    await generateAndFetchInstructions(id, true)
                  }}>{instLoading ? 'Generating…' : 'Generate instructions'}</button>
                </div>
              )}
              {!instLoading && !instError && instructions && (
                <div>
                  {Array.isArray(instSteps) && instSteps.length>0 ? (
                    <>
                      <ol style={{margin:'0 0 0 1.1rem', padding:0}}>
                        {(instClamp ? instSteps.slice(0,6) : instSteps).map((s, i)=> (
                          <li key={i} style={{margin:'.25rem 0'}}>
                            {s.description}
                            {typeof s.duration_min === 'number' && <span className="muted" style={{marginLeft:'.35rem'}}>({s.duration_min} min)</span>}
                          </li>
                        ))}
                      </ol>
                      <div className="actions-row" style={{justifyContent:'space-between', marginTop:'.4rem'}}>
                        <div className="muted">
                          {(()=>{
                            const total = instSteps.reduce((acc, s)=> acc + (typeof s.duration_min==='number'? s.duration_min:0), 0)
                            const when = instFetchedAt ? (()=>{ const ms = Date.now()-instFetchedAt.getTime(); const m = Math.round(ms/60000); return m<1?'just now':`${m} min${m>1?'s':''} ago` })() : ''
                            return `~${total||'—'} min • ${instSteps.length} step${instSteps.length>1?'s':''}${when?` • Generated ${when}`:''}`
                          })()}
                        </div>
                        <div style={{display:'flex', gap:'.4rem'}}>
                          {instSteps.length>6 && (
                            <button className="btn btn-link" onClick={()=> setInstClamp(v=>!v)}>{instClamp?'Show more':'Show less'}</button>
                          )}
                          <button className="btn btn-outline btn-sm" onClick={async ()=>{
                            try{
                              const text = instSteps.map(s=> s.description).join('\n')
                              await navigator.clipboard.writeText(text)
                            }catch{}
                          }}>Copy</button>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="muted" style={{display:'flex', alignItems:'center', gap:'.4rem'}}>
                      {instLoading && <span className="spinner" />}
                      <span>Preparing instructions…</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          {working && (
            <div className="updating-banner" style={{marginBottom:'.6rem'}}>
              <span className="spinner" /> Updating… Please wait
            </div>
          )}
          {!working && updatePreview && (
            <div className="preview card" style={{marginBottom:'.5rem'}}>
              <div style={{fontWeight:700, marginBottom:'.25rem'}}>Update submitted</div>
              <div className="muted">Changes will reflect in the table shortly.</div>
            </div>
          )}
          <div className="grid" style={{gap:'.5rem'}}>
            <div>
              <label className="label" htmlFor="edit-day">Day</label>
              <select id="edit-day" className="select" value={newDay} onChange={e=> { setNewDay(e.target.value); onJumpToSlot?.(e.target.value, newType) }}>
                {dayOptions.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="edit-type">Meal type</label>
              <select id="edit-type" className="select" value={newType} onChange={e=> { setNewType(e.target.value); onJumpToSlot?.(newDay, e.target.value) }}>
                {typeOptions.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div className="actions-row" style={{alignItems:'center', justifyContent:'space-between'}}>
            <div>
              {canReplaceWithChef ? (
                <span className="muted">Chef options available{chefOptions && chefOptions.length ? ` (${chefOptions.length})` : ''}</span>
              ) : (
                <span className="muted">No chef option for this slot.</span>
              )}
            </div>
            <div style={{display:'flex', gap:'.5rem', alignItems:'center'}}>
              {meal?.__canReview && (
                <button className="btn btn-outline btn-sm rate-btn" title="Rate this meal" aria-label="Rate this meal"
                  onClick={()=>{
                    const mealId = meal.meal?.id || meal.id
                    const mealName = meal.meal?.name || meal.name
                    // Close editor first so the review drawer is not covered
                    onClose?.()
                    // Open review drawer
                    const ev = new CustomEvent('open-review', { detail: { id: mealId, name: mealName } })
                    // slight delay to ensure panel unmounts before showing review
                    setTimeout(()=> window.dispatchEvent(ev), 0)
                  }}>
                  <span className="star-gold" aria-hidden>★</span> Rate
                </button>
              )}
              <button className="btn btn-danger" onClick={onDelete} disabled={working}>Delete</button>
            </div>
          </div>
          {chefOptions && chefOptions.length>0 && (
            <div className="card" style={{margin:'.5rem 0', padding:'.5rem', maxHeight:280, overflowY:'auto'}}>
              <div className="label" style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                <span>Chef options</span>
                <div style={{display:'flex', gap:'.35rem', alignItems:'center'}}>
                  <button className="btn btn-outline btn-sm" aria-label="Previous chef option" disabled={chefOptIndex<=0} onClick={()=> setChefOptIndex(i=>Math.max(0, i-1))}>←</button>
                  <div className="muted" style={{minWidth:60, textAlign:'center'}}>{chefOptIndex+1} / {chefOptions.length}</div>
                  <button className="btn btn-outline btn-sm" aria-label="Next chef option" disabled={chefOptIndex>=chefOptions.length-1} onClick={()=> setChefOptIndex(i=>Math.min(chefOptions.length-1, i+1))}>→</button>
                </div>
              </div>
              <div style={{margin:'.35rem 0'}}>
                <Listbox
                  options={chefOptions.map(o=> ({ key:o.eventId, value:String(o.eventId), label:o.name || 'Chef meal', subLabel:`${o.chef?`by ${o.chef}`:''}${o.time?` • ${o.time}`:''}${typeof o.price==='number'?` • $${o.price}`:''}` }))}
                  value={String((chefOptions[chefOptIndex]||{}).eventId||'')}
                  onChange={(val)=>{ const idx = chefOptions.findIndex(o => String(o.eventId)===String(val)); if (idx>=0) setChefOptIndex(idx) }}
                  placeholder="Select chef option…"
                  className="w-100"
                />
              </div>
              {(()=>{
                const opt = chefOptions[chefOptIndex]
                if (!opt) return null
                return (
                  <div className="chef-opt-row" style={{display:'grid', gridTemplateColumns:'1fr', gap:'.4rem'}}>
                    <div>
                      <div style={{fontWeight:700, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}} title={opt.name || 'Chef meal'}>{opt.name || 'Chef meal'}</div>
                      <div className="muted" style={{whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{opt.chef ? `by ${opt.chef}` : ''}{opt.time?` • ${opt.time}`:''}{typeof opt.price==='number'?` • $${opt.price}`:''}</div>
                    </div>
                    <div style={{display:'flex', flexWrap:'wrap', gap:'.35rem', alignItems:'center'}}>
                      <button className="btn btn-outline btn-sm" onClick={()=> onReplaceAlt?.({ is_chef_meal:true, meal_id: opt.eventId })} disabled={working}>Replace</button>
                    </div>
                  </div>
                )
              })()}
              <div style={{marginTop:'.5rem'}}>
                <button className="btn btn-outline btn-sm" style={{width:'100%'}} onClick={onReplaceChef} disabled={working}>Browse all chef meals →</button>
              </div>
            </div>
          )}
          <div style={{margin:'.25rem 0 .5rem'}}>
            <label className="label">Alternatives</label>
            {altsLoading && <div className="muted">Loading suggestions…</div>}
            {altsError && <div className="muted" style={{color:'#d9534f'}}>{altsError}</div>}
            {!altsLoading && !altsError && (!alts || !Array.isArray(alts.alternatives) || alts.alternatives.length===0) && (
              <div className="muted">No alternatives available for this slot.</div>
            )}
            {!altsLoading && !altsError && Array.isArray(alts?.alternatives) && alts.alternatives.length>0 && (
              <div>
                <select className="select" value={altSelectedId} onChange={e=> setAltSelectedId(e.target.value)}>
                  {alts.alternatives.map(a => {
                    const label = a.is_chef_meal
                      ? `${a.chef ? `Chef ${a.chef}` : 'Chef'} — ${a.name}${a.start_date ? ` (${new Date(a.start_date).toLocaleDateString()})` : ''}`
                      : `${a.name}`
                    return <option key={a.meal_id} value={String(a.meal_id)}>{label}</option>
                  })}
            </select>
                <div className="actions-row" style={{marginTop:'.4rem'}}>
                  <button className="btn btn-primary" disabled={!altSelectedId || replacingAltId===Number(altSelectedId)} onClick={async ()=>{
                    const chosen = (alts?.alternatives||[]).find(x => String(x.meal_id) === String(altSelectedId))
                    if (!chosen) return
                    setReplacingAltId(chosen.meal_id)
                    await onReplaceAlt?.(chosen)
                    setReplacingAltId(null)
                  }}>{replacingAltId===Number(altSelectedId)?'Replacing…':'Replace'}</button>
                  <button className="btn btn-link" onClick={()=>{
                    setAltsError(null); setAltsLoading(true)
                    const mpmId = meal.meal_plan_meal_id || meal.id
                    const dateIso = dayToDateString(weekStart, meal.day || meal.day_of_week)
                    api.post('/meals/api/suggest_meal_alternatives/', { meal_plan_meal_ids:[mpmId], meal_dates:[dateIso] })
                      .then(r=> setAlts(Array.isArray(r?.data?.alternatives) ? r.data.alternatives[0] : null))
                      .catch(e=> setAltsError(e?.response?.data?.error || e?.message || 'Failed to refresh suggestions'))
                      .finally(()=> setAltsLoading(false))
                  }}>Refresh</button>
                </div>
                <div className="muted" style={{marginTop:'.25rem'}}>Chef meals are prioritized based on your preferences and location.</div>
              </div>
            )}
          </div>
          <div className="refactor">
            <label className="label" htmlFor="edit-prompt">Change request</label>
            <textarea id="edit-prompt" className={`textarea ${promptHint?'invalid':''}`} rows={4} placeholder={`Refactor this ${mealType?.toLowerCase()}…`} value={prompt} onChange={e=> { setPrompt(e.target.value); if (promptHint) clearPromptHint() }} />
            {promptHint && <div className="field-hint">Please provide a brief instruction (e.g., "make it low-carb")</div>}
            <div className="actions-row">
              <button className="btn btn-primary" onClick={(e)=>{ e.preventDefault(); e.stopPropagation(); onApply?.() }} disabled={working}>Apply changes</button>
              <button className="btn btn-outline" onClick={()=> setPrompt('')} disabled={working || !prompt}>Clear</button>
            </div>
          </div>
          {error && <div className="muted" role="alert" style={{color:'#d9534f', marginTop:'.4rem'}}>{error}</div>}
        </div>
      </aside>
    </>
  )
}

function MealSlotPopover({ slot, meal, chefMeals, weekStart, prompt, setPrompt, working, error, updatePreview, clearPreview, onClose, onDelete, onModify, onReplaceChef }){
  const width = 340
  const popRef = useRef(null)
  const [position, setPosition] = useState(()=>{
    if (!slot?.rect) return {}
    const left = Math.max(16, Math.min(slot.rect.left, window.scrollX + window.innerWidth - width - 16))
    const top = slot.rect.bottom + 8
    return { left, top, width }
  })
  // After render, measure and adjust to keep within viewport; flip above if needed
  useEffect(()=>{
    if (!slot?.rect || !popRef.current) return
    const margin = 12
    const maxLeft = window.scrollX + window.innerWidth - width - margin
    const left = Math.max(margin, Math.min(slot.rect.left, maxLeft))
    let top = slot.rect.bottom + 8
    const rect = popRef.current.getBoundingClientRect()
    const bottom = top + rect.height
    const viewportBottom = window.scrollY + window.innerHeight - margin
    if (bottom > viewportBottom){
      // Try flipping above the anchor
      top = slot.rect.top - rect.height - 8
      if (top < window.scrollY + margin){
        top = window.scrollY + margin
      }
    }
    setPosition({ left, top, width })
  }, [slot, prompt, updatePreview])
  useEffect(()=>{
    const onResize = ()=>{
      if (!slot?.rect) return
      const margin = 12
      const maxLeft = window.scrollX + window.innerWidth - width - margin
      const left = Math.max(margin, Math.min(slot.rect.left, maxLeft))
      setPosition(p => ({ ...p, left }))
    }
    window.addEventListener('resize', onResize)
    return ()=> window.removeEventListener('resize', onResize)
  }, [slot])
  const mealType = meal.type || meal.meal_type
  const mealTitle = meal.name || meal.meal?.name
  // Determine if a matching chef meal exists: same meal type and same date as this slot
  // We compute the slot date using weekStart + day name on the meal.
  // TODO: If backend supplies exact ISO date per meal, read that directly instead of recomputing.
  let canReplaceWithChef = false
  try{
    if (Array.isArray(chefMeals) && chefMeals.length){
      const typeNorm = String(mealType || '').toLowerCase()
      const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
      const offset = map[String(meal.day || meal.day_of_week)] ?? 0
      const slotDate = new Date(weekStart)
      slotDate.setDate(slotDate.getDate()+offset)
      const iso = fmtYMD(slotDate)
      canReplaceWithChef = chefMeals.some(cm => {
        const cmType = String(cm.meal_type || cm.type || '').toLowerCase()
        if (cmType && typeNorm && cmType !== typeNorm) return false
        // Check available_dates dict first
        if (cm.available_dates && typeof cm.available_dates === 'object'){
          return Boolean(cm.available_dates[iso])
        }
        // Fallback: if a single date is present, compare
        if (cm.date){
          try{ return String(cm.date).slice(0,10) === iso }catch{ return false }
        }
        return false
      })
    }
  }catch{}
  // Reflect new name immediately if update preview is present
  const effectiveTitle = (!working && updatePreview && !updatePreview.none && (updatePreview.new_meal?.name || updatePreview.new_meal?.meal?.name)) || mealTitle
  return (
    <div ref={popRef} className="slot-popover" style={position} role="dialog" aria-label={`Edit ${effectiveTitle}`}>
      <div className="slot-popover-head">
        <div className="slot-title">Edit "{effectiveTitle}"</div>
        <button className="icon-btn" aria-label="Close" onClick={onClose}>✕</button>
      </div>
      <div className="slot-popover-body">
        {working && (
          <div className="muted" style={{marginBottom:'.4rem'}}>Updating… Please wait</div>
        )}
        {!working && updatePreview && (
          <div className="preview card" style={{marginBottom:'.5rem'}}>
            {updatePreview.none ? (
              <div className="muted">No changes were needed.</div>
            ) : (
              <div>
                <div style={{fontWeight:700, marginBottom:'.25rem'}}>Updated</div>
                <div style={{display:'grid', gap:'.25rem'}}>
                  <div><span className="muted">Old:</span> {updatePreview.old_meal?.name || '—'}</div>
                  <div><span className="muted">New:</span> {updatePreview.new_meal?.name || '—'}</div>
                  {/* If backend includes additional details like used_pantry_items, show them */}
                  {Array.isArray(updatePreview.new_meal?.used_pantry_items) && updatePreview.new_meal.used_pantry_items.length > 0 && (
                    <div className="muted">Pantry used: {updatePreview.new_meal.used_pantry_items.join(', ')}</div>
                  )}
                </div>
              </div>
            )}
            <div style={{marginTop:'.4rem'}}>
              <button className="btn btn-outline" onClick={clearPreview}>Close</button>
            </div>
          </div>
        )}
        <div className="actions-row">
          {canReplaceWithChef ? (
            <button className="btn btn-outline" onClick={onReplaceChef} disabled={working}>Replace with Chef</button>
          ) : (
            <span className="muted" title="Chef meal not available for this slot">{/* TODO: enable when same-date chef meals are available */}</span>
          )}
          <button className="btn btn-danger" onClick={onDelete} disabled={working}>Delete</button>
        </div>
        <div className="refactor">
          <textarea className="textarea" rows={3} placeholder={`Refactor this ${mealType?.toLowerCase()}…`} value={prompt} onChange={e=> setPrompt(e.target.value)} />
          <div className="actions-row">
            <button className="btn btn-primary" onClick={onModify} disabled={working || !prompt.trim()}>Apply changes</button>
            <button className="btn btn-outline" onClick={()=> setPrompt('')} disabled={working || !prompt}>Clear</button>
          </div>
        </div>
        {error && <div className="muted" role="alert" style={{color:'#d9534f', marginTop:'.4rem'}}>{error}</div>}
      </div>
    </div>
  )
}

function ChefMeals({ chefMeals, weekStart, onChange, onNotify }){
  const [placing, setPlacing] = useState(false)
  const [selected, setSelected] = useState(()=> new Set()) // eventIds
  const [qtyByEvent, setQtyByEvent] = useState({})
  const [notesByEvent, setNotesByEvent] = useState({})
  const [orderingAll, setOrderingAll] = useState(false)
  const [createdOrderIds, setCreatedOrderIds] = useState([])
  const [paymentLinks, setPaymentLinks] = useState([])
  const [initiatingPayment, setInitiatingPayment] = useState(false)
  const { user } = useAuth()

  // Paging + filters for large catalogs
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(12)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [typeFilter, setTypeFilter] = useState('') // Breakfast|Lunch|Dinner|''
  const [dateFilter, setDateFilter] = useState('') // YYYY-MM-DD
  const [query, setQuery] = useState('')
  const [onlyCapacity, setOnlyCapacity] = useState(false)
  const [pageMeals, setPageMeals] = useState([]) // meals from backend for this page
  const [focusSlotFilter, setFocusSlotFilter] = useState(null)

  const toggleSelect = (ev)=>{
    try{
      const eventId = ev.eventId
      if (!eventId) return
      setSelected(prev => {
        const next = new Set(prev); if (next.has(eventId)) next.delete(eventId); else next.add(eventId); return next
      })
      setQtyByEvent(prev => ({ ...prev, [eventId]: Number(prev[eventId]||1) }))
    }catch{}
  }

  const orderSelected = async ()=>{
    if (!selected || selected.size===0) return
    setOrderingAll(true)
    let ok = 0, fail = 0
    const created = []
    const placeOrder = async (eventId, qty, notes)=>{
      // Route through shared axios api (auth, proxy, user_id injection)
      const payload = { meal_event: eventId, quantity: qty, special_requests: notes }
      try{ if (user?.id != null && payload.user_id == null) payload.user_id = user.id }catch{}
      const idem = newIdempotencyKey && newIdempotencyKey()
      const disableIdem = String(import.meta.env.VITE_DISABLE_IDEMPOTENCY || 'false') === 'true'
      const headers = {}
      if (!disableIdem && idem){ headers['Idempotency-Key'] = idem; headers['idempotency-key'] = idem }
      try{
        const resp = await api.post('/meals/api/chef-meal-orders/', payload, { headers })
        const data = resp?.data
        const chefOrderId = data?.id || data?.chef_meal_order?.id || data?.data?.id || null
        const orderId = data?.order || data?.order_id || (data?.order && data.order.id) || null
        return { chefOrderId, orderId }
      }catch(e){
        const status = e?.response?.status
        const msg = `Order failed ${status||''}`.trim()
        try{ onNotify && onNotify(msg, 'error') }catch{}
        throw e
      }
    }
    for (const eventId of selected){
      try{
        const qty = Math.max(1, Number(qtyByEvent[eventId]||1))
        const notes = notesByEvent[eventId] || ''
        const res = await placeOrder(eventId, qty, notes)
        if (res && (res.chefOrderId != null || res.orderId != null)) created.push(res)
        ok++
      }catch{ fail++ }
    }
    if (ok>0) try{ onNotify && onNotify(`${ok} order${ok>1?'s':''} placed${fail>0?` (${fail} failed)`:''}.`, fail>0?'error':'success') }catch{}
    setCreatedOrderIds(created.map(x => x.chefOrderId).filter(Boolean))
    setOrderingAll(false)
    if (ok>0){
      setSelected(new Set()); setQtyByEvent({}); setNotesByEvent({})
      onChange && onChange()
      // Kick off payment initiation for the first created order; if multiple, gather links
      if (created && created.length){
        try{
          setInitiatingPayment(true)
          const links = []
          const parentIds = Array.from(new Set(created.map(x => x.orderId).filter(Boolean)))
          for (const parentId of parentIds){
            const link = await initiatePaymentForOrder(parentId)
            if (link) links.push({ orderId: parentId, url: link })
          }
          setPaymentLinks(links)
          if (links.length){
            // Redirect to first link
            window.location.href = links[0].url
          } else {
            try{ onNotify && onNotify('Payment link unavailable. Please try again from your Orders.', 'error') }catch{}
          }
        }catch(e){ try{ onNotify && onNotify('Payment initiation failed. Please try again.', 'error') }catch{} }
        finally{ setInitiatingPayment(false) }
      }
    }
  }

  // Start Stripe Checkout for a pending order and return session_url
  const initiatePaymentForOrder = async (orderId)=>{
    try{
      // Pre-check to avoid duplicate charges and reuse open sessions
      let pre
      let sid = null
      try{ sid = localStorage.getItem('lastCheckoutSessionId') || null }catch{}
      try{ pre = await api.get(`/meals/api/order-payment-status/${orderId}/`, { params: sid ? { session_id: sid } : {} }) }catch{}
      const p = pre?.data || {}
      if (p?.is_paid){ try{ onNotify && onNotify('Order already paid.', 'success') }catch{}; onOrdersReload?.(); return null }
      if (p?.session_status === 'open' && p?.session_url){
        try{
          localStorage.setItem('lastPaymentOrderId', String(orderId))
          if (p?.session_id) localStorage.setItem('lastCheckoutSessionId', String(p.session_id))
        }catch{}
        window.location.href = p.session_url
        return p.session_url
      }
      const resp = await api.post(`/meals/api/process-chef-meal-payment/${orderId}/`)
      const data = resp?.data || {}
      const url = data?.session_url || (data?.data && data.data.session_url) || null
      const newSid = data?.session_id || (data?.data && data.data.session_id) || null
      try{ if (newSid) localStorage.setItem('lastCheckoutSessionId', String(newSid)) }catch{}
      if (url){
        try{ localStorage.setItem('lastPaymentOrderId', String(orderId)) }catch{}
        window.location.href = url
        return url
      }
      return null
    }catch{ return null }
  }

  // Optionally prefilter by focusSlot when user navigated from a placeholder
  // Fetch paged meals when tab is open
  useEffect(()=>{
    let cancelled = false
    const fetchPage = async ()=>{
      setLoading(true); setError(null)
      try{
        const params = {}
        if (dateFilter){ params.date = dateFilter } else { params.week_start_date = fmtYMD(weekStart) }
        if (typeFilter) params.meal_type = typeFilter
        params.page = page
        params.page_size = pageSize
        
        const resp = await api.get('/meals/api/chef-meals-by-postal-code/', { params })
        const data = resp?.data
        const meals = Array.isArray(data?.data?.meals) ? data.data.meals : (Array.isArray(data?.meals) ? data.meals : (Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])))
        if (cancelled) return
        setPageMeals(Array.isArray(meals)? meals : [])
        const meta = data?.data || {}
        const tc = Number(meta.total_count || data?.total_count || meals?.length || 0)
        const ps = Number(meta.page_size || data?.page_size || pageSize)
        const cp = Number(meta.current_page || data?.current_page || page)
        const tp = Number(meta.total_pages || data?.total_pages || Math.max(1, Math.ceil(tc/ps)))
        setTotalCount(tc); setPageSize(ps); setTotalPages(tp); if (cp!==page) setPage(cp)
        try{
          const counts = (Array.isArray(meals)? meals : []).map(m => ({ id:m?.id, name:m?.name||m?.meal_name, days: m?.available_days_count || (m?.available_dates ? Object.keys(m.available_dates).length : 0) }))
          
        }catch{}
      }catch(e){ if (!cancelled){ setError(e?.response?.data?.error || 'Failed to load chef meals') } }
      finally{ if (!cancelled) setLoading(false) }
    }
    fetchPage()
    return ()=>{ cancelled = true }
  }, [weekStart, page, pageSize, typeFilter, dateFilter])

  // Capture an optional focus-from-slot signal once, then clear the global to avoid sticky filtering
  useEffect(()=>{
    try{
      const ev = window.__focusMealSlot
      if (ev && typeof ev === 'object'){
        setFocusSlotFilter(ev)
      }
      // Clear so it doesn't persist across renders or navigations
      window.__focusMealSlot = null
    }catch{}
  }, [])

  // Flatten meals so each available date becomes its own event row
  const events = useMemo(()=>{
    const base = Array.isArray(pageMeals) && pageMeals.length>0 ? pageMeals : (chefMeals||[])
    return base.flatMap(cm => {
      const rows = []
      if (cm?.available_dates && typeof cm.available_dates === 'object'){
        Object.entries(cm.available_dates).forEach(([iso, info]) => {
          rows.push({
            eventId: info?.event_id || cm.event_id || cm.id,
            dateIso: iso,
            time: info?.event_time,
            price: info?.price || cm.price,
            name: cm.name || cm.meal_name,
            chef: cm.chef_name || cm.chef,
            description: cm.description || '',
            meal_type: info?.meal_type || cm.meal_type || cm.type,
            __base: cm
          })
        })
      } else if (Array.isArray(cm?.chef_meal_events) && cm.chef_meal_events.length){
        cm.chef_meal_events.forEach(ev => {
          rows.push({
            eventId: ev.id,
            dateIso: String(ev.event_date||'').slice(0,10),
            time: ev.event_time,
            price: ev.current_price || cm.price,
            name: cm.name || cm.meal_name,
            chef: cm.chef_name || cm.chef,
            description: cm.description || '',
            meal_type: ev?.meal_type || cm.meal_type || cm.type,
            __base: cm
          })
        })
      } else if (cm.date){
        rows.push({
          eventId: cm.event_id || cm.id,
          dateIso: String(cm.date).slice(0,10),
          time: (new Date(cm.date)).toLocaleTimeString?.(),
          price: cm.price,
          name: cm.name || cm.meal_name,
          chef: cm.chef_name || cm.chef,
          description: cm.description || '',
          meal_type: cm.meal_type || cm.type,
          __base: cm
        })
      }
      return rows
    })
  }, [pageMeals, chefMeals])
  .filter(ev => {
    const q = query.trim().toLowerCase()
    if (!q) return true
    const hay = `${ev.name||''} ${ev.chef||''}`.toLowerCase()
    return hay.includes(q)
  })
  .filter(ev => {
    if (!onlyCapacity) return true
    const base = ev.__base
    if (base?.available_dates && base.available_dates[ev.dateIso]){
      const info = base.available_dates[ev.dateIso]
      const left = Number(info.max_orders||0) - Number(info.orders_count||0)
      return left > 0
    }
    return true
  })
  .filter(ev => {
    // Apply client-side meal type filtering as a safeguard
    if (!typeFilter) return true
    const eventType = String(ev.meal_type || ev.__base?.meal_type || ev.__base?.type || '').toLowerCase()
    return eventType === String(typeFilter).toLowerCase()
  })

  let filtered = events
  try{
    const event = focusSlotFilter
    // Apply focus filter only if provided and no explicit date filter is set
    if (!dateFilter && event && typeof event === 'object'){
      const typeNorm = String(event.type||'').toLowerCase()
      const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
      const offset = map[String(event.day)] ?? null
      if (offset != null){
        const d = new Date(weekStart); d.setDate(d.getDate()+offset)
        const iso = fmtYMD(d)
        filtered = (events||[]).filter(ev => {
          const cmType = String(ev.meal_type || '').toLowerCase()
          if (cmType && typeNorm && cmType !== typeNorm) return false
          return ev.dateIso === iso
        })
      }
    }
  }catch{}

  // Controls toolbar
  const toolbar = (
    <div className="card" style={{display:'flex', flexWrap:'wrap', gap:'.5rem', alignItems:'center', justifyContent:'space-between', marginBottom:'.5rem'}}>
      <div style={{display:'flex', gap:'.5rem', flexWrap:'wrap', alignItems:'center'}}>
        <select className="select" value={typeFilter} onChange={e=> { setTypeFilter(e.target.value); setPage(1) }}>
          <option value="">All types</option>
          <option value="Breakfast">Breakfast</option>
          <option value="Lunch">Lunch</option>
          <option value="Dinner">Dinner</option>
        </select>
        <input className="input" type="date" value={dateFilter} onChange={e=> { setDateFilter(e.target.value); setPage(1) }} />
        <input className="input" type="search" placeholder="Search meals or chefs…" value={query} onChange={e=> setQuery(e.target.value)} />
        <label style={{display:'inline-flex', alignItems:'center', gap:'.35rem'}}>
          <input type="checkbox" checked={onlyCapacity} onChange={e=> setOnlyCapacity(e.target.checked)} />
          <span className="muted">Only show meals I can order</span>
        </label>
        {(!dateFilter && focusSlotFilter) && (
          <span className="badge" style={{display:'inline-flex', alignItems:'center', gap:'.35rem'}}>
            Focus: {String(focusSlotFilter.day)} {String(focusSlotFilter.type)}
            <button className="icon-btn" aria-label="Clear focus" onClick={()=> setFocusSlotFilter(null)}>✕</button>
          </span>
        )}
      </div>
      <div style={{display:'flex', gap:'.35rem', alignItems:'center'}}>
        <button className="btn btn-outline btn-sm" onClick={()=> { setTypeFilter(''); setDateFilter(''); setQuery(''); setOnlyCapacity(false); setFocusSlotFilter(null); setPage(1) }}>Clear filters</button>
        <button className="btn btn-outline btn-sm" disabled={page<=1 || loading} onClick={()=> setPage(p=> Math.max(1, p-1))}>← Prev</button>
        <div className="muted" style={{minWidth:80, textAlign:'center'}}>{page} / {totalPages}</div>
        <button className="btn btn-outline btn-sm" disabled={page>=totalPages || loading} onClick={()=> setPage(p=> Math.min(totalPages, p+1))}>Next →</button>
      </div>
    </div>
  )

  if (!filtered || filtered.length===0) return (
    <div>
      {toolbar}
      <div className="card">No suitable meals for this slot. Adjust filters or try different date/type.</div>
    </div>
  )
  return (
    <div>
      {toolbar}
      <div className="grid grid-2">
        {filtered.map((ev)=> {
          const eventId = ev.eventId
          const sel = eventId ? selected.has(eventId) : false
          return (
            <div key={`${ev.eventId}-${ev.dateIso}`} className="card">
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:'.5rem'}}>
                <h3 style={{margin:0, flex:'1 1 auto', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>
                  {ev.name}
                  <button
                    className="btn-link"
                    style={{marginLeft:'.5rem'}}
                    onClick={(e)=>{
                      e.stopPropagation()
                      const mealName = ev.name || 'this meal'
                      const q = `Can you tell me more about ${mealName}?`
                      const url = `/chat?topic=${encodeURIComponent(mealName)}&meal_id=${encodeURIComponent(ev.eventId||'')}&q=${encodeURIComponent(q)}`
                      window.open(url,'_self')
                    }}
                    aria-label={`Ask about ${ev.name}`}
                    title={`Ask about ${ev.name}`}
                  >Ask</button>
                </h3>
                <label style={{display:'inline-flex', alignItems:'center', gap:'.35rem'}}>
                  <input type="checkbox" checked={sel} onChange={()=> toggleSelect(ev)} disabled={!eventId} />
                  <span className="muted">Select</span>
                </label>
              </div>
              <p className="muted">{ev.description || ''}</p>
              <p><strong>Chef:</strong> {ev.chef}</p>
              <p><strong>Date:</strong> {new Date(ev.dateIso+'T00:00:00').toLocaleDateString()} {ev.time?`• ${ev.time}`:''}</p>
              {ev.price && <p><strong>Price:</strong> ${ev.price}</p>}
              {sel && eventId && (
                <div style={{display:'flex', flexWrap:'wrap', gap:'.35rem', alignItems:'center'}}>
                  <label className="muted" style={{fontSize:'.85rem'}}>Qty</label>
                  <input type="number" className="input" min={1} style={{width:72, padding:'.3rem .4rem'}} value={Number(qtyByEvent[eventId]||1)} onChange={e=> setQtyByEvent(prev=>({ ...prev, [eventId]: Math.max(1, parseInt(e.target.value||'1',10)) }))} />
                  <input type="text" className="input" placeholder="Notes (optional)" value={notesByEvent[eventId]||''} onChange={e=> setNotesByEvent(prev=>({ ...prev, [eventId]: e.target.value }))} />
                </div>
              )}
            </div>
          )
        })}
      </div>
      {selected && selected.size>0 && (
        <div className="card" style={{position:'sticky', bottom:0, zIndex:5}}>
          <div style={{display:'flex', flexWrap:'wrap', alignItems:'center', justifyContent:'space-between', gap:'.5rem'}}>
            <div className="muted">{selected.size} selected</div>
            <div style={{display:'flex', gap:'.5rem'}}>
              <button className="btn btn-outline" onClick={()=> { setSelected(new Set()); setQtyByEvent({}); setNotesByEvent({}) }} disabled={orderingAll}>Clear</button>
              <button className="btn btn-primary" onClick={orderSelected} disabled={orderingAll}>{orderingAll?'Placing…':'Order selected'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function AddPantryDrawer({ open, onClose, onSuccess, onError }){
  if (!open) return null
  const [itemName, setItemName] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [weightPerUnit, setWeightPerUnit] = useState('')
  const [weightUnit, setWeightUnit] = useState('')
  const [expirationDate, setExpirationDate] = useState(() => fmtYMD(new Date()))
  const [itemType, setItemType] = useState('Canned')
  const [notes, setNotes] = useState('')
  const [tags, setTags] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showTips, setShowTips] = useState(false)

  const reset = ()=>{
    setItemName(''); setQuantity(1); setWeightPerUnit(''); setWeightUnit('');
    setExpirationDate(fmtYMD(new Date())); setItemType('Canned'); setNotes(''); setTags('')
  }

  const submit = async ()=>{
    if (!itemName.trim() || !quantity || quantity < 1){
      onError?.('Please provide item name and quantity.')
      return
    }
    setSubmitting(true)
    try{
      const payload = {
        item_name: itemName.trim(),
        quantity: Number(quantity),
        expiration_date: expirationDate || null,
        item_type: itemType || 'Canned',
        notes: notes || '',
        tags: tags.split(',').map(t => t.trim()).filter(Boolean)
      }
      if (weightPerUnit && Number(weightPerUnit) > 0){
        payload.weight_per_unit = Number(weightPerUnit)
        if (weightUnit) payload.weight_unit = weightUnit
      }
      const resp = await api.post('/meals/api/pantry-items/', payload)
      if (resp.status === 201 || resp.status === 200){
        onSuccess?.(payload.item_name)
        reset()
      } else {
        const msg = resp?.data?.error || resp?.data?.detail || 'Failed to add pantry item.'
        onError?.(msg)
      }
    }catch(e){
      const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message
      onError?.(msg)
    }finally{
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="right-panel-overlay" onClick={onClose} />
      <aside className="right-panel" role="dialog" aria-label="Add pantry item">
        <div className="right-panel-head">
          <div className="slot-title">Add Pantry Item</div>
          <button className="icon-btn" aria-label="Close" onClick={onClose}>✕</button>
        </div>
        <div className="right-panel-body">
          {/* Purpose banner */}
          <div className="callout" role="note" style={{marginBottom:'.6rem'}}>
            <div className="icon" aria-hidden>i</div>
            <div>
              <div style={{fontWeight:700}}>Why add pantry items?</div>
              <div className="muted">We use what you already have to tailor meals, reduce waste, and surface items nearing expiration.</div>
            </div>
          </div>
          <button className="btn btn-link" onClick={()=> setShowTips(v=>!v)} aria-expanded={showTips} aria-controls="pi-tips">{showTips ? 'Hide' : 'How to use this'}</button>
          {showTips && (
            <div id="pi-tips" className="card" style={{margin:'.4rem 0', padding:'.6rem'}}>
              <ul style={{margin:'0 0 .25rem 1rem'}}>
                <li>Use tags for dietary flags (e.g., <em>gluten-free, vegan</em>).</li>
                <li>Set an expiration date to get "use soon" suggestions.</li>
                <li>Weight per unit helps with recipe scaling (e.g., 15 oz cans).</li>
              </ul>
              <div className="muted">You can add items quickly here while planning meals.</div>
            </div>
          )}
          <div className="grid" style={{gap:'.6rem'}}>
            <div>
              <label htmlFor="pi-name" className="label">Item Name</label>
              <input id="pi-name" className="input" type="text" value={itemName} onChange={e=> setItemName(e.target.value)} placeholder="Black beans" />
            </div>
            <div className="grid" style={{gridTemplateColumns:'1fr 1fr', gap:'.5rem'}}>
              <div>
                <label htmlFor="pi-qty" className="label">Quantity</label>
                <input id="pi-qty" className="input" type="number" min={1} value={quantity} onChange={e=> setQuantity(parseInt(e.target.value||'1',10))} />
              </div>
              <div>
                <label htmlFor="pi-date" className="label">Expiration Date</label>
                <input id="pi-date" className="input" type="date" value={expirationDate} onChange={e=> setExpirationDate(e.target.value)} />
              </div>
            </div>
            <div className="grid" style={{gridTemplateColumns:'1fr 1fr', gap:'.5rem'}}>
              <div>
                <label htmlFor="pi-wpu" className="label">Weight Per Unit</label>
                <input id="pi-wpu" className="input" type="number" step="0.1" min={0} value={weightPerUnit} onChange={e=> setWeightPerUnit(e.target.value)} placeholder="e.g., 15.5" />
              </div>
              <div>
                <label htmlFor="pi-unit" className="label">Weight Unit</label>
                <select id="pi-unit" className="select" value={weightUnit} onChange={e=> setWeightUnit(e.target.value)}>
                  <option value="">(none)</option>
                  <option value="oz">oz</option>
                  <option value="lb">lb</option>
                  <option value="g">g</option>
                  <option value="kg">kg</option>
                </select>
              </div>
            </div>
            <div className="grid" style={{gridTemplateColumns:'1fr 1fr', gap:'.5rem'}}>
              <div>
                <label htmlFor="pi-type" className="label">Item Type</label>
                <select id="pi-type" className="select" value={itemType} onChange={e=> setItemType(e.target.value)}>
                  <option value="Canned">Canned</option>
                  <option value="Dry">Dry</option>
                </select>
              </div>
              <div>
                <label htmlFor="pi-tags" className="label">Tags</label>
                <input id="pi-tags" className="input" type="text" value={tags} onChange={e=> setTags(e.target.value)} placeholder="Gluten-Free, High-Protein" />
              </div>
            </div>
            <div>
              <label htmlFor="pi-notes" className="label">Notes</label>
              <textarea id="pi-notes" className="textarea" rows={3} value={notes} onChange={e=> setNotes(e.target.value)} placeholder="Any special notes…" />
            </div>
            <div className="actions-row" style={{marginTop:'.25rem'}}>
              <button className="btn btn-primary" onClick={submit} disabled={submitting}>{submitting? 'Adding…' : 'Add Item'}</button>
              <button className="btn btn-outline" onClick={reset} disabled={submitting}>Reset</button>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}

function QuickHealthDrawer({ open, onClose, onSuccess, onError }){
  if (!open) return null
  const [date, setDate] = useState(() => fmtYMD(new Date()))
  const [weight, setWeight] = useState('')
  const [unit, setUnit] = useState('kg')
  const [mood, setMood] = useState('Neutral')
  const [energy, setEnergy] = useState(5)
  const [saving, setSaving] = useState(false)
  const moods = ['Happy','Sad','Stressed','Relaxed','Energetic','Tired','Neutral']

  const toKg = (w)=>{
    const n = Number(w)
    if (!n || Number.isNaN(n)) return null
    return unit === 'kg' ? n : Math.round((n/2.20462)*100)/100
  }

  const save = async ()=>{
    setSaving(true)
    try{
      const payload = { date_recorded: date, mood, energy_level: Number(energy) }
      const kg = toKg(weight)
      if (kg != null) payload.weight = kg
      const resp = await api.post('/customer_dashboard/api/health_metrics/', payload)
      if (resp.status === 200){ onSuccess?.() }
      else { onError?.('Failed to save metrics') }
    }catch(e){ onError?.(e?.response?.data?.error || e?.message) } finally { setSaving(false) }
  }

  return (
    <>
      <div className="right-panel-overlay" onClick={onClose} />
      <aside className="right-panel" role="dialog" aria-label="Quick log health">
        <div className="right-panel-head">
          <div className="slot-title">Quick Log Health</div>
          <button className="icon-btn" aria-label="Close" onClick={onClose}>✕</button>
        </div>
        <div className="right-panel-body">
          <div className="grid" style={{gap:'.6rem'}}>
            <div>
              <label className="label" htmlFor="qh-date">Date</label>
              <input id="qh-date" className="input" type="date" value={date} onChange={e=> setDate(e.target.value)} />
            </div>
            <div className="grid" style={{gridTemplateColumns:'1fr 1fr', gap:'.5rem'}}>
              <div>
                <label className="label" htmlFor="qh-weight">Weight</label>
                <input id="qh-weight" className="input" type="number" placeholder="e.g., 72" value={weight} onChange={e=> setWeight(e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="qh-unit">Unit</label>
                <select id="qh-unit" className="select" value={unit} onChange={e=> setUnit(e.target.value)}>
                  <option value="kg">kg</option>
                  <option value="lbs">lbs</option>
                </select>
              </div>
            </div>
            <div>
              <label className="label" htmlFor="qh-mood">Mood</label>
              <select id="qh-mood" className="select" value={mood} onChange={e=> setMood(e.target.value)}>
                {moods.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="qh-energy">Energy</label>
              <input id="qh-energy" className="input" type="number" min={1} max={10} value={energy} onChange={e=> setEnergy(e.target.value)} />
            </div>
            <div className="actions-row">
              <button className="btn btn-primary" onClick={save} disabled={saving}>{saving?'Saving…':'Save'}</button>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
