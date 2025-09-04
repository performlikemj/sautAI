import React, { useEffect, useState, useRef, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../api'
import Listbox from '../components/Listbox.jsx'
import { COUNTRIES, countryNameFromCode, codeFromCountryName } from '../utils/geo.js'

const FALLBACK_DIETS = ['Everything','Vegetarian','Vegan','Halal','Kosher','Gluten‑Free','Pescatarian','Keto','Paleo','Low‑Calorie','Low‑Sodium','High‑Protein','Dairy‑Free','Nut‑Free']
const FALLBACK_ALLERGENS = ['Peanuts','Tree nuts','Milk','Egg','Wheat','Soy','Fish','Shellfish','Sesame','Mustard','Celery','Lupin','Sulfites','Molluscs','Corn','Gluten','Kiwi','Pine Nuts','Sunflower Seeds']
const TIMEZONES = ['UTC','America/New_York','America/Chicago','America/Los_Angeles','Europe/London','Europe/Paris','Asia/Tokyo']

export default function Profile(){
  const { user, setUser, refreshUser } = useAuth()
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)
  const [applyOpen, setApplyOpen] = useState(false)
  const [chefForm, setChefForm] = useState({ experience:'', bio:'', serving_areas:'', profile_pic:null })
  const [applyMsg, setApplyMsg] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [toasts, setToasts] = useState([]) // {id, text, tone, closing}
  const [locationHint, setLocationHint] = useState(false)
  // Household & communication
  const [household, setHousehold] = useState([]) // [{name, age, dietary_preferences:[], notes}]
  const [householdIdx, setHouseholdIdx] = useState(0)
  const [receiveEmails, setReceiveEmails] = useState(true)
  const [prefLang, setPrefLang] = useState('en')
  const [prefTz, setPrefTz] = useState('UTC')
  // dynamic option lists
  const [dietOptions, setDietOptions] = useState(FALLBACK_DIETS)
  const [allergyOptions, setAllergyOptions] = useState(FALLBACK_ALLERGENS)
  const [langOptions, setLangOptions] = useState([
    { code:'en', label:'English' },
    { code:'es', label:'Español' },
    { code:'fr', label:'Français' },
    { code:'ja', label:'日本語' },
  ])
  // Delete account
  const [confirmText, setConfirmText] = useState('')
  const [deletePassword, setDeletePassword] = useState('')
  const [deleting, setDeleting] = useState(false)

  useEffect(()=>{
    api.get('/auth/api/user_details/').then(res=> {
      const data = res.data || {}
      const normalized = {
        ...data,
        // Map backend field names to UI fields and coerce types for inputs
        phone: data.phone_number || '',
        custom_allergies: Array.isArray(data.custom_allergies) ? data.custom_allergies.join(', ') : (data.custom_allergies || ''),
        custom_dietary_preferences: Array.isArray(data.custom_dietary_preferences) ? data.custom_dietary_preferences.join(', ') : (data.custom_dietary_preferences || ''),
        is_chef: Boolean(data?.is_chef),
        current_role: data?.current_role || 'customer'
      }
      setForm(prev => ({ ...(prev||{}), ...normalized }))
      if (Array.isArray(data.household_members)){
        setHousehold(data.household_members.map(m => ({
          name: m.name || '',
          age: typeof m.age === 'number' ? m.age : (m.age ? parseInt(m.age, 10) || 0 : 0),
          dietary_preferences: Array.isArray(m.dietary_preferences) ? m.dietary_preferences : [],
          notes: m.notes || ''
        })))
      }
      setReceiveEmails(!Boolean(data.unsubscribed_from_emails))
      setPrefLang(data.preferred_language || 'en')
      // Prefer user_timezone, then timezone, else default
      setPrefTz(data.user_timezone || data.timezone || 'UTC')
    })
    // Fetch languages only; dietary/allergies/timezones use fallbacks/browser
    ;(async ()=>{
      try{
        const langRes = await api.get('/auth/api/languages/').catch(()=>null)
        if (langRes?.data && Array.isArray(langRes.data)) {
          const seen = new Set()
          const langs = []
          for (const l of langRes.data){
            const code = l.code || l.id || l.locale
            if (!code || seen.has(code)) continue
            seen.add(code)
            langs.push({ code, label: l.name_local ? `${l.name} (${l.name_local})` : (l.name || code) })
          }
          if (langs.length) setLangOptions(langs)
        }
      }catch{ /* ignore; fallback languages remain */ }
    })()
    // Auto-open chef application if hinted by URL (?applyChef=1)
    try{
      const params = new URLSearchParams(window.location.search)
      if (params.get('applyChef') === '1' && !applyOpen){
        // If missing city/country, nudge first instead of opening panel
        const needCity = !((form?.city && String(form.city).trim()) || (user?.address && user.address.city))
        const needCountry = !((form?.country && String(form.country).trim()) || (user?.address && user.address.country))
        const needLocation = needCity || needCountry || params.get('completeLocation') === '1'
        if (needLocation){ setLocationHint(true) }
        else { setApplyOpen(true) }
      }
    }catch{}
  }, [])

  // When auth context loads address, populate form without making another API call
  useEffect(()=>{
    try{
      const a = user?.address || null
      if (!a) return
      const postal = a.input_postalcode || a.postal_code || a.postalcode || ''
      const rawCountry = a.country || ''
      let countryCode = String(rawCountry||'').trim()
      if (countryCode && countryCode.length !== 2){
        const mapped = codeFromCountryName(countryCode)
        if (mapped) countryCode = mapped
      } else {
        countryCode = countryCode.toUpperCase()
      }
      setForm(prev => ({
        ...(prev||{}),
        street: a.street || '',
        city: a.city || '',
        state: a.state || '',
        postal_code: postal,
        country: countryCode || (prev?.country || '')
      }))
    }catch{}
  }, [user?.address])

  const set = (k)=>(e)=> setForm({...form, [k]: e.target.value})
  const toggleList = (k, v) => {
    const arr = new Set(form[k] || [])
    if (arr.has(v)) arr.delete(v); else arr.add(v)
    setForm({...form, [k]: Array.from(arr)})
  }

  const saveProfile = async (sourceLabel='profile')=>{
    setSaving(true); setMsg(`Saving ${sourceLabel}…`)
    try{
      // Validate country/postal pair rule before sending (consider existing address defaults)
      const postal = (form?.post_code || form?.postal_code || user?.address?.postalcode || '').trim()
      const countryVal = (form?.country || user?.address?.country || '').trim()
      const hasPostal = Boolean(postal)
      const hasCountry = Boolean(countryVal)
      if ((hasPostal && !hasCountry) || (!hasPostal && hasCountry)){
        setSaving(false)
        setLocationHint(true)
        pushToast('Please provide both country and postal code together.', 'error')
        try{ document.querySelector('#personal-info')?.scrollIntoView({ behavior:'smooth', block:'start' }) }catch{}
        return
      }
      const payload = buildProfilePayload()
      const resp = await api.post('/auth/api/update_profile/', payload)
      if (resp.status >= 200 && resp.status < 300){
        setMsg('Profile updated successfully.')
        try{ await refreshUser?.() }catch{}
        pushToast('Profile updated successfully.', 'success')
      } else {
        setMsg('Failed to update profile.')
        pushToast('Failed to update profile.', 'error')
      }
    }catch(e){
      setMsg('Failed to update profile.')
      pushToast('Failed to update profile.', 'error')
    }finally{ setSaving(false) }
  }

  // Deprecated per unification; kept for compatibility if referenced
  const saveHouseholdAndComms = async ()=> saveProfile('preferences')

  // Toast helpers (matching Meal Plans slide-in)
  const pushToast = (text, tone='info')=>{
    const id = Math.random().toString(36).slice(2)
    setToasts(prev => [...prev, { id, text, tone, closing:false }])
    setTimeout(()=>{
      setToasts(prev => prev.map(t => t.id === id ? { ...t, closing:true } : t))
      setTimeout(()=> setToasts(prev => prev.filter(t => t.id !== id)), 260)
    }, 3000)
  }

  const ensureLocationBeforeApply = ()=>{
    const city = (form?.city || user?.address?.city || '').trim()
    const country = (form?.country || user?.address?.country || '').trim()
    if (!city || !country){
      setLocationHint(true)
      pushToast('Please add your city and country before applying to be a chef.', 'error')
      // Try to scroll Personal Info into view
      try{ document.querySelector('#personal-info')?.scrollIntoView({ behavior:'smooth', block:'start' }) }catch{}
      return false
    }
    return true
  }

  const addMember = ()=> setHousehold(arr => ([...arr, { name:'', age:0, dietary_preferences:[], notes:'' }]))
  const removeMember = (idx)=> setHousehold(arr => arr.filter((_,i)=> i!==idx))
  const updateMember = (idx, key, value)=> setHousehold(arr => arr.map((m,i)=> i===idx ? ({...m, [key]: value}) : m))

  // Build unified payload matching backend Streamlit update_profile
  const buildProfilePayload = ()=>{
    const normalizeCommaList = (val)=>{
      if (Array.isArray(val)){
        // Support arrays of strings or objects with name
        return val.map(v => typeof v === 'object' && v !== null ? (v.name ?? '') : String(v))
                 .map(s => String(s).trim())
                 .filter(Boolean)
      }
      if (typeof val === 'string'){
        return val.split(',').map(s=>s.trim()).filter(Boolean)
      }
      return []
    }
    const ensureArray = (val)=> Array.isArray(val) ? val : (val ? [val] : [])

    const cleanedHousehold = (household||[])
      .map(m => ({
        name: (m.name||'').trim(),
        age: m.age ? Number(m.age) : null,
        dietary_preferences: Array.isArray(m.dietary_preferences) ? m.dietary_preferences : [],
        notes: (m.notes||'').trim(),
      }))
      .filter(m => m.name || m.age || (m.dietary_preferences && m.dietary_preferences.length) || m.notes)
    // Normalize postal/country: send both or neither
    const postal = (form?.post_code || form?.postal_code || user?.address?.postalcode || '').trim()
    const countryVal = (form?.country || user?.address?.country || '').trim()
    const sendPostal = Boolean(postal && countryVal)

    return {
      username: form?.username || '',
      email: form?.email || '',
      phone_number: form?.phone || '',
      dietary_preferences: ensureArray(form?.dietary_preferences),
      custom_dietary_preferences: normalizeCommaList(form?.custom_dietary_preferences),
      allergies: ensureArray(form?.allergies),
      custom_allergies: normalizeCommaList(form?.custom_allergies),
      timezone: prefTz,
      user_timezone: prefTz,
      preferred_language: prefLang,
      unsubscribed_from_emails: !receiveEmails,
      household_member_count: Math.max(1, cleanedHousehold.length),
      household_members: cleanedHousehold,
      address: {
        street: form?.street || '',
        city: form?.city || '',
        state: form?.state || '',
        postalcode: sendPostal ? postal : '',
        input_postalcode: sendPostal ? postal : '',
        country: sendPostal ? countryVal : ''
      }
    }
  }

  const submitChef = async (e)=>{
    e.preventDefault()
    setApplyMsg(null)
    if (!ensureLocationBeforeApply()){
      setApplyMsg('Please complete your city and country in Personal Info, then submit again.')
      return
    }
    const fd = new FormData()
    const city = (form?.city || user?.address?.city || '').trim()
    const country = (form?.country || user?.address?.country || '').trim()
    fd.append('experience', chefForm.experience)
    fd.append('bio', chefForm.bio)
    fd.append('serving_areas', chefForm.serving_areas)
    if (city) fd.append('city', city)
    if (country) fd.append('country', country)
    if (chefForm.profile_pic) fd.append('profile_pic', chefForm.profile_pic)
    try{
      const resp = await api.post('/chefs/api/chefs/submit-chef-request/', fd, { headers:{'Content-Type':'multipart/form-data'} })
      if (resp.status===200 || resp.status===201){
        setApplyMsg('Application submitted. We will notify you when approved.')
        const u = await api.get('/auth/api/user_details/'); setUser(u.data)
      } else {
        setApplyMsg('Submission failed.')
      }
    }catch(e){
      const msg = e?.response?.data?.error || 'Submission failed.'
      setApplyMsg(msg)
    }
  }

  if (!form) return <div>Loading…</div>

  return (
    <div>
      <h2>Profile</h2>
      {/* Inline status message removed in favor of slide-in toasts */}
      {!user?.is_chef && (
        <div className="card" style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:'.75rem', marginBottom:'1rem'}}>
          <div>
            <div style={{fontWeight:800}}>Become a Community Chef</div>
            <div className="muted">Share your cooking, earn fairly, and serve your neighborhood.</div>
          </div>
          <button className="btn btn-primary" onClick={()=> { if (ensureLocationBeforeApply()) setApplyOpen(true) }}>Apply to Become a Chef</button>
        </div>
      )}
      <div className="grid grid-2">
        <div className="card" id="personal-info">
          <h3>Personal Info</h3>
          {locationHint && (
            <div className="callout" style={{marginBottom:'.6rem'}}>
              <div className="icon" aria-hidden>📍</div>
              <div>
                <div style={{fontWeight:800}}>Add your city and country</div>
                <div className="muted">We need your location to match you with nearby customers and show your profile correctly.</div>
              </div>
            </div>
          )}
          <div className="label">Username</div>
          <input className="input" value={form.username||''} onChange={set('username')} />
          <div className="label">Email</div>
          <input className="input" value={form.email||''} onChange={set('email')} />
          <div className="label">Phone</div>
          <input className="input" value={form.phone||''} onChange={set('phone')} />
          <div className="label">City</div>
          <input className="input" value={form.city||''} onChange={set('city')} placeholder={user?.address?.city ? user.address.city : ''} />
          <div className="label">Country</div>
          <Listbox
            options={COUNTRIES.map(c=>({ key:c.code, value:c.code, label:c.name, subLabel:c.code }))}
            value={(form.country || user?.address?.country || '').toUpperCase()}
            onChange={(val)=> setForm({ ...form, country: String(val||'').toUpperCase() })}
            placeholder="Select country"
          />
          <div className="label">Postal Code</div>
          <input className="input" value={form.postal_code||''} onChange={set('postal_code')} />
          <div style={{marginTop:'.6rem'}}>
            <button className="btn btn-primary" onClick={()=> saveProfile('personal info')} disabled={saving}>{saving?'Saving…':'Save'}</button>
            {!user?.is_chef && (
              <button className="btn btn-outline" style={{marginLeft:'.5rem'}} onClick={()=> { if (ensureLocationBeforeApply()) setApplyOpen(true) }}>Become a Chef</button>
            )}
          </div>
        </div>
        <div className="card">
          <h3>Preferences</h3>
          <div className="label">Dietary</div>
          <DietMultiSelect
            options={dietOptions}
            selected={form.dietary_preferences||[]}
            onChange={(arr)=> setForm({...form, dietary_preferences: arr})}
            placeholder="Select dietary preferences"
          />
          <div className="label">Custom dietary (comma separated)</div>
          <input className="input" value={form.custom_dietary_preferences||''} onChange={set('custom_dietary_preferences')} />

          <div className="label" style={{marginTop:'.6rem'}}>Allergies</div>
          <DietMultiSelect
            options={allergyOptions}
            selected={form.allergies||[]}
            onChange={(arr)=> setForm({...form, allergies: arr})}
            placeholder="Select allergies"
          />
          <div className="label">Custom allergies (comma separated)</div>
          <input className="input" value={form.custom_allergies||''} onChange={set('custom_allergies')} />
          <div style={{marginTop:'.6rem'}}>
            <button className="btn btn-outline" onClick={()=> saveProfile('preferences')} disabled={saving}>Save Preferences</button>
          </div>
        </div>
      </div>

      <div className="grid grid-2" style={{marginTop:'1rem'}}>
        <div className="card">
          <h3>Household</h3>
          <p className="muted">Add members to tailor plans. Use arrows or the selector to switch between members.</p>
          {household.length === 0 && (
            <div className="muted" style={{marginBottom:'.5rem'}}>No household members yet.</div>
          )}
          {household.length > 0 && (
            <div style={{display:'flex', alignItems:'center', gap:'.5rem', marginBottom:'.5rem'}}>
              <button className="btn btn-outline" onClick={()=> setHouseholdIdx(i=> Math.max(0, i-1))} disabled={householdIdx===0}>←</button>
              <select className="select" value={householdIdx} onChange={e=> setHouseholdIdx(Number(e.target.value))}>
                {household.map((_,i)=> <option key={i} value={i}>{`Member ${i+1}`}</option>)}
              </select>
              <button className="btn btn-outline" onClick={()=> setHouseholdIdx(i=> Math.min(household.length-1, i+1))} disabled={householdIdx===household.length-1}>→</button>
              <span className="muted" style={{marginLeft:'.25rem'}}>({householdIdx+1} of {household.length})</span>
            </div>
          )}
          {household.length > 0 && (()=>{ const idx = householdIdx; const m = household[idx] || { name:'', age:0, dietary_preferences:[], notes:'' }
            return (
              <div className="card" style={{padding:'.75rem', marginBottom:'.5rem'}}>
                <div className="grid" style={{gridTemplateColumns:'1fr 140px', gap:'.5rem'}}>
                  <div>
                    <div className="label">Name</div>
                    <input className="input" value={m.name} onChange={e=>updateMember(idx,'name',e.target.value)} />
                  </div>
                  <div>
                    <div className="label">Age</div>
                    <input className="input" type="number" min="0" value={m.age||0} onChange={e=>updateMember(idx,'age',Number(e.target.value||0))} />
                  </div>
                </div>
                <div className="label" style={{marginTop:'.4rem'}}>Dietary Preferences</div>
                <DietMultiSelect
                  options={dietOptions}
                  selected={m.dietary_preferences||[]}
                  onChange={(arr)=> updateMember(idx,'dietary_preferences', arr)}
                  placeholder="Select preferences for this member"
                />
                <div className="label" style={{marginTop:'.4rem'}}>Notes</div>
                <textarea className="textarea" rows={2} value={m.notes} onChange={e=>updateMember(idx,'notes',e.target.value)} />
                <div style={{marginTop:'.5rem', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                  <span className="muted">Member {idx+1} of {household.length}</span>
                  <button className="btn btn-outline" onClick={()=>removeMember(idx)}>Remove</button>
                </div>
              </div>
            )})()}
          <div>
            <button className="btn btn-primary" onClick={()=> { addMember(); setHouseholdIdx(household.length) }}>Add Member</button>
          </div>
          <div style={{marginTop:'.6rem'}}>
            <button className="btn btn-outline" onClick={()=> saveProfile('household')} disabled={saving}>Save Household</button>
          </div>
        </div>

        <div className="card">
          <h3>Communication</h3>
          <div className="label">Email Preferences</div>
          <div role="radiogroup" aria-label="Email preferences" style={{display:'grid', gap:'.35rem'}}>
            <label className="radio">
              <input type="radio" name="email_prefs" checked={receiveEmails} onChange={()=>setReceiveEmails(true)} />
              <span style={{marginLeft:'.35rem'}}>Yes — receive emails</span>
            </label>
            <label className="radio">
              <input type="radio" name="email_prefs" checked={!receiveEmails} onChange={()=>setReceiveEmails(false)} />
              <span style={{marginLeft:'.35rem'}}>No — do not email me</span>
            </label>
          </div>
          <div className="label" style={{marginTop:'.6rem'}}>Preferred Language</div>
          <select className="select" value={prefLang} onChange={e=> setPrefLang(e.target.value)}>
            {langOptions.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
          <div className="label" style={{marginTop:'.6rem'}}>Time Zone</div>
          <TimezoneSelect value={prefTz} onChange={setPrefTz} />
          <div style={{marginTop:'.6rem'}}>
            <button className="btn btn-outline" onClick={()=> saveProfile('communication')} disabled={saving}>Save Communication</button>
          </div>
        </div>
      </div>

      {applyOpen && (
        <>
          <div className="right-panel-overlay" onClick={()=> setApplyOpen(false)} />
          <aside className="right-panel" role="dialog" aria-label="Become a Chef">
            <div className="right-panel-head">
              <div className="slot-title">Become a Community Chef</div>
              <button className="icon-btn" onClick={()=> setApplyOpen(false)}>✕</button>
            </div>
            <div className="right-panel-body">
              {applyMsg && <div className="card" style={{marginBottom:'.6rem'}}>{applyMsg}</div>}
              <div className="label">Experience</div>
              <textarea className="textarea" rows={3} value={chefForm.experience} onChange={e=>setChefForm({...chefForm, experience:e.target.value})} />
              <div className="label">Bio</div>
              <textarea className="textarea" rows={3} value={chefForm.bio} onChange={e=>setChefForm({...chefForm, bio:e.target.value})} />
              <div className="label">Serving areas (postal codes)</div>
              <input className="input" value={chefForm.serving_areas} onChange={e=>setChefForm({...chefForm, serving_areas:e.target.value})} />
              <div className="label">Profile picture (optional)</div>
              <input type="file" onChange={e=>setChefForm({...chefForm, profile_pic:e.target.files?.[0]||null})} />
              <div className="actions-row" style={{marginTop:'.6rem'}}>
                <button className="btn btn-primary" disabled={submitting} onClick={async ()=>{
                  setSubmitting(true); setApplyMsg(null)
                  try{
                    const fd = new FormData()
                    fd.append('experience', chefForm.experience)
                    fd.append('bio', chefForm.bio)
                    fd.append('serving_areas', chefForm.serving_areas)
                    if (chefForm.profile_pic) fd.append('profile_pic', chefForm.profile_pic)
                    const resp = await api.post('/chefs/api/chefs/submit-chef-request/', fd, { headers:{'Content-Type':'multipart/form-data'} })
                    if (resp.status===200 || resp.status===201){
                      setApplyMsg('Application submitted. We will notify you when approved.')
                    } else {
                      setApplyMsg('Submission failed. Please try again later.')
                    }
                  }catch(e){ setApplyMsg('Submission failed. Please try again.') }
                  finally{ setSubmitting(false) }
                }}>{submitting?'Submitting…':'Submit Application'}</button>
                <button className="btn btn-outline" onClick={()=> setApplyOpen(false)}>Close</button>
              </div>
            </div>
          </aside>
        </>
      )}

      <div className="card" style={{marginTop:'1rem', borderColor:'#f5c6cb'}}>
        <h3 style={{color:'#a94442'}}>Danger Zone</h3>
        <p className="muted">Delete your account and all associated data. This cannot be undone.</p>
        <div className="label">Type "done eating" to confirm</div>
        <input className="input" value={confirmText} onChange={e=> setConfirmText(e.target.value)} placeholder="done eating" />
        <div className="label" style={{marginTop:'.4rem'}}>Password</div>
        <input className="input" type="password" value={deletePassword} onChange={e=> setDeletePassword(e.target.value)} />
        <div style={{marginTop:'.6rem'}}>
          <button className="btn btn-danger" disabled={deleting || confirmText !== 'done eating' || !deletePassword}
            onClick={async ()=>{
              if (confirmText !== 'done eating' || !deletePassword) return
              setDeleting(true)
              try{
                const resp = await api.delete('/auth/api/delete_account/', { data: { confirmation: confirmText, password: deletePassword } })
                if (resp.status === 200){
                  setMsg('Your account has been deleted. Goodbye!')
                  pushToast('Your account has been deleted. Goodbye!', 'success')
                  window.location.href = '/login'
                } else {
                  setMsg('Failed to delete account.')
                  pushToast('Failed to delete account.', 'error')
                }
              }catch(e){ setMsg('Failed to delete account.'); pushToast('Failed to delete account.', 'error') }
              finally{ setDeleting(false) }
            }}>Delete My Account</button>
        </div>
      </div>
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

function TimezoneSelect({ value, onChange }){
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [zones, setZones] = useState(TIMEZONES)
  const wrapRef = useRef(null)
  useEffect(()=>{
    const onDoc = (e)=>{ if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false) }
    document.addEventListener('click', onDoc)
    return ()=> document.removeEventListener('click', onDoc)
  }, [])
  useEffect(()=>{
    ;(async ()=>{
      try{
        const iana = (Intl && Intl.supportedValuesOf) ? Intl.supportedValuesOf('timeZone') : []
        if (Array.isArray(iana) && iana.length){
          const sorted = Array.from(new Set(iana)).sort((a,b)=> a.localeCompare(b))
          setZones(sorted)
        }
      }catch{ /* ignore */ }
      // No backend fetch for timezones to avoid 404; rely on browser or fallback
    })()
  }, [])
  const filtered = zones.filter(z => z.toLowerCase().includes(query.toLowerCase()))
  return (
    <div ref={wrapRef} className="multi-wrap">
      <div className={`multi-field ${open?'open':''}`} onClick={()=> setOpen(o=>!o)}>
        <span>{value || 'Select time zone'}</span>
        <span className="caret">▾</span>
      </div>
      {open && (
        <div className="multi-pop">
          <input className="input" placeholder="Search…" value={query} onChange={e=> setQuery(e.target.value)} autoFocus />
          <div className="multi-list">
            {filtered.map(tz => (
              <div key={tz} className="multi-item" onClick={()=> { onChange(tz); setOpen(false) }}>
                {tz}
              </div>
            ))}
            {filtered.length===0 && <div className="muted" style={{padding:'.5rem'}}>No matches</div>}
          </div>
        </div>
      )}
    </div>
  )
}

function DietMultiSelect({ options, selected, onChange, placeholder }){
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const wrapRef = useRef(null)
  useEffect(()=>{
    const onDoc = (e)=>{ if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false) }
    document.addEventListener('click', onDoc)
    return ()=> document.removeEventListener('click', onDoc)
  }, [])
  const filtered = useMemo(()=> options.filter(o => String(o).toLowerCase().includes(query.toLowerCase())), [options, query])
  const toggle = (val)=>{
    const set = new Set(selected||[])
    if (set.has(val)) set.delete(val); else set.add(val)
    onChange(Array.from(set))
  }
  return (
    <div ref={wrapRef} className="multi-wrap">
      <div className={`multi-field ${open?'open':''}`} onClick={()=> setOpen(o=>!o)} role="combobox" aria-expanded={open}>
        {(selected||[]).length === 0 ? (
          <span className="muted">{placeholder}</span>
        ) : (
          <div className="chips">
            {(selected||[]).map(v => (
              <span key={v} className="chip" onClick={(e)=>{ e.stopPropagation(); toggle(v) }}>{v} ✕</span>
            ))}
          </div>
        )}
        <span className="caret">▾</span>
      </div>
      {open && (
        <div className="multi-pop">
          <input className="input" placeholder="Search…" value={query} onChange={e=> setQuery(e.target.value)} autoFocus />
          <div className="multi-list">
            {filtered.map(opt => (
              <label key={opt} className={`multi-item ${selected?.includes(opt)?'sel':''}`}>
                <input type="checkbox" checked={selected?.includes(opt)} onChange={()=> toggle(opt)} />
                <span>{opt}</span>
              </label>
            ))}
            {filtered.length===0 && <div className="muted" style={{padding:'.5rem'}}>No matches</div>}
          </div>
        </div>
      )}
    </div>
  )
}
