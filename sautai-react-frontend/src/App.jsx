import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Chat from './pages/Chat.jsx'
import MealPlans from './pages/MealPlans.jsx'
import Profile from './pages/Profile.jsx'
import ChefDashboard from './pages/ChefDashboard.jsx'
import NotFound from './pages/NotFound.jsx'
import AccessDenied from './pages/AccessDenied.jsx'
import VerifyEmail from './pages/VerifyEmail.jsx'
import Account from './pages/Account.jsx'
import MealPlanApproval from './pages/MealPlanApproval.jsx'
import EmailAuth from './pages/EmailAuth.jsx'
// History removed
import HealthMetrics from './pages/HealthMetrics.jsx'
import PublicChef from './pages/PublicChef.jsx'
import ChefsDirectory from './pages/ChefsDirectory.jsx'

export default function App(){
  const [globalToasts, setGlobalToasts] = useState([]) // {id, text, tone, closing}

  useEffect(()=>{
    const onToast = (e)=>{
      try{
        const detail = e?.detail || {}
        const text = detail.text || String(detail) || 'An error occurred'
        const tone = detail.tone || 'error'
        const id = Math.random().toString(36).slice(2)
        setGlobalToasts(prev => [...prev, { id, text, tone, closing:false }])
        setTimeout(()=>{
          setGlobalToasts(prev => prev.map(t => t.id === id ? { ...t, closing:true } : t))
          setTimeout(()=> setGlobalToasts(prev => prev.filter(t => t.id !== id)), 260)
        }, 3800)
      }catch{}
    }
    window.addEventListener('global-toast', onToast)
    return ()=> window.removeEventListener('global-toast', onToast)
  }, [])
  return (
    <div>
      <NavBar />
      <div className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/account" element={<Account />} />
          <Route path="/register" element={<Register />} />
          <Route path="/chat" element={<ProtectedRoute requiredRole="customer"><Chat /></ProtectedRoute>} />
          <Route path="/meal-plans" element={<ProtectedRoute requiredRole="customer"><MealPlans /></ProtectedRoute>} />
          <Route path="/meal_plans" element={<MealPlanApproval />} />
          <Route path="/email_auth" element={<EmailAuth />} />
          <Route path="/assistant" element={<EmailAuth />} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/chefs/dashboard" element={<ProtectedRoute requiredRole="chef"><ChefDashboard /></ProtectedRoute>} />
          <Route path="/verify-email" element={<ProtectedRoute><VerifyEmail /></ProtectedRoute>} />
          <Route path="/c/:username" element={<PublicChef />} />
          <Route path="/chefs" element={<ChefsDirectory />} />
          {/* History route removed */}
          <Route path="/health" element={<ProtectedRoute requiredRole="customer"><HealthMetrics /></ProtectedRoute>} />
          <Route path="/403" element={<AccessDenied />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
        <div className="footer">
          <p>Cook with care. Share with joy. — <a href="https://www.buymeacoffee.com/sautai" target="_blank">Support sautai</a></p>
        </div>
      </div>
      <GlobalToastOverlay toasts={globalToasts} />
    </div>
  )
}

function GlobalToastOverlay({ toasts }){
  if (!toasts || toasts.length===0) return null
  return createPortal(
    <div className="toast-container" role="status" aria-live="polite">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.tone} ${t.closing?'closing':''}`}>{t.text}</div>
      ))}
    </div>,
    document.body
  )
}
