import React, { useEffect, useState } from 'react'
import { api } from '../api'

function toArray(payload){
  if (!payload) return []
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  if (Array.isArray(payload?.data)) return payload.data
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.events)) return payload.events
  if (Array.isArray(payload?.orders)) return payload.orders
  // Sometimes single object
  if (typeof payload === 'object') return Object.values(payload).filter(v => typeof v === 'object')
  return []
}

export default function ChefDashboard(){
  const [events, setEvents] = useState([])
  const [orders, setOrders] = useState([])
  const [form, setForm] = useState({ name:'', description:'', base_price:'' })
  const [notice, setNotice] = useState(null)

  const load = async ()=>{
    setNotice(null)
    try{
      const u = await api.get('/auth/api/user_details/')
      console.log('[ChefDashboard] user_details', { current_role: u.data?.current_role, is_chef: u.data?.is_chef })
    }catch(e){
      console.warn('[ChefDashboard] user_details failed', e?.response?.status)
    }

    // Chef events
    try{
      const m = await api.get('/meals/api/chef-meal-events/')
      const arr = toArray(m.data)
      console.log('[ChefDashboard] GET /meals/api/chef-meal-events/ ←', m.status, { shape: Object.keys(m.data||{}), length: arr.length })
      setEvents(arr)
    }catch(e){
      const status = e?.response?.status
      console.warn('[ChefDashboard] events error', { status, url: e?.config?.url })
      if (status === 404){
        setNotice('Chef event endpoints not found at /meals/api/chef-meal-events/. Please confirm backend routes.')
      }
      setEvents([])
    }

    // Chef orders
    try{
      const o = await api.get('/meals/api/chef-received-orders/')
      const arr = toArray(o.data)
      console.log('[ChefDashboard] GET /meals/api/chef-received-orders/ ←', o.status, { shape: Object.keys(o.data||{}), length: arr.length })
      setOrders(arr)
    }catch(e){
      const status = e?.response?.status
      console.warn('[ChefDashboard] orders error', { status, url: e?.config?.url })
      if (status === 404){
        setNotice(prev => prev || 'Chef orders endpoint not found at /meals/api/chef-received-orders/.')
      }
      setOrders([])
    }
  }

  useEffect(()=>{ load() }, [])

  const createMeal = async (e)=>{
    e.preventDefault()
    try{
      const resp = await api.post('/meals/api/chef/meals/', form)
      const arr = toArray(resp.data)
      // If API returns created object, append; else reload
      if (arr.length === 0 && resp.data && typeof resp.data === 'object'){
        setEvents(x=>[...x, resp.data])
      }else{
        setEvents(x=>[...x, ...arr])
      }
      setForm({ name:'', description:'', base_price:'' })
    }catch(e){
      const status = e?.response?.status
      console.warn('[ChefDashboard] createMeal failed', { status, url: e?.config?.url, data: e?.response?.data })
      alert(status === 404 ? 'Create endpoint not found at /meals/api/chef/meals/.' : 'Failed to create meal')
    }
  }

  const eventsArray = Array.isArray(events) ? events : []
  const ordersArray = Array.isArray(orders) ? orders : []

  return (
    <div>
      <h2>Chef Dashboard</h2>

      {notice && <div className="card" style={{borderColor:'#f0d000'}}>{notice}</div>}

      <div className="card">
        <h3>Create a new offering</h3>
        <form onSubmit={createMeal}>
          <div className="label">Name</div>
          <input className="input" value={form.name} onChange={e=>setForm({...form, name:e.target.value})} required />
          <div className="label">Description</div>
          <textarea className="textarea" value={form.description} onChange={e=>setForm({...form, description:e.target.value})} />
          <div className="label">Base price (USD)</div>
          <input className="input" value={form.base_price} onChange={e=>setForm({...form, base_price:e.target.value})} />
          <div style={{marginTop:'.6rem'}}><button className="btn btn-primary">Add Meal</button></div>
        </form>
      </div>

      <div className="grid grid-2" style={{marginTop:'1rem'}}>
        <div className="card">
          <h3>My Events</h3>
          {eventsArray.length===0 ? <p>No events yet.</p> : (
            <ul>
              {eventsArray.map(ev => (
                <li key={ev.id || ev.event_id || Math.random()}>
                  <strong>{ev.meal_name || ev.name || 'Event'}</strong> — {(ev.description || ev.details || '')} {ev.base_price?`($${ev.base_price})`:''}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card">
          <h3>Orders</h3>
          {ordersArray.length===0 ? <p>No orders yet.</p> : (
            <ul>
              {ordersArray.map(o => (
                <li key={o.id || o.order_id || Math.random()}>
                  {(o.customer_name||'Customer')} ordered <strong>{o.meal_name||o.meal||'Meal'}</strong> x{(o.quantity||1)} for {o.event_date? new Date(o.event_date).toLocaleString(): '(date TBD)'} — <em>{o.status||'Pending'}</em>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
