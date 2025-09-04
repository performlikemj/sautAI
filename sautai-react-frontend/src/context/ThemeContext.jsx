import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'

const ThemeContext = createContext({ theme: 'light', setTheme: () => {}, toggleTheme: () => {} })

function getSystemTheme(){
  try{
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }catch{
    return 'light'
  }
}

function getInitialTheme(){
  try{
    const stored = localStorage.getItem('theme')
    if (stored === 'light' || stored === 'dark') return stored
  }catch{}
  return getSystemTheme()
}

export function ThemeProvider({ children }){
  const [theme, setThemeState] = useState(getInitialTheme)

  useEffect(()=>{
    const root = document.documentElement
    root.setAttribute('data-theme', theme)
    try{ localStorage.setItem('theme', theme) }catch{}
  }, [theme])

  useEffect(()=>{
    // React to system preference changes only if user hasn't explicitly chosen
    let stored
    try{ stored = localStorage.getItem('theme') }catch{}
    if (stored === 'light' || stored === 'dark') return
    const mql = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null
    const onChange = () => setThemeState(getSystemTheme())
    try{ mql && mql.addEventListener('change', onChange) }catch{ try{ mql && mql.addListener(onChange) }catch{} }
    return () => { try{ mql && mql.removeEventListener('change', onChange) }catch{ try{ mql && mql.removeListener(onChange) }catch{} } }
  }, [])

  const api = useMemo(()=>({
    theme,
    setTheme: (t) => setThemeState(t === 'dark' ? 'dark' : 'light'),
    toggleTheme: () => setThemeState(prev => prev === 'dark' ? 'light' : 'dark')
  }), [theme])

  return (
    <ThemeContext.Provider value={api}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(){
  return useContext(ThemeContext)
}


