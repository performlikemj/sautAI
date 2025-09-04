import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function ProtectedRoute({ children, requiredRole }){
  const { user, loading } = useAuth()
  if (loading) return <div className="container"><p>Loading…</p></div>
  if (!user) {
    const next = typeof window !== 'undefined' ? window.location.pathname + window.location.search : '/'
    console.warn('[ProtectedRoute] No user → redirect to /login', { next })
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />
  }

  // If user not verified, restrict access to most protected pages
  try{
    const path = typeof window !== 'undefined' ? (window.location.pathname || '') : ''
    const allowUnverifiedPaths = new Set(['/verify-email','/profile'])
    const isAllowed = allowUnverifiedPaths.has(path)
    const isVerified = Boolean(user?.email_confirmed)
    if (!isVerified && !isAllowed){
      return <Navigate to="/verify-email" replace />
    }
  }catch{}

  if (requiredRole){
    const isChef = Boolean(user?.is_chef)
    const currentRole = user?.current_role || 'customer'
    const roleAllowed = (
      (requiredRole === 'chef' && isChef && currentRole === 'chef') ||
      (requiredRole === 'customer' && currentRole === 'customer')
    )
    if (!roleAllowed){
      return <Navigate to="/403" replace />
    }
  }

  return children
}
