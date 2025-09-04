import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../context/AuthContext.jsx'
import { countryNameFromCode } from '../utils/geo.js'

function renderAreas(areas){
  if (!Array.isArray(areas) || areas.length === 0) return ''
  const names = areas
    .map(p => (p?.postal_code || p?.postalcode || p?.code || p?.name || ''))
    .filter(Boolean)
  return names.join(', ')
}

function formatAreasDisplay(areas){
  const codes = renderAreas(areas)
  if (!codes) return ''
  return `(serves ${codes})`
}

function extractCityCountry(chef, authUser){
  // Mirror the logic used on the PublicChef profile page
  
  const isSelf = authUser && (chef?.user?.id === authUser?.id || chef?.user?.username === authUser?.username)
  const sp = Array.isArray(chef?.serving_postalcodes) ? chef.serving_postalcodes : []
  const spCity = sp.map(p=> (p?.city||'').trim()).find(Boolean) || ''
  const spCountryRaw = sp.map(p=> (p?.country?.code || p?.country?.name || p?.country || p?.country_code || '')).find(v=> String(v||'').trim()) || ''
  const city = String(
    chef?.city || chef?.location_city || chef?.location?.city || chef?.address?.city || chef?.user?.address?.city || spCity ||
    (isSelf ? (authUser?.address?.city || '') : '')
  ).trim()
  let countryRaw = (
    chef?.country || chef?.location_country || chef?.location?.country || chef?.address?.country || chef?.user?.address?.country || spCountryRaw ||
    chef?.country_code || chef?.countryCode || chef?.location?.country_code || chef?.address?.country_code || chef?.user?.address?.country_code ||
    (isSelf ? (authUser?.address?.country || authUser?.address?.country_code || '') : '')
  )
  countryRaw = String(countryRaw || '').trim()
  const country = countryRaw.length === 2 ? countryNameFromCode(countryRaw) : countryRaw
  if (city && country) return `${city}, ${country}`
  return city || country || ''
}

export default function ChefsDirectory(){
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [chefs, setChefs] = useState([])
  const [error, setError] = useState(null)
  const [onlyServesMe, setOnlyServesMe] = useState(false)
  const [query, setQuery] = useState('')
  
  const [userDetailsById, setUserDetailsById] = useState({})

  const mePostal = user?.postal_code || user?.address?.postalcode || ''

  const filtered = useMemo(()=>{
    const q = (query||'').toLowerCase()
    return chefs.filter(c => {
      const name = c?.user?.username?.toLowerCase?.() || ''
      const areas = renderAreas(c?.serving_postalcodes)
      const matchQ = !q || name.includes(q) || areas.toLowerCase().includes(q)
      if (!matchQ) return false
      if (onlyServesMe && mePostal){
        const tokens = areas.split(/\s*,\s*/)
        return tokens.includes(mePostal)
      }
      return true
    })
  }, [chefs, query, onlyServesMe, mePostal])

  useEffect(()=>{ document.title = 'sautai — Chefs' }, [])

  useEffect(()=>{
    let mounted = true
    setLoading(true)
    setError(null)
    
    api.get('/chefs/api/public/', { skipUserId: true })
      .then(async res => { 
        const list = Array.isArray(res.data)? res.data : (res.data?.results||[])
        
        if (!mounted) return
        setChefs(list)
        const ids = Array.from(new Set(list.map(c => c?.user?.id).filter(Boolean)))
        if (ids.length){
          try{
            const entries = await Promise.all(ids.map(async uid => {
              try{
                const r = await api.get('/auth/api/user_details/', { params: { user_id: uid }, skipUserId: true })
                return [uid, r?.data||null]
              }catch{ return [uid, null] }
            }))
            if (!mounted) return
            setUserDetailsById(Object.fromEntries(entries))
          }catch{}
        }
      })
      .catch((e)=> { if (mounted) setError('Unable to load chefs.') })
      .finally(()=> { if (mounted) setLoading(false) })
    return ()=>{ mounted = false }
  }, [])

  return (
    <div>
      <h2>Chefs</h2>
      <div className="card" style={{display:'flex', gap:'.5rem', alignItems:'center'}}>
        <input className="input" placeholder="Search by name or area…" value={query} onChange={e=> setQuery(e.target.value)} />
        {mePostal && (
          <label style={{display:'inline-flex', alignItems:'center', gap:'.35rem'}}>
            <input type="checkbox" checked={onlyServesMe} onChange={e=> setOnlyServesMe(e.target.checked)} />
            <span>Serves my area ({mePostal})</span>
          </label>
        )}
      </div>

      {loading && <div className="muted">Loading…</div>}
      {!loading && error && <div className="card" style={{borderColor:'#e66'}}>{error}</div>}
      {!loading && !error && (
        <div className="grid grid-3">
          {filtered.map(c => (
            <Link key={c.id} to={`/c/${encodeURIComponent(c?.user?.username || c.id)}`} className="card" style={{textDecoration:'none'}}>
              <div style={{display:'flex', alignItems:'center', gap:'.6rem'}}>
                {c.profile_pic_url && <img src={c.profile_pic_url} alt={c?.user?.username||'Chef'} style={{height:48, width:48, borderRadius:'999px', objectFit:'cover', border:'1px solid var(--border)'}} />}
                <div>
                  <div style={{fontWeight:800, color:'inherit'}}>{c?.user?.username || 'Chef'}</div>
                  <div className="muted" style={{fontSize:'.9rem'}}>
                    {(()=>{
                      const loc = extractCityCountry({
                        ...c,
                        user: { ...(c?.user||{}), address: (userDetailsById?.[c?.user?.id]?.address || c?.user?.address) }
                      }, user)
                      
                      const areas = formatAreasDisplay(c.serving_postalcodes)
                      if (loc && areas) return <><span>{loc} </span><span>{areas}</span></>
                      if (loc) return loc
                      const codes = renderAreas(c.serving_postalcodes)
                      return codes ? `Serves ${codes}` : '—'
                    })()}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}


