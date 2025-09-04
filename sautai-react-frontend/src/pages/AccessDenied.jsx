import React from 'react'
import { Link } from 'react-router-dom'

export default function AccessDenied(){
  return (
    <div className="container">
      <div className="card" style={{textAlign:'center', borderColor:'#f0d000'}}>
        <h2 style={{marginTop:0}}>Access denied</h2>
        <p className="muted">You don’t have permission to view this page.</p>
        <p className="muted" style={{marginTop:'.25rem'}}>If you’re a chef, switch roles from the navbar and try again. If your email is not verified yet, please verify to unlock all features.</p>
        <div style={{display:'flex', gap:'.5rem', justifyContent:'center', marginTop:'.6rem'}}>
          <Link to="/" className="btn btn-primary">Go Home</Link>
          <Link to="/meal-plans" className="btn btn-outline">Meal Plans</Link>
          <Link to="/verify-email" className="btn btn-outline">Verify Email</Link>
        </div>
      </div>
    </div>
  )
}


