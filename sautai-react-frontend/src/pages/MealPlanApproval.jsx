import React, { useEffect, useState } from 'react'

export default function MealPlanApproval(){
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')

  useEffect(()=>{
    const params = new URLSearchParams(window.location.search)
    const approval_token = params.get('approval_token')
    const meal_prep_preference = params.get('meal_prep_preference')
    const action = params.get('action') || ''
    const user_id = params.get('user_id') || ''

    // Emergency plan generation flow (email link)
    if (approval_token && action === 'generate_emergency_plan'){
      const base = import.meta.env.VITE_API_BASE
      if (!base){
        setStatus('error')
        setMessage('Missing VITE_API_BASE configuration.')
        return
      }
      const runEmergency = async () => {
        try{
          setStatus('loading')
          const body = { approval_token }
          if (user_id) body.user_id = user_id
          const res = await fetch(`${base}/meals/api/generate_emergency_supply/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
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
            const msg = (data && (data.message || data.detail)) || text || 'Emergency supply list generated successfully! Check your email for details.'
            setStatus('success')
            setMessage(typeof msg === 'string' ? msg : JSON.stringify(msg))
          } else {
            const err = (data && (data.error || data.message || data.detail)) || text || 'Error generating emergency plan.'
            setStatus('error')
            setMessage(typeof err === 'string' ? err : JSON.stringify(err))
          }
        } catch (e){
          setStatus('error')
          setMessage('Network error. Please try again.')
        }
      }
      runEmergency()
      return
    }

    // Standard meal plan approval flow
    if (!approval_token || !meal_prep_preference){
      setStatus('error')
      setMessage('Missing approval token or preference.')
      return
    }
    if (!['daily', 'one_day_prep'].includes(meal_prep_preference)){
      setStatus('error')
      setMessage('Invalid meal prep preference.')
      return
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
        const res = await fetch(`${base}/meals/api/email_approved_meal_plan/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approval_token, meal_prep_preference })
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
          const msg = (data && (data.message || data.error)) || text || 'Meal plan approved successfully.'
          setStatus('success')
          setMessage(typeof msg === 'string' ? msg : JSON.stringify(msg))
        } else {
          const err = (data && (data.error || data.message)) || text || ''
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
      <h1>Meal Plan Approval</h1>
      {status === 'idle' && <p>Preparing…</p>}
      {status === 'loading' && <p>Approving…</p>}
      {status === 'success' && <p className="success-text">{message}</p>}
      {status === 'error' && <p className="error-text">{message}</p>}
    </div>
  )
}


