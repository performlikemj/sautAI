import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, refreshAccessToken } from '../api'

// Streaming chat UI using Vercel AI SDK's useChat for state, wired to backend SSE
export default function Chat(){
  const [params] = useSearchParams()
  const initialThread = params.get('thread')
  const [threadId, setThreadId] = useState(initialThread)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState(null)
  const [aborter, setAborter] = useState(null)
  const useDedup = true

  const endRef = useRef(null)
  const baseURL = useMemo(()=> api?.defaults?.baseURL || '', [])

  // useChat manages messages and input locally (UI-only usage)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const stop = ()=> aborter?.abort()
  const handleInputChange = (e)=> setInput(e.target.value)

  // Load existing history when a thread is specified
  useEffect(()=>{
    let mounted = true
    if (initialThread){
      api.get(`/customer_dashboard/api/thread_detail/${initialThread}/`).then(res => {
        if (!mounted) return
        const raw = res.data.chat_history || []
        raw.sort((a,b)=> new Date(a.created_at) - new Date(b.created_at))
        setMessages(raw.map((m, idx) => ({ id: `hist-${idx}`, role: m.role, content: m.content })))
      }).catch(()=>{})
    }
    return ()=>{ mounted = false }
  }, [initialThread, setMessages])

  // Auto-scroll as new content arrives
  useEffect(()=>{
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isStreaming])

  const newChat = ()=>{
    stop()
    aborter?.abort()
    setAborter(null)
    setMessages([])
    setThreadId(null)
    setInput('')
    setError(null)
  }

  async function sendMessage(){
    const text = input.trim()
    if (!text || isStreaming) return
    setError(null)
    setInput('')

    // Show user message
    setMessages(prev => [...prev, { id: `u-${Date.now()}`, role: 'user', content: text }])

    // Prepare streaming assistant message placeholder
    const assistantId = `a-${Date.now()}`
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '' }])

    const controller = new AbortController()
    setAborter(controller)
    setIsStreaming(true)

    try{
      const url = `${baseURL}/customer_dashboard/api/assistant/stream-message/`

      // Proactively refresh access token (handles cookie or refresh-token mode)
      try { await refreshAccessToken() } catch { /* ignore; may not have refresh */ }
      let token = localStorage.getItem('accessToken') || ''
      const body = { message: text }
      if (threadId) body.thread_id = threadId

      let resp = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal
      })

      // If unauthorized, try one refresh-and-retry
      if (resp.status === 401){
        try { await refreshAccessToken() } catch {}
        token = localStorage.getItem('accessToken') || ''
        resp = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(body),
          signal: controller.signal
        })
      }

      if (!resp.ok){
        throw new Error(`Request failed ${resp.status}`)
      }

      // Stream and parse SSE
      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const commitAppend = (delta)=>{
        if (!delta) return
        setMessages(prev => prev.map(m => {
          if (m.id !== assistantId) return m
          const curr = m.content || ''
          const d = String(delta)
          // Dedup
          if (d.startsWith(curr)){
            return { ...m, content: d }
          }
          if (curr && (curr.endsWith(d) || curr.includes(d))){
            return m
          }
          return { ...m, content: curr + d }
        }))
      }

      const processEvent = (dataLine)=>{
        try{
          const json = JSON.parse(dataLine)
          const t = json?.type
          if (t === 'response.created'){
            const rid = json?.id
            if (rid && !threadId) setThreadId(rid)
          } else if (t === 'response.output_text.delta'){
            const delta = json?.delta?.text || ''
            if (delta) commitAppend(delta)
          } else if (t === 'response.tool'){
            // Optional: surface tool events subtly; skip for now
          } else if (t === 'response.completed'){
            // End of this turn. Ensure we do not have a duplicated trailing space
          } else if (t === 'error'){
            throw new Error(json?.message || 'Stream error')
          } else if (t === 'text'){
            // Fallback compatibility: some emit simple {type:'text', content}
            const delta = json?.content || ''
            if (delta) commitAppend(delta)
          }
        }catch(e){
          // Ignore malformed lines
        }
      }

      while (true){
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // Split by double newlines (SSE event delimiter)
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1){
          const chunk = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const lines = chunk.split('\n')
          for (const line of lines){
            const trimmed = line.trim()
            if (trimmed.startsWith('data: ')){
              const data = trimmed.slice(6)
              if (data) processEvent(data)
            }
          }
        }
      }
    } catch (e){
      if (e?.name !== 'AbortError'){
        setError(e)
        setMessages(prev => prev.map(m => m.role === 'assistant' && m.content === '' ? ({ ...m, content: 'Sorry, something went wrong. Please try again.' }) : m))
      }
    } finally {
      setIsStreaming(false)
      setAborter(null)
    }
  }

  const onKeyDown = (e)=>{
    if (e.key === 'Enter' && !e.shiftKey){
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="page-chat">
      <div className="chat-header">
        <div className="left">
          <h2>Chat with sautAI</h2>
          <div className="sub muted">Meal planning, nutrition, and local chef help</div>
        </div>
        <div className="right">
          <button className="btn btn-outline" onClick={newChat}>New chat</button>
        </div>
      </div>

      <div className="chat-surface card">
        <div className="messages" role="log" aria-live="polite">
          {messages.map(m => (
            <MessageBubble key={m.id} role={m.role} content={m.content} />
          ))}
          {isStreaming && (
            <div className="typing-row"><span className="dot" /><span className="dot" /><span className="dot" /></div>
          )}
          <div ref={endRef} />
        </div>

        <div className="composer">
          <textarea
            className="textarea"
            rows={1}
            placeholder="Ask anything about meals, nutrition, or chefs…"
            value={input}
            onChange={handleInputChange}
            onKeyDown={onKeyDown}
            disabled={isStreaming}
          />
          <div className="composer-actions">
            {isStreaming ? (
              <button className="btn btn-outline" onClick={()=> aborter?.abort()}>
                Stop
              </button>
            ) : (
              <button className="btn btn-primary" onClick={sendMessage} disabled={!input.trim()}>
                Send
              </button>
            )}
          </div>
        </div>
        {error && <div className="error-text">{String(error?.message || error)}</div>}
      </div>
    </div>
  )
}

function MessageBubble({ role, content }){
  const isUser = role === 'user'
  return (
    <div className={`msg-row ${isUser ? 'right' : 'left'}`}>
      <div className={`bubble ${isUser ? 'user' : 'assistant'}`}>
        <div className="bubble-content">{content}</div>
      </div>
    </div>
  )
}
