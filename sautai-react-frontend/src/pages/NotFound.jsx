import React from 'react'
import { Link } from 'react-router-dom'

export default function NotFound(){
  return (
    <div className="container">
      <div className="card" style={{textAlign:'center'}}>
        <h2 style={{marginTop:0}}>Page not found</h2>
        <p className="muted">We couldn’t find what you were looking for.</p>
        <div style={{display:'flex', gap:'.5rem', justifyContent:'center', marginTop:'.6rem'}}>
          <Link to="/" className="btn btn-primary">Go Home</Link>
          <Link to="/profile" className="btn btn-outline">Profile</Link>
          <Link to="/meal-plans" className="btn btn-outline">Meal Plans</Link>
        </div>
      </div>
    </div>
  )
}


