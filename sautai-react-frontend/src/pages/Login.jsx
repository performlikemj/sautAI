import React, { useState } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../api'

export default function Login(){
  const { login } = useAuth()
  const nav = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showForgot, setShowForgot] = useState(false)
  const [email, setEmail] = useState('')
  const [forgotMsg, setForgotMsg] = useState('')
  const [forgotError, setForgotError] = useState('')
  const [forgotLoading, setForgotLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try{
      await login(username, password)
      try{
        const sp = new URLSearchParams(location.search)
        const next = sp.get('next')
        if (next && next.startsWith('/')){
          nav(decodeURIComponent(next), { replace: true })
        } else {
          nav('/meal-plans', { replace: true })
        }
      }catch{
        nav('/meal-plans', { replace: true })
      }
    }catch(err){
      setError('Invalid credentials or server error.')
    }finally{
      setLoading(false)
    }
  }

  const requestReset = async (e) => {
    e.preventDefault()
    setForgotError('')
    setForgotMsg('')
    if (!email){ setForgotError('Please enter your email address.'); return }
    setForgotLoading(true)
    try{
      const res = await api.post('/auth/api/password_reset_request/', { email }, { skipUserId: true })
      if (res.status === 200){
        setForgotMsg("Reset password link sent. Please check your email (and spam).")
      } else {
        setForgotError('Failed to send reset link. Please verify your email and try again.')
      }
    }catch(e){
      const msg = e?.response?.data?.message || 'Failed to send reset link. Please try again.'
      setForgotError(msg)
    }finally{
      setForgotLoading(false)
    }
  }

  return (
    <div style={{maxWidth:420, margin:'1rem auto'}}>
      <h2>Login</h2>
      {error && <div className="card" style={{borderColor:'#d9534f'}}>{error}</div>}
      <form onSubmit={submit}>
        <div className="label">Username</div>
        <input className="input" value={username} onChange={e=>setUsername(e.target.value)} required />
        <div className="label">Password</div>
        <input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} required />
        <div style={{marginTop:'.75rem'}}>
          <button className="btn btn-primary" disabled={loading}>{loading?'Signing in…':'Sign In'}</button>
          <Link to="/register" className="btn btn-outline" style={{marginLeft:'.5rem'}}>Create account</Link>
        </div>
      </form>

      <div style={{marginTop:'0.75rem'}}>
        <button className="btn btn-link" onClick={()=>{ setShowForgot(v=>!v); setForgotError(''); setForgotMsg('') }}>
          {showForgot ? 'Hide forgot password' : 'Forgot your password?'}
        </button>
      </div>

      {showForgot && (
        <div className="card" style={{marginTop:'0.5rem'}}>
          <div className="label">Reset your password</div>
          <p className="muted">Enter your email and we will send you a reset link.</p>
          <form onSubmit={requestReset}>
            <div className="label">Email</div>
            <input className="input" type="email" value={email} onChange={e=> setEmail(e.target.value)} placeholder="you@example.com" required />
            {forgotError && <div className="card" style={{marginTop:'.5rem', borderColor:'#d9534f'}}>{forgotError}</div>}
            {forgotMsg && <div className="card" style={{marginTop:'.5rem'}}>{forgotMsg}</div>}
            <div style={{marginTop:'.6rem'}}>
              <button className="btn btn-primary" disabled={forgotLoading}>{forgotLoading?'Sending…':'Send reset link'}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
