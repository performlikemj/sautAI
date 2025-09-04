import React, { useEffect, useRef, useState } from 'react'

// Lightweight Leaflet loader (no build-time dep if user doesn't open)
function useLeaflet(){
  const [L, setL] = useState(null)
  useEffect(()=>{
    let cancelled = false
    ;(async ()=>{
      try{
        if (window.L){ setL(window.L); return }
        await Promise.all([
          import('leaflet/dist/leaflet.css'),
          import('leaflet')
        ]).then(([_, lib])=>{ if (!cancelled){ window.L = lib.default || lib; setL(window.L) } })
      }catch{}
    })()
    return ()=>{ cancelled = true }
  }, [])
  return L
}

export default function MapPanel({ open, onClose, countryCode, postalCodes = [], city }){
  const L = useLeaflet()
  const mapRef = useRef(null)
  const mapObj = useRef(null)
  const [error, setError] = useState(null)

  useEffect(()=>{
    if (!open || !L) return
    if (mapObj.current){ mapObj.current.invalidateSize(); return }
    const map = L.map(mapRef.current).setView([20,0], 2)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(map)
    mapObj.current = map
  }, [open, L])

  // Cleanly destroy the map when panel closes so reopening works reliably
  useEffect(()=>{
    if (!open && mapObj.current){
      try{ mapObj.current.remove() }catch{}
      mapObj.current = null
    }
  }, [open])

  useEffect(()=>{
    if (!open || !L || !mapObj.current) return
    const map = mapObj.current
    setError(null)

    const overlays = []
    const fit = []

    const addBoundary = (geojson)=>{
      try{
        const layer = L.geoJSON(geojson, { style: { color:'#3E8F3E', weight:2, fillColor:'#5cb85c', fillOpacity:.15 } }).addTo(map)
        overlays.push(layer)
        try{ fit.push(layer.getBounds()) }catch{}
      }catch{}
    }

    const cc = String(countryCode||'').toLowerCase()

    const fetchNominatim = async (q)=>{
      const url = `https://nominatim.openstreetmap.org/search?format=json&countrycodes=${encodeURIComponent(cc)}&postalcode=${encodeURIComponent(q)}&polygon_geojson=1&limit=1`
      const r = await fetch(url, { headers:{ 'Accept-Language':'en', 'User-Agent':'sautai/1.0 (demo)' } })
      if (!r.ok) throw new Error('geo lookup failed')
      return r.json()
    }

    const fetchNominatimFallbackQ = async (q)=>{
      const url = `https://nominatim.openstreetmap.org/search?format=json&countrycodes=${encodeURIComponent(cc)}&q=${encodeURIComponent(q)}&polygon_geojson=1&limit=1`
      const r = await fetch(url, { headers:{ 'Accept-Language':'en', 'User-Agent':'sautai/1.0 (demo)' } })
      if (!r.ok) throw new Error('geo lookup failed')
      return r.json()
    }

    const postalVariants = (code)=>{
      const c = String(code||'').trim()
      const v = new Set([c])
      if (/^\d{7}$/.test(c) && cc === 'jp'){ v.add(`${c.slice(0,3)}-${c.slice(3)}`) }
      if (/^\d{3}-\d{4}$/.test(c) && cc === 'jp'){ v.add(c.replace(/-/g,'')) }
      return Array.from(v).filter(Boolean)
    }

    const fetchOverpassPolygon = async (pc)=>{
      try{
        const osmtogeojson = (await import('osmtogeojson')).default
        const q = `
          [out:json][timeout:25];
          area["ISO3166-1"="${cc.toUpperCase()}"]->.searchArea;
          (
            relation["boundary"~"postal_code|administrative"]["postal_code"="${pc}"](area.searchArea);
            relation["boundary"~"postal_code|administrative"]["addr:postcode"="${pc}"](area.searchArea);
            way["boundary"~"postal_code|administrative"]["postal_code"="${pc}"](area.searchArea);
            way["boundary"~"postal_code|administrative"]["addr:postcode"="${pc}"](area.searchArea);
          );
          out body; >; out skel qt;`
        const r = await fetch('https://overpass-api.de/api/interpreter', { method:'POST', body: q, headers:{ 'Content-Type':'text/plain' } })
        if (!r.ok) return null
        const data = await r.json()
        const gj = osmtogeojson(data)
        if (gj && gj.features && gj.features.length){ return gj }
        return null
      }catch{ return null }
    }

    const run = async ()=>{
      try{
        // Clear old
        overlays.forEach(o=> map.removeLayer(o))
        // If no postals, try city
        if (!postalCodes || postalCodes.length===0){
          if (!city){ setError('No service areas to show'); return }
          const url = `https://nominatim.openstreetmap.org/search?format=json&city=${encodeURIComponent(city)}&countrycodes=${encodeURIComponent(countryCode||'')}&polygon_geojson=1&limit=1`
          const r = await fetch(url)
          const data = await r.json()
          if (Array.isArray(data) && data[0]?.geojson){ addBoundary(data[0].geojson); map.fitBounds(L.geoJSON(data[0].geojson).getBounds()) }
          return
        }
        let polygonCount = 0
        for (const raw of postalCodes){
          const variants = postalVariants(raw)
          let got = false
          for (const pc of variants){
            try{
              const data = await fetchNominatim(pc)
              const gj = Array.isArray(data) ? data[0]?.geojson : null
              if (gj && gj.type && gj.type !== 'Point'){ addBoundary(gj); polygonCount++; got = true; break }
              const alt = await fetchNominatimFallbackQ(`${pc} ${cc}`)
              const gj2 = Array.isArray(alt) ? alt[0]?.geojson : null
              if (gj2 && gj2.type && gj2.type !== 'Point'){ addBoundary(gj2); polygonCount++; got = true; break }
              const over = await fetchOverpassPolygon(pc)
              if (over && over.features && over.features.length){ addBoundary(over); polygonCount++; got = true; break }
            }catch{}
          }
          if (!got){ /* keep scanning; but do not drop a point */ }
        }
        if (fit.length){
          try{
            const bounds = fit.reduce((a,b)=> a.extend(b), fit[0])
            map.fitBounds(bounds, { padding:[12,12] })
          }catch{}
        } else {
          // No polygons found; try to approximate a boundary from multiple centroid points (convex hull)
          let anyCircle = false
          const pts = []
          for (const raw of postalCodes){
            const variants = postalVariants(raw)
            for (const pc of variants){
              try{
                const data = await fetchNominatim(pc)
                const p = Array.isArray(data) && data[0]
                if (p && p.lat && p.lon){
                  pts.push([parseFloat(p.lon), parseFloat(p.lat)])
                  anyCircle = true; break
                }
                const alt = await fetchNominatimFallbackQ(`${pc} ${cc}`)
                const p2 = Array.isArray(alt) && alt[0]
                if (p2 && p2.lat && p2.lon){
                  pts.push([parseFloat(p2.lon), parseFloat(p2.lat)])
                  anyCircle = true; break
                }
              }catch{}
            }
          }
          if (anyCircle && pts.length){
            try{
              const turf = await import('@turf/convex')
              const helpers = await import('@turf/helpers')
              const fc = helpers.featureCollection(pts.map(([x,y])=> helpers.point([x,y])))
              const hull = turf.default(fc)
              if (hull){ addBoundary(hull); map.fitBounds(L.geoJSON(hull).getBounds(), { padding:[12,12] }); setError(null); return }
            }catch{}
            // fallback to one combined circle if hull failed
            try{
              const avg = pts.reduce((a,[x,y])=>[a[0]+x, a[1]+y],[0,0]).map(v=> v/pts.length)
              const c = L.circle([avg[1], avg[0]], { radius: 1400, color:'#3E8F3E', fillColor:'#5cb85c', fillOpacity:.18 }).addTo(map)
              overlays.push(c); try{ map.fitBounds(c.getBounds(), { padding:[12,12] }) }catch{}
              setError(null); return
            }catch{}
          }

          // Still nothing — fallback to city boundary or centroid
          if (city){
            try{
              const url = `https://nominatim.openstreetmap.org/search?format=json&city=${encodeURIComponent(city)}&countrycodes=${encodeURIComponent(cc)}&polygon_geojson=1&limit=1`
              const r = await fetch(url)
              const data = await r.json()
              if (Array.isArray(data) && data[0]?.geojson && data[0].geojson.type !== 'Point'){
                addBoundary(data[0].geojson)
                map.fitBounds(L.geoJSON(data[0].geojson).getBounds())
              } else if (Array.isArray(data) && data[0]?.lat && data[0]?.lon){
                const c = L.circle([parseFloat(data[0].lat), parseFloat(data[0].lon)], { radius: 2000, color:'#3E8F3E', fillColor:'#5cb85c', fillOpacity:.18 }).addTo(map)
                overlays.push(c); try{ map.fitBounds(c.getBounds(), { padding:[12,12] }) }catch{}
                setError(null)
              } else {
                setError('Boundary not available for the provided postal codes.')
              }
            }catch{ setError('Boundary not available for the provided postal codes.') }
          } else {
            setError('Boundary not available for the provided postal codes.')
          }
        }
      }catch(e){ setError('Unable to load map for this area.') }
    }
    run()
    return ()=>{ overlays.forEach(o=> map.removeLayer(o)) }
  }, [open, L, countryCode, postalCodes, city])

  if (!open) return null
  return (
    <>
      <div className="right-panel-overlay" onClick={onClose} />
      <aside className="right-panel" role="dialog" aria-label="Service area map">
        <div className="right-panel-head">
          <div className="slot-title">Approximate Service Area</div>
          <button className="icon-btn" onClick={onClose}>✕</button>
        </div>
        <div className="right-panel-body" style={{padding:0}}>
          {error && <div className="card" style={{margin:'1rem'}}>{error}</div>}
          <div ref={mapRef} style={{height:'70vh', minHeight:420, width:'100%'}} />
          <div style={{padding:'0.75rem'}} className="muted">Data © OpenStreetMap contributors • Boundaries from Nominatim</div>
        </div>
      </aside>
    </>
  )
}


