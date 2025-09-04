import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext.jsx'

function fmtYMD(d){
  const y = d.getFullYear(); const m = String(d.getMonth()+1).padStart(2,'0'); const day = String(d.getDate()).padStart(2,'0')
  return `${y}-${m}-${day}`
}

export default function HealthMetrics(){
  const { user } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [metrics, setMetrics] = useState([]) // array of records
  const [date, setDate] = useState(()=> fmtYMD(new Date()))
  const [weight, setWeight] = useState('')
  const [unit, setUnit] = useState('kg')
  const [mood, setMood] = useState('Neutral')
  const [energy, setEnergy] = useState(5)
  const [saving, setSaving] = useState(false)
  const [page, setPage] = useState(1)

  const moods = ['Happy','Sad','Stressed','Relaxed','Energetic','Tired','Neutral']

  const fetchMetrics = async ()=>{
    setLoading(true); setError(null)
    try{
      const params = { user_id: user?.id }
      const resp = await api.get('/customer_dashboard/api/health_metrics/', { params })
      const data = Array.isArray(resp.data) ? resp.data : (resp.data?.results || [])
      setMetrics(data)
    }catch(e){ setError('Failed to load metrics') } finally { setLoading(false) }
  }

  useEffect(()=>{ if (user?.id) fetchMetrics() }, [user?.id])

  const latest = useMemo(()=> Array.isArray(metrics) && metrics.length ? metrics[0] : null, [metrics])

  const toKg = (w)=>{
    const n = Number(w)
    if (!n || Number.isNaN(n)) return null
    return unit === 'kg' ? n : Math.round((n/2.20462)*100)/100
  }

  const save = async ()=>{
    if (!user?.id){ setError('User missing'); return }
    setSaving(true); setError(null)
    try{
      const payload = { id: user.id, date_recorded: date, mood, energy_level: Number(energy) }
      const kg = toKg(weight)
      if (kg != null) payload.weight = kg
      const resp = await api.post('/customer_dashboard/api/health_metrics/', payload)
      if (resp.status === 200){
        await fetchMetrics()
        setWeight('');
      } else {
        setError(resp?.data?.error || 'Failed to save metrics')
      }
    }catch(e){ setError(e?.response?.data?.error || e?.message) } finally { setSaving(false) }
  }

  // Simple client-side pagination
  const pageSize = 10
  const totalPages = Math.max(1, Math.ceil((metrics?.length||0)/pageSize))
  const rows = (metrics||[]).slice((page-1)*pageSize, page*pageSize)

  return (
    <div>
      <div className="card" style={{marginBottom:'1rem'}}>
        <h2 style={{margin:'0 0 .4rem'}}>Health Metrics</h2>
        <div className="muted">Track your weight, mood, and energy. More insights coming soon.</div>
      </div>

      {/* Summary */}
      <div className="grid grid-3" style={{marginBottom:'1rem'}}>
        <div className="card">
          <div className="muted">Latest Weight</div>
          <div style={{fontWeight:800, fontSize:'1.3rem'}}>{latest?.weight ? `${latest.weight} kg` : '—'}</div>
        </div>
        <div className="card">
          <div className="muted">Current Mood</div>
          <div style={{fontWeight:800, fontSize:'1.3rem'}}>{latest?.mood || '—'}</div>
        </div>
        <div className="card">
          <div className="muted">Energy Level</div>
          <div style={{fontWeight:800, fontSize:'1.3rem'}}>{latest?.energy_level ?? '—'}</div>
        </div>
      </div>

      {/* Add/Update form */}
      <div className="card" style={{marginBottom:'1rem'}}>
        <div className="grid" style={{gap:'.6rem', gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))'}}>
          <div>
            <label className="label" htmlFor="hm-date">Date</label>
            <input id="hm-date" className="input" type="date" value={date} onChange={e=> setDate(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="hm-weight">Weight</label>
            <input id="hm-weight" className="input" type="number" placeholder="e.g., 72" value={weight} onChange={e=> setWeight(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="hm-unit">Unit</label>
            <select id="hm-unit" className="select" value={unit} onChange={e=> setUnit(e.target.value)}>
              <option value="kg">kg</option>
              <option value="lbs">lbs</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="hm-mood">Mood</label>
            <select id="hm-mood" className="select" value={mood} onChange={e=> setMood(e.target.value)}>
              {moods.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="hm-energy">Energy</label>
            <input id="hm-energy" className="input" type="number" min={1} max={10} value={energy} onChange={e=> setEnergy(e.target.value)} />
          </div>
        </div>
        <div style={{marginTop:'.6rem'}}>
          <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save Metrics'}</button>
        </div>
        {error && <div className="muted" style={{color:'#d9534f', marginTop:'.4rem'}}>{error}</div>}
      </div>

      {/* Table */}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Weight (kg)</th>
              <th>Mood</th>
              <th>Energy</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4}>Loading…</td></tr>
            ) : rows.length ? (
              rows.map((r, i) => (
                <tr key={`${r.id||i}-${r.date_recorded}`}>
                  <td>{r.date_recorded}</td>
                  <td>{r.weight ?? '—'}</td>
                  <td>{r.mood || '—'}</td>
                  <td>{r.energy_level ?? '—'}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan={4}>No data</td></tr>
            )}
          </tbody>
        </table>
        <div style={{display:'flex', gap:'.5rem', justifyContent:'space-between', marginTop:'.6rem'}}>
          <button className="btn btn-outline" disabled={page<=1} onClick={()=> setPage(p=>Math.max(1, p-1))}>Previous</button>
          <div className="muted">Page {page} of {totalPages}</div>
          <button className="btn btn-outline" disabled={page>=totalPages} onClick={()=> setPage(p=>Math.min(totalPages, p+1))}>Next</button>
        </div>
      </div>
    </div>
  )
}


