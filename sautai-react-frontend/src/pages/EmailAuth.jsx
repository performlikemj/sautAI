import React, { useEffect, useState } from 'react'

export default function EmailAuth(){
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')

  useEffect(()=>{
    const params = new URLSearchParams(window.location.search)
    let auth_token = params.get('auth_token') || ''
    const action = params.get('action') || ''

    if (!auth_token){
      setStatus('error')
      setMessage('Missing auth token.')
      return
    }

    // Streamlit sometimes appends the action to the token value; trim if present
    if (action === 'email_auth' && auth_token.endsWith(action)){
      auth_token = auth_token.slice(0, -action.length)
    }

    const base = import.meta.env.VITE_API_BASE
    if (!base){
      setStatus('error')
      setMessage('Missing VITE_API_BASE configuration.')
      return
    }

    const run = async () => {
      try{
        setStatus('loading')
        const res = await fetch(`${base}/auth/api/email_auth/${encodeURIComponent(auth_token)}/`, {
          method: 'GET'
        })
        const contentType = res.headers.get('content-type') || ''
        let data = null
        let text = ''
        if (contentType.includes('application/json')){
          try{ data = await res.json() }catch{ data = null }
        }
        if (data == null){
          try{ text = await res.text() }catch{ text = '' }
        }
        if (res.ok){
          const msg = (data && (data.message || data.detail)) || text || 'Email confirmed successfully! You can now email your assistant.'
          setStatus('success')
          setMessage(typeof msg === 'string' ? msg : JSON.stringify(msg))
        } else {
          // Prefer explicit message keys if present; otherwise fallback
          let err = (data && (data.detail || data.message)) || text || 'Failed to confirm email. The link may be invalid or expired.'
          setStatus('error')
          setMessage(typeof err === 'string' ? err : JSON.stringify(err))
        }
      } catch (e){
        setStatus('error')
        setMessage('Network error. Please try again.')
      }
    }
    run()
  }, [])

  return (
    <div className="card">
      <h1>Email Authentication</h1>
      {status === 'idle' && <p>Preparing…</p>}
      {status === 'loading' && <p>Confirming…</p>}
      {status === 'success' && <p className="success-text">{message}</p>}
      {status === 'error' && <p className="error-text">{message}</p>}
    </div>
  )
}


