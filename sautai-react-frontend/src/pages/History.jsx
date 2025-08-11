import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function History(){
  const [items, setItems] = useState([])
  const [next, setNext] = useState(null)
  const [prev, setPrev] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  const load = async (p=1)=>{
    setLoading(true)
    try{
      const res = await api.get(`/customer_dashboard/api/thread_history/?page=${p}`)
      setItems(res.data.results || res.data.items || [])
      setNext(res.data.next || null)
      setPrev(res.data.previous || null)
      setPage(p)
    }catch{
      setItems([]); setNext(null); setPrev(null)
    }finally{
      setLoading(false)
    }
  }

  useEffect(()=>{ load(1) }, [])

  return (
    <div>
      <h2>Chat History</h2>
      {loading && <div className="card">Loading…</div>}
      {!loading && items.length===0 && <div className="card">No conversations yet.</div>}
      <div className="grid">
        {items.map(th => (
          <div key={th.id || th.thread_id} className="card">
            <h3>{th.title || 'Conversation'}</h3>
            <p><em>{th.created_at ? new Date(th.created_at).toLocaleString() : ''}</em></p>
            <Link to={`/chat?thread=${th.id || th.thread_id}`} className="btn btn-primary">Open</Link>
          </div>
        ))}
      </div>
      <div style={{marginTop:'.75rem', display:'flex', gap:'.5rem'}}>
        <button className="btn btn-outline" onClick={()=>load(page-1)} disabled={!prev}>Previous</button>
        <button className="btn btn-outline" onClick={()=>load(page+1)} disabled={!next}>Next</button>
      </div>
    </div>
  )
}
