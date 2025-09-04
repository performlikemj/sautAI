import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'

function BurgerIcon({ open=false }){
  const stroke = 'currentColor'
  return (
    <svg width="22" height="18" viewBox="0 0 22 18" aria-hidden focusable="false">
      <g stroke={stroke} strokeWidth="2" strokeLinecap="round">
        <line className="line line1" x1="2" y1="3" x2="20" y2="3" />
        <line className="line line2" x1="2" y1="9" x2="20" y2="9" />
        <line className="line line3" x1="2" y1="15" x2="20" y2="15" />
      </g>
    </svg>
  )
}

export default function NavBar(){
  const { user, logout, switchRole } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const nav = useNavigate()
  const [switching, setSwitching] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [brandSrc, setBrandSrc] = useState('/sautai_logo_web.png')
  const onBrandError = ()=> setBrandSrc('/sautai_logo_transparent_800.png')
  const isAuthed = Boolean(user)
  const inChef = user?.current_role === 'chef'

  const doLogout = () => {
    logout()
    setMenuOpen(false)
    nav('/login')
  }

  const closeMenu = () => { setMenuOpen(false); setMoreOpen(false) }

  const selectRole = async (target)=>{
    const access = localStorage.getItem('accessToken')
    const refresh = localStorage.getItem('refreshToken')
    try{
      setSwitching(true)
      await switchRole(target)
      if (target === 'chef') nav('/chefs/dashboard')
      else nav('/meal-plans')
    }catch(e){
      const status = e?.response?.status
      const msg = e?.message || 'Failed to switch role'
      console.error('[NavBar] switchRole() failed', { status, url: e?.config?.url, err: e })
      // Non-blocking slide-in toast via window event (handled by page-level overlays)
      try{
        const ev = new CustomEvent('global-toast', { detail: { text: msg, tone: 'error' } })
        window.dispatchEvent(ev)
      }catch{}
    }finally{
      setSwitching(false)
      setMenuOpen(false)
    }
  }

  return (
    <div className="navbar">
      <div className="navbar-inner container">
        <div className="brand">
          <Link to="/" onClick={closeMenu} style={{display:'inline-flex', alignItems:'center', gap:'.5rem', textDecoration:'none'}}>
            <img src={brandSrc} onError={onBrandError} alt="sautai" style={{height:32, width:'auto', borderRadius:6}} />
            <span style={{color:'inherit', textDecoration:'none'}}>sautai</span>
          </Link>
        </div>

        <button
          className={`btn btn-outline menu-toggle${menuOpen ? ' open' : ''}`}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          aria-controls="site-menu"
          onClick={()=>setMenuOpen(v=>!v)}
          title="Menu"
          type="button"
        >
          <BurgerIcon open={menuOpen} />
        </button>

        <div id="site-menu" className={"nav-links" + (menuOpen ? " open" : "") }>
          <Link to="/" onClick={closeMenu} className="btn btn-outline">Home</Link>
          {(!inChef && isAuthed) && <Link to="/meal-plans" onClick={closeMenu} className="btn btn-outline">Meal Plans</Link>}
          {(inChef && isAuthed) && <Link to="/chefs/dashboard" onClick={closeMenu} className="btn btn-outline">Chef Dashboard</Link>}
          {!isAuthed && (
            <Link to="/chefs" onClick={closeMenu} className="btn btn-outline">Chefs</Link>
          )}
          {isAuthed && (
            (()=>{
              const items = []
              if (!inChef){ items.push({ to:'/chat', label:'Chat' }); items.push({ to:'/health', label:'Health' }) }
              items.push({ to:'/chefs', label:'Chefs' })
              items.push({ to:'/profile', label:'Profile' })
              if (items.length === 0) return null
              return (
                <div className="menu-wrap">
                  <button type="button" className="btn btn-outline" aria-haspopup="menu" aria-expanded={moreOpen} onClick={()=> setMoreOpen(v=>!v)}>More ▾</button>
                  {moreOpen && (
                    <div className="menu-pop" role="menu" aria-label="More">
                      {items.map(i => (
                        <Link key={i.to} to={i.to} onClick={closeMenu} className="menu-item" role="menuitem">{i.label}</Link>
                      ))}
                    </div>
                  )}
                </div>
              )
            })()
          )}
          {/* History removed */}
          {user?.is_chef && (
            <div className="role-toggle" role="group" aria-label="Select role">
              <button
                type="button"
                className={`seg ${user?.current_role !== 'chef' ? 'active' : ''}`}
                aria-pressed={user?.current_role !== 'chef'}
                disabled={switching}
                title="Use app as Customer"
                onClick={()=>selectRole('customer')}
              >
                {switching && user?.current_role === 'chef' ? '…' : '🥣 Customer'}
              </button>
              <button
                type="button"
                className={`seg ${user?.current_role === 'chef' ? 'active' : ''}`}
                aria-pressed={user?.current_role === 'chef'}
                disabled={switching}
                title="Use app as Chef"
                onClick={()=>selectRole('chef')}
              >
                {switching && user?.current_role !== 'chef' ? '…' : '👨‍🍳 Chef'}
              </button>
            </div>
          )}
          {!user && <Link to="/login" onClick={closeMenu} className="btn btn-primary">Login</Link>}
          {!user && <Link to="/register" onClick={closeMenu} className="btn btn-outline">Register</Link>}
          {user && <button onClick={doLogout} className="btn btn-primary">Logout</button>}
          <button
            type="button"
            className="btn btn-outline"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
            aria-label={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
          >
            {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
          </button>
        </div>
      </div>
    </div>
  )
}
