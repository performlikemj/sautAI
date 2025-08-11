import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Register(){
  const { register } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({ username:'', email:'', password:'', confirm:'' })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    if (form.password !== form.confirm){ setError('Passwords do not match.'); return }
    if (form.password.length < 8){ setError('Password must be at least 8 characters.'); return }
    setLoading(true)
    try{
      await register({ username: form.username, email: form.email, password: form.password })
      nav('/meal-plans')
    }catch(err){
      setError('Registration failed. Try a different username/email or check server logs.')
    }finally{
      setLoading(false)
    }
  }

  const set = (k)=>(e)=>setForm({...form, [k]: e.target.value})

  return (
    <div style={{maxWidth:480, margin:'1rem auto'}}>
      <h2>Create your account</h2>
      {error && <div className="card" style={{borderColor:'#d9534f'}}>{error}</div>}
      <form onSubmit={submit}>
        <div className="label">Username</div>
        <input className="input" value={form.username} onChange={set('username')} required />
        <div className="label">Email</div>
        <input className="input" type="email" value={form.email} onChange={set('email')} required />
        <div className="label">Password</div>
        <input className="input" type="password" value={form.password} onChange={set('password')} required />
        <div className="label">Confirm Password</div>
        <input className="input" type="password" value={form.confirm} onChange={set('confirm')} required />
        <div style={{marginTop:'.75rem'}}>
          <button className="btn btn-primary" disabled={loading}>{loading?'Creating…':'Create Account'}</button>
          <Link to="/login" className="btn btn-outline" style={{marginLeft:'.5rem'}}>I have an account</Link>
        </div>
      </form>
    </div>
  )
}
