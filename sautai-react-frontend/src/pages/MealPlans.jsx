import React, { useEffect, useState, useMemo, useRef } from 'react'
import { api, newIdempotencyKey } from '../api'
import { useAuth } from '../context/AuthContext.jsx'

function startOfWeek(d){
  const x = new Date(d); const day = x.getDay() // 0 Sun
  const diff = (day === 0 ? -6 : 1) - day // Monday as start
  x.setDate(x.getDate()+diff)
  x.setHours(0,0,0,0)
  return x
}
function fmtISO(d){ return d.toISOString().slice(0,10) }
function fmtYMD(d){
  const y = d.getFullYear()
  const m = String(d.getMonth()+1).padStart(2,'0')
  const day = String(d.getDate()).padStart(2,'0')
  return `${y}-${m}-${day}`
}

export default function MealPlans(){
  const { user } = useAuth()
  const [weekStart, setWeekStart] = useState(startOfWeek(new Date()))
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [chefMeals, setChefMeals] = useState([])
  const [tab, setTab] = useState('overview')

  const log = useMemo(() => (
    (...args) => console.log('[MealPlans]', ...args)
  ), [])

  useEffect(()=>{
    log('mount', {
      apiBase: import.meta.env.VITE_API_BASE || '(relative via proxy)',
      page: 'MealPlans',
      now: new Date().toISOString(),
    })
  }, [log])

  const fetchPlan = async ()=>{
    setLoading(true); setError(null)
    try{
      const params = { week_start_date: fmtYMD(weekStart) }
      const tok = localStorage.getItem('accessToken')
      log('fetchPlan token?', { present: Boolean(tok), length: tok?.length })
      log('fetchPlan → GET /meals/api/meal_plans/', { params })
      const resp = await api.get(`/meals/api/meal_plans/`, { params })
      log('fetchPlan ←', { status: resp.status, keys: Object.keys(resp.data||{}), raw: resp.data })
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
      setPlan(normalized || null)
    }catch(e){
      const status = e?.response?.status
      const data = e?.response?.data
      log('fetchPlan error', { status, data, message: e?.message })
      if (status === 401){
        window.location.href = '/login'
      }
      setError('No plan found. Generate one below.')
      setPlan(null)
    }finally{ setLoading(false) }
  }

  const fetchChefMeals = async ()=>{
    // If user has no postal code, skip requests and surface hint
    if (!user?.postal_code && !(user?.address && user.address.postalcode)){
      log('fetchChefMeals skipped: missing postal code', { userPostal: user?.postal_code, addrPostal: user?.address?.postalcode })
      setChefMeals([])
      return
    }
    try{
      const params = { week_start_date: fmtYMD(weekStart) }
      log('fetchChefMeals → GET /meals/api/chef-meals-by-postal-code/', { params })
      const resp = await api.get(`/meals/api/chef-meals-by-postal-code/`, { params })
      log('fetchChefMeals ←', { status: resp.status, count: (resp.data?.results||resp.data||[]).length, raw: resp.data })
      setChefMeals(resp.data.results || resp.data || [])
    }catch(e){
      // Show a friendly hint if backend indicates missing postal code
      setChefMeals([])
      const detail = e?.response?.data?.code || e?.response?.data?.detail || ''
      log('fetchChefMeals error', { status: e?.response?.status, data: e?.response?.data, detail, message: e?.message })
      if (e?.response?.status === 400 || e?.response?.status === 422){
        console.warn('Chef meals request issue:', e?.response?.data)
        alert('Chef meals unavailable. Please set your postal code in Profile and try again. Redirecting you to Profile…')
        window.location.href = '/profile'
      }
    }
  }

  useEffect(()=>{
    log('useEffect weekStart changed', { weekStart: fmtYMD(weekStart) })
    fetchPlan(); fetchChefMeals()
  }, [weekStart])

  const shiftWeek = (delta)=>{
    const d = new Date(weekStart); d.setDate(d.getDate()+delta*7); const next = startOfWeek(d); setWeekStart(next)
    log('shiftWeek', { delta, newWeekStart: fmtYMD(next) })
  }

  const generatePlan = async ()=>{
    setLoading(true); setError(null)
    try{
      const idem = newIdempotencyKey()
      const payload = { week_start_date: fmtYMD(weekStart) }
      log('generatePlan → POST /meals/api/generate_meal_plan/ (with Idempotency-Key)', { payload, idem })
      let resp
      try{
        resp = await api.post('/meals/api/generate_meal_plan/', payload, { headers: { 'Idempotency-Key': idem } })
      }catch(err){
        // CORS may block custom headers; retry without Idempotency-Key
        log('generatePlan retry without Idempotency-Key due to error', { message: err?.message })
        resp = await api.post('/meals/api/generate_meal_plan/', payload)
      }
      log('generatePlan ←', { status: resp.status, keys: Object.keys(resp.data||{}), raw: resp.data })
      // If immediate plan returned:
      if (resp.data && resp.data.meals){ setPlan(resp.data) }
      else {
        // Show info and poll if a polling_url provided
        alert('Plan generation requested. This may take a few minutes.')
      }
    }catch(e){
      log('generatePlan error', { status: e?.response?.status, data: e?.response?.data, message: e?.message })
      setError('Could not generate plan. Check preferences or try again.')
    }finally{ setLoading(false) }
  }

  return (
    <div className="page-plans">
      <div className="plans-header card" role="group" aria-label="Meal plan controls">
        <div className="left">
          <h2 style={{margin:'0 0 .25rem'}}>Meal Plans</h2>
          <div className="sub">Week of <strong>{fmtISO(weekStart)}</strong></div>
        </div>
        <div className="right">
          <div className="controls">
            <button className="btn btn-outline" onClick={()=>shiftWeek(-1)}>← Prev Week</button>
            <button className="btn btn-outline" onClick={()=>shiftWeek(1)}>Next Week →</button>
            <button className="btn btn-primary" onClick={generatePlan}>Generate / Refresh</button>
          </div>
          <div className="tabs">
            <button className={`tab ${tab==='overview'?'active':''}`} onClick={()=>{ log('tab→overview'); setTab('overview') }}>Overview</button>
            <button className={`tab ${tab==='chefs'?'active':''}`} onClick={()=>{ log('tab→chefs'); setTab('chefs') }}>Chef Meals</button>
          </div>
        </div>
      </div>

      {loading && <div className="card">Loading…</div>}
      {error && <div className="card" style={{borderColor:'#d9534f'}}>{error}</div>}

      {tab==='overview' && (
        <Overview
          plan={plan}
          weekStart={weekStart}
          chefMeals={chefMeals}
          onChange={()=>{ fetchPlan() }}
          onReplaceChef={()=> setTab('chefs')}
        />
      )}

      {tab==='chefs' && (
        user?.postal_code || (user?.address && user.address.postalcode) ? (
          <ChefMeals chefMeals={chefMeals} weekStart={weekStart} onChange={()=>{ fetchPlan(); fetchChefMeals() }} />
        ) : (
          <div className="card">Please set your postal code in your Profile to view chef meals near you.</div>
        )
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

function Overview({ plan, weekStart, chefMeals, onChange, onReplaceChef }){
  const [selectedSlot, setSelectedSlot] = useState(null) // { day, meal, rect }
  const [working, setWorking] = useState(false)
  const [error, setError] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [updatePreview, setUpdatePreview] = useState(null) // {old_meal, new_meal, ...}
  const [replacingId, setReplacingId] = useState(null)
  const [expandedDescIds, setExpandedDescIds] = useState(()=> new Set())
  const [updatedIds, setUpdatedIds] = useState(()=> new Set())
  if (!plan) return <div className="card">No plan available for this week.</div>
  const meals = Array.isArray(plan?.meals) ? plan.meals : (plan?.meal_plan_meals || [])
  const grouped = groupByDay(meals || [])
  const dayOrder = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
  const typeOrder = ['Breakfast','Lunch','Dinner']
  const flatRows = Object.keys(grouped).flatMap(day => (grouped[day]||[]).map(m => ({ ...m, __day: day })))
    .sort((a,b)=> dayOrder.indexOf(a.__day) - dayOrder.indexOf(b.__day)
      || typeOrder.indexOf((a.meal_type||a.type)) - typeOrder.indexOf((b.meal_type||b.type)))

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

  const onSelect = (day, meal, ev) => {
    try{
      const r = ev?.currentTarget?.getBoundingClientRect?.()
      const rect = r ? { top: r.top + window.scrollY, left: r.left + window.scrollX, right: r.right + window.scrollX, bottom: r.bottom + window.scrollY, width: r.width } : null
      setSelectedSlot({ day, meal, rect })
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
    }catch(e){ setError('Unable to delete meal.') } finally { setWorking(false) }
  }

  function dayToDateString(weekStartDate, dayName){
    const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
    const offset = map[dayName] ?? 0
    const d = new Date(weekStartDate)
    d.setDate(d.getDate()+offset)
    return fmtYMD(d)
  }

  async function modifyMeal(meal){
    if (!prompt?.trim()) return
    setWorking(true); setError(null); setUpdatePreview(null)
    setReplacingId(meal.meal_plan_meal_id || meal.id)
    try{
      const mealPlanMealId = meal.meal_plan_meal_id || meal.id
      const mealDate = dayToDateString(weekStart, meal.day || meal.day_of_week)
      const resp = await api.post('/meals/api/update_meals_with_prompt/', {
        meal_plan_meal_ids: [meal.meal_plan_meal_id || meal.id],
        meal_dates: [mealDate],
        prompt
      })
      const updates = resp?.data?.updates || []
      if (updates.length > 0){
        setUpdatePreview(updates[0])
      } else {
        setUpdatePreview({ none: true })
      }
      // Mark row as updated (temporary chip)
      setUpdatedIds(prev => {
        const next = new Set(prev); next.add(mealPlanMealId); return next
      })
      setTimeout(()=>{
        setUpdatedIds(prev => { const next = new Set(prev); next.delete(mealPlanMealId); return next })
      }, 2500)
      onChange && onChange()
    }catch(e){ setError('Unable to apply changes.') } finally { setWorking(false); setReplacingId(null) }
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
          {flatRows.map((m,i)=>{
            const day = m.__day
            const type = m.type || m.meal_type
            const title = m.name || m.meal?.name
            const desc = m.meal?.description || m.description || ''
            const id = m.meal_plan_meal_id || m.id || m.meal?.id || `${day}-${i}`
            const replacing = replacingId === (m.meal_plan_meal_id || m.id)
            return (
              <tr key={id} id={`row-${id}`} className={replacing ? 'replacing' : ''}>
                <td className="col-day">{day}</td>
                <td className="col-type">{type}</td>
                <td className="col-name">{title}</td>
                <td className="col-desc" title={desc}>
                  <div className={`desc-clamp ${expandedDescIds.has(id)?'expanded':''}`}>{desc}</div>
                  {desc && (
                    <button className="btn-link" onClick={(ev)=>{ ev.stopPropagation(); toggleDesc(id) }}>
                      {expandedDescIds.has(id) ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </td>
                <td className="col-actions">
                  {replacing ? (
                    <div className="updating-chip"><span className="spinner" /> Updating…</div>
                  ) : updatedIds.has(id) ? (
                    <div className="updated-chip">Updated</div>
                  ) : (
                    <button className="btn btn-outline btn-sm" onClick={(ev)=> { ev.stopPropagation(); onSelect(day, m) }}>Edit</button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {selectedSlot && (
        <RightEditPanel
          open={Boolean(selectedSlot)}
          slot={selectedSlot}
          meal={selectedSlot.meal}
          weekStart={weekStart}
          chefMeals={chefMeals}
          prompt={prompt}
          setPrompt={setPrompt}
          working={working}
          error={error}
          updatePreview={updatePreview}
          onJumpToSlot={jumpToSlot}
          onClose={()=> { setSelectedSlot(null); setUpdatePreview(null) }}
          onDelete={()=> deleteMeal(selectedSlot.meal)}
          onApply={()=> modifyMeal(selectedSlot.meal)}
          onReplaceChef={()=> { setSelectedSlot(null); onReplaceChef && onReplaceChef() }}
        />
      )}
    </div>
  )
}

function RightEditPanel({ open, slot, meal, weekStart, chefMeals, prompt, setPrompt, working, error, updatePreview, onClose, onDelete, onApply, onReplaceChef, onJumpToSlot }){
  if (!open || !meal) return null
  const mealType = meal.type || meal.meal_type
  const mealTitle = meal.name || meal.meal?.name
  const dayName = meal.day || meal.day_of_week
  const dayOptions = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
  const typeOptions = ['Breakfast','Lunch','Dinner']
  const [newDay, setNewDay] = useState(dayName)
  const [newType, setNewType] = useState(mealType)
  const [altMealId, setAltMealId] = useState('')

  // Determine if a matching chef meal exists: same meal type and same date as this slot
  let canReplaceWithChef = false
  try{
    if (Array.isArray(chefMeals) && chefMeals.length){
      const typeNorm = String(mealType || '').toLowerCase()
      const map = { Monday:0, Tuesday:1, Wednesday:2, Thursday:3, Friday:4, Saturday:5, Sunday:6 }
      const offset = map[String(meal.day || meal.day_of_week)] ?? 0
      const slotDate = new Date(weekStart)
      slotDate.setDate(slotDate.getDate()+offset)
      const iso = slotDate.toISOString().slice(0,10)
      canReplaceWithChef = chefMeals.some(cm => {
        const cmType = String(cm.meal_type || cm.type || '').toLowerCase()
        if (cmType && typeNorm && cmType !== typeNorm) return false
        if (cm.available_dates && typeof cm.available_dates === 'object') return Boolean(cm.available_dates[iso])
        if (cm.date){ try{ return String(cm.date).slice(0,10) === iso }catch{ return false } }
        return false
      })
    }
  }catch{}

  return (
    <>
      <div className="right-panel-overlay" onClick={onClose} />
      <aside className="right-panel" role="dialog" aria-label={`Edit ${mealTitle}`}>
        <div className="right-panel-head">
          <div className="slot-title">Edit “{mealTitle}”</div>
          <button className="icon-btn" aria-label="Close" onClick={onClose}>✕</button>
        </div>
        <div className="right-panel-body">
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
              <label className="label">Day</label>
              <select className="select" value={newDay} onChange={e=> { setNewDay(e.target.value); onJumpToSlot?.(e.target.value, newType) }}>
                {dayOptions.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Meal type</label>
              <select className="select" value={newType} onChange={e=> { setNewType(e.target.value); onJumpToSlot?.(newDay, e.target.value) }}>
                {typeOptions.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div className="actions-row" style={{alignItems:'center', justifyContent:'space-between'}}>
            <div>
              {canReplaceWithChef ? (
                <button className="btn btn-outline" onClick={onReplaceChef} disabled={working}>Replace with Chef</button>
              ) : (
                <span className="muted">No chef option for this slot.</span>
              )}
            </div>
            <div>
              <button className="btn btn-danger" onClick={onDelete} disabled={working}>Delete</button>
            </div>
          </div>
          <div style={{margin:'.25rem 0 .5rem'}}>
            <label className="label">Alternative meal</label>
            <select className="select" value={altMealId} onChange={e=> setAltMealId(e.target.value)} disabled>
              <option value="">No alternatives (coming soon)</option>
            </select>
          </div>
          <div className="refactor">
            <textarea className="textarea" rows={4} placeholder={`Refactor this ${mealType?.toLowerCase()}…`} value={prompt} onChange={e=> setPrompt(e.target.value)} />
            <div className="actions-row">
              <button className="btn btn-primary" onClick={onApply} disabled={working || !prompt.trim()}>Apply changes</button>
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
      const iso = slotDate.toISOString().slice(0,10)
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
  return (
    <div ref={popRef} className="slot-popover" style={position} role="dialog" aria-label={`Edit ${mealTitle}`}>
      <div className="slot-popover-head">
        <div className="slot-title">Edit “{mealTitle}”</div>
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

function ChefMeals({ chefMeals, weekStart, onChange }){
  const [placing, setPlacing] = useState(false)

  const replaceWithChef = async (cm)=>{
    setPlacing(true)
    try{
      const payload = { meal_event: cm.event_id || cm.id, quantity: 1, special_requests: '' }
      const idem = newIdempotencyKey()
      const resp = await api.post('/meals/api/chef-meal-orders/', payload, { headers: { 'Idempotency-Key': idem } })
      if (resp.status === 201 || resp.status === 200){
        alert('Order placed. Proceed to payment if required.')
        onChange && onChange()
      } else {
        alert('Could not place order.')
      }
    }catch(e){
      alert('Order failed.')
    }finally{
      setPlacing(false)
    }
  }

  if (!chefMeals || chefMeals.length===0) return <div className="card">No chef meals available for this week near you.</div>
  return (
    <div className="grid grid-2">
      {chefMeals.map((cm)=> (
        <div key={cm.id} className="card">
          <h3>{cm.meal_name || cm.name}</h3>
          <p className="muted">{cm.description || ''}</p>
          <p><strong>Chef:</strong> {cm.chef_name || cm.chef}</p>
          {cm.date && <p><strong>Date:</strong> {new Date(cm.date).toLocaleString()}</p>}
          {cm.price && <p><strong>Price:</strong> ${cm.price}</p>}
          <button className="btn btn-primary" onClick={()=>replaceWithChef(cm)} disabled={placing}>Replace / Order</button>
        </div>
      ))}
    </div>
  )
}
