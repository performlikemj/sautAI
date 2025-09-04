import React, { useEffect, useMemo, useRef, useState } from 'react'

// A responsive carousel that shows multiple items at once.
// - Supports swipe/drag, keyboard arrows, autoplay, hover/touch pause
// - Adjusts slides per view based on container width
export default function MultiCarousel({
  items = [],
  ariaLabel = 'carousel',
  autoPlay = false,
  intervalMs = 5000,
  pauseOnHover = true,
  pauseOnTouch = true,
  loop = true
}){
  const containerRef = useRef(null)
  const [visibleCount, setVisibleCount] = useState(4)
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)

  const startXRef = useRef(0)
  const deltaXRef = useRef(0)
  const draggingRef = useRef(false)

  const maxIndex = Math.max(0, items.length - visibleCount)

  const clamp = (i)=> Math.max(0, Math.min(maxIndex, i))
  const go = (i)=> setIndex(clamp(i))
  const next = ()=> setIndex(i => {
    if (i >= maxIndex) return loop ? 0 : maxIndex
    return i + 1
  })
  const prev = ()=> setIndex(i => {
    if (i <= 0) return loop ? maxIndex : 0
    return i - 1
  })

  // Determine visibleCount based on container width
  useEffect(()=>{
    const el = containerRef.current
    if (!el) return
    const compute = (w)=>{
      if (w >= 1200) return 6
      if (w >= 1000) return 5
      if (w >= 820) return 4
      if (w >= 620) return 3
      if (w >= 420) return 2
      return 1
    }
    const ro = new ResizeObserver(entries => {
      for (const entry of entries){
        const w = entry.contentRect?.width || el.clientWidth || 0
        setVisibleCount(v => {
          const n = compute(w)
          return n !== v ? n : v
        })
      }
    })
    try{ ro.observe(el) }catch{}
    return ()=> ro.disconnect()
  }, [])

  // Keep index in bounds when visibleCount/items change
  useEffect(()=>{ setIndex(i => clamp(i)) }, [visibleCount, items.length])

  // Keyboard navigation
  useEffect(()=>{
    const onKey = (e)=>{
      if (e.key === 'ArrowRight') next()
      if (e.key === 'ArrowLeft') prev()
    }
    document.addEventListener('keydown', onKey)
    return ()=> document.removeEventListener('keydown', onKey)
  }, [maxIndex])

  // Drag/Swipe handlers
  const onStart = (x)=>{ draggingRef.current = true; startXRef.current = x; deltaXRef.current = 0; if (pauseOnTouch) setPaused(true) }
  const onMove = (x)=>{ if (!draggingRef.current) return; deltaXRef.current = x - startXRef.current }
  const onEnd = ()=>{
    if (!draggingRef.current) return
    const dx = deltaXRef.current
    draggingRef.current = false
    const el = containerRef.current
    const width = el ? el.clientWidth : 0
    const tileWidth = width / Math.max(1, visibleCount)
    const threshold = Math.max(40, tileWidth * 0.25)
    if (Math.abs(dx) > threshold){ if (dx < 0) next(); else prev() }
    deltaXRef.current = 0
    if (pauseOnTouch) setTimeout(()=> setPaused(false), 300)
  }

  const listeners = useMemo(()=>({
    onTouchStart: (e)=> onStart(e.touches[0].clientX),
    onTouchMove: (e)=> onMove(e.touches[0].clientX),
    onTouchEnd: onEnd,
    onMouseDown: (e)=>{ e.preventDefault(); onStart(e.clientX) },
    onMouseMove: (e)=> onMove(e.clientX),
    onMouseUp: onEnd,
    onMouseLeave: onEnd,
  }), [visibleCount])

  // Autoplay
  useEffect(()=>{
    if (!(autoPlay && items.length > visibleCount && !paused)) return
    const id = setInterval(()=> next(), Math.max(2200, intervalMs))
    return ()=> clearInterval(id)
  }, [autoPlay, intervalMs, items.length, visibleCount, paused, maxIndex])

  // Pause when tab hidden
  useEffect(()=>{
    const onVis = ()=>{ if (document.hidden) setPaused(true); else setPaused(false) }
    document.addEventListener('visibilitychange', onVis)
    return ()=> document.removeEventListener('visibilitychange', onVis)
  }, [])

  const pageCount = Math.max(1, maxIndex + 1)
  const translatePercent = (100 / Math.max(1, visibleCount)) * index
  const isCentered = items.length <= visibleCount

  return (
    <div aria-label={ariaLabel} role="region" className="multi-carousel">
      <div
        ref={containerRef}
        className="multi-viewport"
        onMouseEnter={()=> pauseOnHover && setPaused(true)}
        onMouseLeave={()=> pauseOnHover && setPaused(false)}
      >
        <div className="multi-window" {...listeners}>
          <div
            className={`multi-track ${isCentered ? 'center' : ''}`}
            style={{ transform: isCentered ? 'none' : `translateX(-${translatePercent}%)` }}
          >
            {items.map((node, i)=> (
              <div key={i} className="multi-item" style={{ flex:`0 0 ${100/Math.max(1, visibleCount)}%` }}>
                <div className="multi-item-inner">
                  {node}
                </div>
              </div>
            ))}
          </div>
        </div>
        {items.length > visibleCount && (
          <>
            <button aria-label="Previous" className="multi-nav prev" onClick={prev}>‹</button>
            <button aria-label="Next" className="multi-nav next" onClick={next}>›</button>
          </>
        )}
      </div>
      {items.length > visibleCount && (
        <div className="multi-dots">
          {Array.from({ length: pageCount }).map((_, i)=> (
            <button key={i} aria-label={`Go to slide ${i+1}`} className={`dot ${i===index? 'on':''}`} onClick={()=> go(i)} />
          ))}
        </div>
      )}
    </div>
  )
}


