import React, { useEffect, useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { api } from '../api'

function useQuery(){
  const { search } = useLocation()
  return React.useMemo(()=> new URLSearchParams(search), [search])
}

export default function Account(){
  const q = useQuery()
  const action = (q.get('action')||'').trim()
  const uid = (q.get('uid')||'').trim()
  const token = (q.get('token')||'').trim()
  const approvalToken = (q.get('approval_token')||'').trim()
  const mealPrepPref = (q.get('meal_prep_preference')||'').trim()
  const authTokenFull = (q.get('auth_token')||'').trim()
  const userIdParam = (q.get('user_id')||'').trim()
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')

  // Secure: only allow these actions without login
  const allowAnon = new Set(['activate','password_reset','process_now'])
  const safeAction = allowAnon.has(action) ? action : ''

  useEffect(()=>{
    // process_now (email processing) – no login required
    if (safeAction === 'process_now' && token){
      setLoading(true); setMsg('Processing your message…'); setError('')
      ;(async ()=>{
        try{
          // Mirror Streamlit behavior; backend may accept GET
          const res = await api.get('/auth/api/process_now/', { params: { token } })
          if (res?.data?.status === 'success') setMsg(res.data.message || 'Processed successfully.')
          else setMsg(res?.data?.message || 'Your message was processed.')
        }catch(e){ setError('Failed to process the message. Please try again later.') }
        finally{ setLoading(false) }
      })()
    }
    // activate – verify email without login
    if (safeAction === 'activate' && uid && token){
      setLoading(true); setMsg('Activating your account…'); setError('')
      ;(async ()=>{
        try{
          const res = await api.post('/auth/api/register/verify-email/', { uid, token })
          setMsg(res?.data?.message || 'Your account has been activated!')
        }catch(e){
          const m = e?.response?.data?.message || 'Account activation failed.'
          setError(m)
        }finally{ setLoading(false) }
      })()
    }
    // email_auth – confirm email channel for assistant, no login needed
    if ((action||'') === 'email_auth' && authTokenFull){
      setLoading(true); setMsg('Confirming your email…'); setError('')
      // Streamlit trims suffix; emulate safely by removing trailing action if present
      let actual = authTokenFull
      if (actual.endsWith(action)) actual = actual.slice(0, -action.length)
      ;(async ()=>{
        try{
          const res = await api.get(`/auth/api/email_auth/${encodeURIComponent(actual)}/`)
          if (res?.status === 200){ setMsg(res?.data?.message || 'Email confirmed successfully! You can now email your assistant.') }
          else { setError('Failed to confirm email. The link may be invalid or expired.') }
        }catch{
          setError('Failed to confirm email. The link may be invalid or expired.')
        }finally{ setLoading(false) }
      })()
    }
    // Meal plan email approvals via approval_token
    if (approvalToken && !loading){
      if ((action||'') === 'generate_emergency_plan'){
        setLoading(true); setMsg('Generating your emergency pantry plan…'); setError('')
        ;(async ()=>{
          try{
            const payload = { approval_token: approvalToken }
            if (userIdParam) payload.user_id = userIdParam
            const res = await api.post('/meals/api/generate_emergency_supply/', payload)
            if (res?.status === 200){ setMsg('Emergency supply list generated successfully! Check your email for details.') }
            else { setError('Error generating emergency plan.') }
          }catch(e){ setError('Error generating emergency plan.') }
          finally{ setLoading(false) }
        })()
      } else {
        // Default: approve meal plan from email
        setLoading(true); setMsg('Approving your meal plan…'); setError('')
        ;(async ()=>{
          try{
            const res = await api.post('/meals/api/email_approved_meal_plan/', { approval_token: approvalToken, meal_prep_preference: mealPrepPref || undefined }, { skipUserId: true })
            const successMsg = res?.data?.message || res?.data?.error || 'Your meal plan has been approved!'
            setMsg(successMsg)
          }catch(e){
            const data = e?.response?.data
            const err = (data && (data.error || data.message)) || e?.message 
            setError(typeof err === 'string' ? err : JSON.stringify(err))
          }
          finally{ setLoading(false) }
        })()
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [safeAction, uid, token, action, authTokenFull, approvalToken, mealPrepPref, userIdParam])

  const submitReset = async (e)=>{
    e.preventDefault()
    setError(''); setMsg('')
    if (!pw || !pw2) { setError('Please fill in all fields.'); return }
    if (pw !== pw2) { setError('New password and confirmation do not match.'); return }
    setLoading(true)
    try{
      const res = await api.post('/auth/api/reset_password/', { uid, token, new_password: pw, confirm_password: pw2 })
      if (res.status === 200){ setMsg('Password reset successfully. Please log in with your new password.') }
      else { setError('Failed to reset password.') }
    }catch(e){ setError(e?.response?.data?.message || 'Failed to reset password.') }
    finally{ setLoading(false) }
  }

  return (
    <div>
      <h2>Account</h2>
      {safeAction === 'process_now' && (
        <div className="card">
          <div className="label">Process Email Now</div>
          {loading && <div className="muted">Processing…</div>}
          {msg && <div className="card" style={{marginTop:'.5rem'}}>{msg}</div>}
          {error && <div className="card" style={{marginTop:'.5rem', borderColor:'#d9534f'}}>{error}</div>}
          <div style={{marginTop:'.6rem'}}>
            <Link to="/" className="btn btn-outline">Go Home</Link>
          </div>
        </div>
      )}

      {safeAction === 'activate' && (
        <div className="card">
          <div className="label">Account Activation</div>
          {loading && <div className="muted">Activating your account…</div>}
          {msg && <div className="card" style={{marginTop:'.5rem'}}>{msg}</div>}
          {error && <div className="card" style={{marginTop:'.5rem', borderColor:'#d9534f'}}>{error}</div>}
          <div style={{marginTop:'.6rem'}}>
            <Link to="/login" className="btn btn-primary">Log In</Link>
            <Link to="/" className="btn btn-outline" style={{marginLeft:'.5rem'}}>Home</Link>
          </div>
        </div>
      )}

      {safeAction === 'password_reset' && (
        <div className="card">
          <div className="label">Reset Password</div>
          <form onSubmit={submitReset}>
            <div className="label">New Password</div>
            <input className="input" type="password" value={pw} onChange={e=> setPw(e.target.value)} />
            <div className="label">Confirm New Password</div>
            <input className="input" type="password" value={pw2} onChange={e=> setPw2(e.target.value)} />
            {error && <div className="card" style={{marginTop:'.5rem', borderColor:'#d9534f'}}>{error}</div>}
            {msg && <div className="card" style={{marginTop:'.5rem'}}>{msg}</div>}
            <div style={{marginTop:'.6rem'}}>
              <button className="btn btn-primary" disabled={loading}>{loading?'Submitting…':'Reset Password'}</button>
              <Link to="/login" className="btn btn-outline" style={{marginLeft:'.5rem'}}>Log In</Link>
            </div>
          </form>
        </div>
      )}

      {!safeAction && (
        <div className="card">
          <div className="label">Account</div>
          <p className="muted">No valid action specified. Please use the link from your email, or visit the login page.</p>
          <div style={{marginTop:'.6rem'}}>
            <Link to="/login" className="btn btn-primary">Log In</Link>
            <Link to="/" className="btn btn-outline" style={{marginLeft:'.5rem'}}>Home</Link>
          </div>
        </div>
      )}
    </div>
  )
}


