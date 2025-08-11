import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function ProtectedRoute({ children, requiredRole }){
  const { user, loading } = useAuth()
  if (loading) return <div className="container"><p>Loading…</p></div>
  if (!user) {
    console.warn('[ProtectedRoute] No user → redirect to /login')
    return <Navigate to="/login" replace />
  }

  if (requiredRole){
    const isChef = Boolean(user?.is_chef)
    const currentRole = user?.current_role || 'customer'
    const roleAllowed = (
      (requiredRole === 'chef' && isChef && currentRole === 'chef') ||
      (requiredRole === 'customer' && currentRole === 'customer')
    )
    console.log('[ProtectedRoute]', { requiredRole, isChef, currentRole, roleAllowed })
    if (!roleAllowed){
      console.warn('[ProtectedRoute] Access denied, redirecting to /', { requiredRole, isChef, currentRole })
      return <Navigate to="/" replace />
    }
  }

  return children
}
