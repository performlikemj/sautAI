import React, { useEffect, useRef, useState } from 'react'

export default function Carousel({ items = [], ariaLabel = 'carousel', autoPlay = false, intervalMs = 5000, pauseOnHover = true, pauseOnTouch = true }){
  const [index, setIndex] = useState(0)
  const trackRef = useRef(null)
  const startXRef = useRef(0)
  const deltaXRef = useRef(0)
  const isDraggingRef = useRef(false)
  const [paused, setPaused] = useState(false)

  const clamp = (v)=> Math.max(0, Math.min(items.length - 1, v))
  const go = (i)=> setIndex(clamp(i))
  const next = ()=> go(index + 1)
  const prev = ()=> go(index - 1)

  useEffect(()=>{
    const onKey = (e)=>{
      if (e.key === 'ArrowRight') next()
      if (e.key === 'ArrowLeft') prev()
    }
    document.addEventListener('keydown', onKey)
    return ()=> document.removeEventListener('keydown', onKey)
  }, [index])

  const onTouchStart = (x)=>{ isDraggingRef.current = true; startXRef.current = x; deltaXRef.current = 0; if (pauseOnTouch) setPaused(true) }
  const onTouchMove = (x)=>{ if (!isDraggingRef.current) return; deltaXRef.current = x - startXRef.current }
  const onTouchEnd = ()=>{
    if (!isDraggingRef.current) return
    const dx = deltaXRef.current
    isDraggingRef.current = false
    if (Math.abs(dx) > 50){ if (dx < 0) next(); else prev() }
    deltaXRef.current = 0
    if (pauseOnTouch) setTimeout(()=> setPaused(false), 300)
  }

  const listeners = {
    onTouchStart: (e)=> onTouchStart(e.touches[0].clientX),
    onTouchMove: (e)=> onTouchMove(e.touches[0].clientX),
    onTouchEnd: onTouchEnd,
    onMouseDown: (e)=>{ e.preventDefault(); onTouchStart(e.clientX) },
    onMouseMove: (e)=> onTouchMove(e.clientX),
    onMouseUp: onTouchEnd,
    onMouseLeave: onTouchEnd,
  }

  useEffect(()=>{
    if (!(autoPlay && items.length > 1 && !paused)) return
    const id = setInterval(()=> setIndex(i => (i + 1) % items.length), Math.max(2000, intervalMs))
    return ()=> clearInterval(id)
  }, [autoPlay, intervalMs, items.length, paused])

  // When items change length, clamp index to avoid getting stuck beyond bounds
  useEffect(()=>{
    setIndex(i => clamp(i))
  }, [items.length])

  useEffect(()=>{
    const onVis = ()=>{ if (document.hidden) setPaused(true); else setPaused(false) }
    document.addEventListener('visibilitychange', onVis)
    return ()=> document.removeEventListener('visibilitychange', onVis)
  }, [])

  return (
    <div aria-label={ariaLabel} role="region">
      <div style={{ position:'relative' }} onMouseEnter={()=> pauseOnHover && setPaused(true)} onMouseLeave={()=> pauseOnHover && setPaused(false)}>
        <div
          ref={trackRef}
          {...listeners}
          style={{
            overflow:'hidden',
            borderRadius: 8,
            userSelect:'none'
          }}
        >
          <div
            style={{
              display:'flex',
              transition:'transform 280ms ease',
              transform:`translateX(-${index * 100}%)`
            }}
          >
            {items.map((node, i)=> (
              <div key={i} style={{ flex:'0 0 100%', padding:'.25rem' }}>
                {node}
              </div>
            ))}
          </div>
        </div>
        {items.length > 1 && (
          <>
            <button
              aria-label="Previous"
              className="icon-btn"
              onClick={prev}
              style={{ position:'absolute', top:'50%', left:6, transform:'translateY(-50%)', background:'rgba(255,255,255,0.9)' }}
            >
              ←
            </button>
            <button
              aria-label="Next"
              className="icon-btn"
              onClick={next}
              style={{ position:'absolute', top:'50%', right:6, transform:'translateY(-50%)', background:'rgba(255,255,255,0.9)' }}
            >
              →
            </button>
          </>
        )}
      </div>
      {items.length > 1 && (
        <div style={{ display:'flex', justifyContent:'center', marginTop:'.35rem', gap:6 }}>
          {items.map((_, i)=> (
            <button
              key={i}
              aria-label={`Go to slide ${i+1}`}
              className="dot"
              onClick={()=> go(i)}
              style={{
                width:8, height:8, borderRadius:'50%', border:'1px solid var(--border)',
                backgroundColor: i===index ? 'var(--text)' : 'transparent'
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}


