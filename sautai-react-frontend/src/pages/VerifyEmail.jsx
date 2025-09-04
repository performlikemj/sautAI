import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../api'

export default function VerifyEmail(){
  const { user } = useAuth()
  const [sending, setSending] = useState(false)
  const [msg, setMsg] = useState(null)

  const resend = async ()=>{
    setMsg(null); setSending(true)
    try{
      await api.post('/auth/api/resend-activation-link/', { user_id: user?.id })
      setMsg('A new activation link has been sent to your email.')
      window.dispatchEvent(new CustomEvent('global-toast', { detail: { text:'Activation email sent.', tone:'success' } }))
    }catch(e){
      setMsg('Failed to resend activation link. Please try again later.')
    }finally{ setSending(false) }
  }

  const email = user?.email || 'your email'

  return (
    <div>
      <h2>Verify your email</h2>
      <div className="card">
        <p className="muted">We sent an activation link to <strong>{email}</strong>.</p>
        <p className="muted">Please click the link in that email to activate your account. Once activated, you’ll have full access.</p>
        {msg && <div className="card" style={{marginTop:'.5rem'}}>{msg}</div>}
        <div style={{marginTop:'.6rem'}}>
          <button className="btn btn-primary" onClick={resend} disabled={sending}>{sending?'Sending…':'Resend activation link'}</button>
        </div>
      </div>
    </div>
  )
}


