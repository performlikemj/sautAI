import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login(){
  const { login } = useAuth()
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try{
      await login(username, password)
      nav('/meal-plans')
    }catch(err){
      setError('Invalid credentials or server error.')
    }finally{
      setLoading(false)
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
    </div>
  )
}
