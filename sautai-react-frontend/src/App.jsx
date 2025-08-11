import React from 'react'
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
import History from './pages/History.jsx'

export default function App(){
  return (
    <div>
      <NavBar />
      <div className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/chat" element={<ProtectedRoute requiredRole="customer"><Chat /></ProtectedRoute>} />
          <Route path="/meal-plans" element={<ProtectedRoute requiredRole="customer"><MealPlans /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="/chefs/dashboard" element={<ProtectedRoute requiredRole="chef"><ChefDashboard /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute requiredRole="customer"><History /></ProtectedRoute>} />
        </Routes>
        <div className="footer">
          <p>Cook with care. Share with joy. — <a href="https://www.buymeacoffee.com/sautai" target="_blank">Support sautAI</a></p>
        </div>
      </div>
    </div>
  )
}
