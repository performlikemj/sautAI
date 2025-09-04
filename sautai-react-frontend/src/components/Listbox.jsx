import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

export default function Listbox({
  options,
  value,
  onChange,
  placeholder = 'Select…',
  filterable = true,
  loading = false,
  disabled = false,
  getKey,
  renderItem,
  className = '',
  portal = true
}){
  const wrapRef = useRef(null)
  const listRef = useRef(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0 })

  const normalized = useMemo(()=>{
    const map = (opt)=>{
      if (typeof opt === 'string') return { key: opt, value: opt, label: opt }
      const key = getKey ? getKey(opt) : (opt.key ?? opt.value ?? opt.label)
      return { key, ...opt }
    }
    const list = (options||[]).map(map)
    if (!query) return list
    const q = query.toLowerCase()
    return list.filter(o => String(o.label||'').toLowerCase().includes(q) || String(o.subLabel||'').toLowerCase().includes(q))
  }, [options, query, getKey])

  const selected = useMemo(()=> normalized.find(o => String(o.value) === String(value)) || null, [normalized, value])

  useEffect(()=>{
    const onDoc = (e)=>{
      if (!open) return
      const withinTrigger = wrapRef.current && wrapRef.current.contains(e.target)
      const withinPopover = listRef.current && listRef.current.contains(e.target)
      if (withinTrigger || withinPopover) return
      setOpen(false)
    }
    document.addEventListener('mousedown', onDoc, true)
    return ()=> document.removeEventListener('mousedown', onDoc, true)
  }, [open])

  useEffect(()=>{ if (open) setTimeout(()=> listRef.current?.focus(), 0) }, [open])

  // Position popover to body to avoid clipping by overflow containers
  useEffect(()=>{
    if (!open || !portal) return
    const calc = ()=>{
      if (!wrapRef.current) return
      const r = wrapRef.current.getBoundingClientRect()
      const left = Math.max(8, Math.min(r.left, window.innerWidth - r.width - 8))
      const below = r.bottom + 6
      const spaceBelow = window.innerHeight - below
      const spaceAbove = r.top - 8
      // Prefer below; if not enough space, open above
      const openAbove = spaceBelow < 220 && spaceAbove > spaceBelow
      const top = openAbove ? Math.max(8, r.top - Math.min(420, spaceAbove) - 6) : below
      setPos({ top, left, width: r.width })
    }
    calc()
    window.addEventListener('resize', calc)
    window.addEventListener('scroll', calc, true)
    return ()=>{ window.removeEventListener('resize', calc); window.removeEventListener('scroll', calc, true) }
  }, [open, portal])

  const choose = (val)=>{ if (disabled) return; onChange && onChange(val); setOpen(false) }

  const onKeyDown = (e)=>{
    if (!open){
      if (['ArrowDown','Enter',' '].includes(e.key)){ e.preventDefault(); setOpen(true) }
      return
    }
    if (e.key === 'Escape'){ e.preventDefault(); setOpen(false); return }
    if (e.key === 'ArrowDown'){ e.preventDefault(); setActiveIndex(i=> Math.min(i+1, Math.max(0, normalized.length-1))); return }
    if (e.key === 'ArrowUp'){ e.preventDefault(); setActiveIndex(i=> Math.max(i-1, 0)); return }
    if (e.key === 'Home'){ e.preventDefault(); setActiveIndex(0); return }
    if (e.key === 'End'){ e.preventDefault(); setActiveIndex(Math.max(0, normalized.length-1)); return }
    if (e.key === 'Enter'){ e.preventDefault(); const o = normalized[activeIndex]; if (o) choose(o.value); return }
  }

  return (
    <div ref={wrapRef} className={`listbox-wrap ${className}`.trim()}>
      <button type="button" className={`listbox-field${disabled?' disabled':''}`} aria-haspopup="listbox" aria-expanded={open} onClick={()=> !disabled && setOpen(o=>!o)} onKeyDown={onKeyDown}>
        <span className={`listbox-field-text ${selected?'':'placeholder'}`}>{selected ? (selected.display || selected.label) : placeholder}</span>
        <span className="caret" aria-hidden>▾</span>
      </button>
      {open && (!portal ? (
        <div className="listbox-pop" role="listbox" aria-activedescendant={normalized[activeIndex]?.key} tabIndex={-1} ref={listRef} onKeyDown={onKeyDown}>
          {filterable && (
            <input className="input listbox-search" placeholder="Search…" value={query} onChange={e=> { setQuery(e.target.value); setActiveIndex(0) }} autoFocus />
          )}
          <div className="listbox-list">
            {loading && <div className="muted" style={{padding:'.4rem .5rem'}}>Loading…</div>}
            {!loading && normalized.length===0 && <div className="muted" style={{padding:'.4rem .5rem'}}>No results</div>}
            {!loading && normalized.map((o, i) => (
              <div
                id={String(o.key)}
                key={String(o.key)}
                role="option"
                aria-selected={String(o.value) === String(value)}
                className={`listbox-option ${i===activeIndex?'active':''} ${String(o.value)===String(value)?'sel':''}`}
                onMouseEnter={()=> setActiveIndex(i)}
                onClick={()=> choose(o.value)}
              >
                {renderItem ? renderItem(o) : (
                  <div className="listbox-option-inner">
                    <div className="title">{o.label}</div>
                    {o.subLabel && <div className="sub muted">{o.subLabel}</div>}
                    {Array.isArray(o.chips) && o.chips.length>0 && (
                      <div className="chips">
                        {o.chips.map((c, idx)=> <span key={idx} className="chip small">{c}</span>)}
                      </div>
                    )}
                  </div>
                )}
                {String(o.value)===String(value) && <span className="check" aria-hidden>✓</span>}
              </div>
            ))}
          </div>
        </div>
      ) : createPortal(
        <div className="listbox-pop" role="listbox" aria-activedescendant={normalized[activeIndex]?.key} tabIndex={-1} ref={listRef} onKeyDown={onKeyDown}
          style={{ position:'fixed', top: pos.top, left: pos.left, width: pos.width, zIndex: 1000 }}
        >
          {filterable && (
            <input className="input listbox-search" placeholder="Search…" value={query} onChange={e=> { setQuery(e.target.value); setActiveIndex(0) }} autoFocus />
          )}
          <div className="listbox-list">
            {loading && <div className="muted" style={{padding:'.4rem .5rem'}}>Loading…</div>}
            {!loading && normalized.length===0 && <div className="muted" style={{padding:'.4rem .5rem'}}>No results</div>}
            {!loading && normalized.map((o, i) => (
              <div
                id={String(o.key)}
                key={String(o.key)}
                role="option"
                aria-selected={String(o.value) === String(value)}
                className={`listbox-option ${i===activeIndex?'active':''} ${String(o.value)===String(value)?'sel':''}`}
                onMouseEnter={()=> setActiveIndex(i)}
                onClick={()=> choose(o.value)}
              >
                {renderItem ? renderItem(o) : (
                  <div className="listbox-option-inner">
                    <div className="title">{o.label}</div>
                    {o.subLabel && <div className="sub muted">{o.subLabel}</div>}
                    {Array.isArray(o.chips) && o.chips.length>0 && (
                      <div className="chips">
                        {o.chips.map((c, idx)=> <span key={idx} className="chip small">{c}</span>)}
                      </div>
                    )}
                  </div>
                )}
                {String(o.value)===String(value) && <span className="check" aria-hidden>✓</span>}
              </div>
            ))}
          </div>
        </div>,
        document.body
      ))}
    </div>
  )
}


