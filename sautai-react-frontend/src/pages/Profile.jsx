import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../api'

const DIETS = ['Everything','Vegetarian','Vegan','Halal','Kosher','Gluten‑Free']
const ALLERGENS = ['Peanuts','Shellfish','Dairy','Eggs','Soy','Wheat']

export default function Profile(){
  const { user, setUser } = useAuth()
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)
  const [applyOpen, setApplyOpen] = useState(false)
  const [chefForm, setChefForm] = useState({ experience:'', bio:'', serving_areas:'', profile_pic:null })
  const [applyMsg, setApplyMsg] = useState(null)

  useEffect(()=>{
    api.get('/auth/api/user_details/').then(res=> setForm({
      ...res.data,
      is_chef: Boolean(res.data?.is_chef),
      current_role: res.data?.current_role || 'customer'
    }))
  }, [])

  const set = (k)=>(e)=> setForm({...form, [k]: e.target.value})
  const toggleList = (k, v) => {
    const arr = new Set(form[k] || [])
    if (arr.has(v)) arr.delete(v); else arr.add(v)
    setForm({...form, [k]: Array.from(arr)})
  }

  const save = async ()=>{
    setSaving(true); setMsg(null)
    try{
      const resp = await api.put('/auth/api/user_details/', form)
      setUser(resp.data)
      setMsg('Profile updated.')
    }catch(e){
      setMsg('Failed to save profile.')
    }finally{ setSaving(false) }
  }

  const submitChef = async (e)=>{
    e.preventDefault()
    setApplyMsg(null)
    const fd = new FormData()
    fd.append('experience', chefForm.experience)
    fd.append('bio', chefForm.bio)
    fd.append('serving_areas', chefForm.serving_areas)
    if (chefForm.profile_pic) fd.append('profile_pic', chefForm.profile_pic)
    try{
      const resp = await api.post('/chefs/api/chefs/submit-chef-request/', fd, { headers:{'Content-Type':'multipart/form-data'} })
      if (resp.status===200 || resp.status===201){
        setApplyMsg('Application submitted. We will notify you when approved.')
        // Optionally refresh user
        const u = await api.get('/auth/api/user_details/'); setUser(u.data)
      } else {
        setApplyMsg('Submission failed.')
      }
    }catch(e){
      setApplyMsg('Submission failed.')
    }
  }

  if (!form) return <div>Loading…</div>

  return (
    <div>
      <h2>Profile</h2>
      {msg && <div className="card">{msg}</div>}
      <div className="grid grid-2">
        <div className="card">
          <h3>Personal Info</h3>
          <div className="label">Username</div>
          <input className="input" value={form.username||''} onChange={set('username')} />
          <div className="label">Email</div>
          <input className="input" value={form.email||''} onChange={set('email')} />
          <div className="label">Phone</div>
          <input className="input" value={form.phone||''} onChange={set('phone')} />
          <div className="label">Postal Code</div>
          <input className="input" value={form.postal_code||''} onChange={set('postal_code')} />
          <div style={{marginTop:'.6rem'}}>
            <button className="btn btn-primary" onClick={save} disabled={saving}>{saving?'Saving…':'Save'}</button>
          </div>
        </div>
        <div className="card">
          <h3>Preferences</h3>
          <div className="label">Dietary</div>
          <div style={{display:'flex', flexWrap:'wrap', gap:'.4rem'}}>
            {DIETS.map(d => (
              <label key={d} className="btn btn-outline" style={{cursor:'pointer'}}>
                <input type="checkbox" style={{marginRight:'.35rem'}} checked={(form.dietary_preferences||[]).includes(d)} onChange={()=>toggleList('dietary_preferences', d)} />
                {d}
              </label>
            ))}
          </div>
          <div className="label">Custom dietary (comma separated)</div>
          <input className="input" value={form.custom_dietary_preferences||''} onChange={set('custom_dietary_preferences')} />

          <div className="label" style={{marginTop:'.6rem'}}>Allergies</div>
          <div style={{display:'flex', flexWrap:'wrap', gap:'.4rem'}}>
            {ALLERGENS.map(a => (
              <label key={a} className="btn btn-outline" style={{cursor:'pointer'}}>
                <input type="checkbox" style={{marginRight:'.35rem'}} checked={(form.allergies||[]).includes(a)} onChange={()=>toggleList('allergies', a)} />
                {a}
              </label>
            ))}
          </div>
          <div className="label">Custom allergies (comma separated)</div>
          <input className="input" value={form.custom_allergies||''} onChange={set('custom_allergies')} />
        </div>
      </div>

      {!user?.is_chef && (
        <div className="card" style={{marginTop:'1rem'}}>
          <h3>Become a Community Chef</h3>
          <p>Share your cooking, earn income, and feed your community. 🎉</p>
          {!applyOpen ? (
            <button className="btn btn-primary" onClick={()=>setApplyOpen(true)}>Apply to Become a Chef</button>
          ) : (
            <form onSubmit={submitChef}>
              {applyMsg && <div className="card">{applyMsg}</div>}
              <div className="label">Experience</div>
              <textarea className="textarea" value={chefForm.experience} onChange={e=>setChefForm({...chefForm, experience:e.target.value})} />
              <div className="label">Bio</div>
              <textarea className="textarea" value={chefForm.bio} onChange={e=>setChefForm({...chefForm, bio:e.target.value})} />
              <div className="label">Serving areas (postal codes)</div>
              <input className="input" value={chefForm.serving_areas} onChange={e=>setChefForm({...chefForm, serving_areas:e.target.value})} />
              <div className="label">Profile picture</div>
              <input type="file" onChange={e=>setChefForm({...chefForm, profile_pic:e.target.files?.[0]||null})} />
              <div style={{marginTop:'.6rem'}}>
                <button className="btn btn-primary" type="submit">Submit Application</button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  )
}
