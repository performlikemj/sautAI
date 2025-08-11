import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

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
  const nav = useNavigate()
  const [switching, setSwitching] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  const doLogout = () => {
    logout()
    setMenuOpen(false)
    nav('/login')
  }

  const closeMenu = () => setMenuOpen(false)

  const selectRole = async (target)=>{
    if (!user) { console.warn('[NavBar] selectRole called but no user'); return }
    if (user.current_role === target) { console.log('[NavBar] selectRole noop (already in role)', target); return }
    const access = localStorage.getItem('accessToken')
    const refresh = localStorage.getItem('refreshToken')
    console.log('[NavBar] selectRole →', {
      current: user?.current_role, target,
      hasAccess: Boolean(access), hasRefresh: Boolean(refresh),
      accessLen: access?.length || 0, refreshLen: refresh?.length || 0
    })
    try{
      setSwitching(true)
      console.log('[NavBar] switchRole() starting')
      await switchRole(target)
      console.log('[NavBar] switchRole() success; navigating…')
      if (target === 'chef') nav('/chefs/dashboard')
      else nav('/meal-plans')
    }catch(e){
      const status = e?.response?.status
      console.error('[NavBar] switchRole() failed', { status, url: e?.config?.url, err: e })
      alert('Failed to switch role')
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
            <img src="/sautai_logo.PNG" alt="sautAI" style={{height:24, width:'auto', borderRadius:6}} />
            <span style={{color:'inherit', textDecoration:'none'}}>sautAI</span>
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
          {user?.current_role !== 'chef' && user && <Link to="/meal-plans" onClick={closeMenu} className="btn btn-outline">Meal Plans</Link>}
          {user?.current_role !== 'chef' && user && <Link to="/chat" onClick={closeMenu} className="btn btn-outline">Chat</Link>}
          {user?.current_role !== 'chef' && user && <Link to="/history" onClick={closeMenu} className="btn btn-outline">History</Link>}
          {user && <Link to="/profile" onClick={closeMenu} className="btn btn-outline">Profile</Link>}
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
                🥣 Customer
              </button>
              <button
                type="button"
                className={`seg ${user?.current_role === 'chef' ? 'active' : ''}`}
                aria-pressed={user?.current_role === 'chef'}
                disabled={switching}
                title="Use app as Chef"
                onClick={()=>selectRole('chef')}
              >
                👨‍🍳 Chef
              </button>
            </div>
          )}
          {!user && <Link to="/login" onClick={closeMenu} className="btn btn-primary">Login</Link>}
          {!user && <Link to="/register" onClick={closeMenu} className="btn btn-outline">Register</Link>}
          {user && <button onClick={doLogout} className="btn btn-primary">Logout</button>}
        </div>
      </div>
    </div>
  )
}
