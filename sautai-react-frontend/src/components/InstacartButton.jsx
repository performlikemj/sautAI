import React from 'react'

export default function InstacartButton({ url, text = 'Get Ingredients', logoSrc = 'https://live.staticflickr.com/65535/54538897116_fb233f397f_m.jpg' }){
  if (!url) return null
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      style={{ textDecoration: 'none' }}
      aria-label={`${text} on Instacart`}
    >
      <div
        style={{
          height: 46,
          display: 'inline-flex',
          alignItems: 'center',
          padding: '16px 18px',
          background: '#FFFFFF',
          border: '0.5px solid #E8E9EB',
          borderRadius: 8,
        }}
      >
        <img
          src={logoSrc}
          alt="Instacart"
          style={{ height: 22, width: 'auto', marginRight: 10 }}
        />
        <span
          style={{
            fontFamily: 'Arial, sans-serif',
            fontSize: 16,
            fontWeight: 500,
            color: '#000000',
            whiteSpace: 'nowrap',
          }}
        >
          {text}
        </span>
      </div>
    </a>
  )
}


