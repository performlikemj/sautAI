import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../api'
import Carousel from '../components/Carousel.jsx'

export default function Home(){
  const { user } = useAuth()
  const [applyOpen, setApplyOpen] = useState(false)
  const [chefForm, setChefForm] = useState({ experience:'', bio:'', serving_areas:'', profile_pic:null })
  const [submitting, setSubmitting] = useState(false)
  const [applyMsg, setApplyMsg] = useState(null)

  const FeatureRow = ({ image, title, bullets, reverse=false }) => (
    <div className={"media" + (reverse ? " reverse" : "")}>
      <div className="media-image">
        <img src={image} alt={title} className="image-rounded" />
      </div>
      <div className="media-body card">
        <h3 style={{marginTop:0}}>{title}</h3>
        <ul className="list">
          {bullets.map((b, i)=> <li key={i} dangerouslySetInnerHTML={{__html: b}} />)}
        </ul>
      </div>
    </div>
  )

  return (
    <div className="page-home">
      {/* Hero */}
      <section className="section">
        <div className="hero hero-split">
          <div className="hero-content">
            <div className="eyebrow">Community • Food • AI</div>
            <h1 className="display"><span className="text-gradient">Connect With Local Chefs</span></h1>
            <p>We link you with talented cooks in your community — from chefs preserving family recipes to those creating new flavors. Our AI simply helps plan your meals.</p>
            <div className="hero-actions">
              {!user && <Link to="/register" className="btn btn-primary">Get Started Today 🍽️</Link>}
              {!user && <Link to="/chefs" className="btn btn-outline">Explore as Guest</Link>}
              {user ? (
                 user?.is_chef ? null : <button className="btn btn-outline" onClick={()=> setApplyOpen(true)}>Become a Chef</button>
              ) : (
                <Link to="/login?next=/profile?applyChef=1" className="btn btn-outline">Become a Chef</Link>
              )}
            </div>
          </div>
          <div className="hero-image">
            <img src="https://live.staticflickr.com/65535/54548860874_7569d1dbdc_b.jpg" alt="Community chefs" className="image-rounded" />
          </div>
        </div>
      </section>

      <div className="divider" />

      {applyOpen && (
        <>
          <div className="right-panel-overlay" onClick={()=> setApplyOpen(false)} />
          <aside className="right-panel" role="dialog" aria-label="Become a Chef">
            <div className="right-panel-head">
              <div className="slot-title">Become a Community Chef</div>
              <button className="icon-btn" onClick={()=> setApplyOpen(false)}>✕</button>
            </div>
            <div className="right-panel-body">
              {applyMsg && <div className="card" style={{marginBottom:'.6rem'}}>{applyMsg}</div>}
              <p className="muted">Share your experience and where you can serve. You can complete your profile later.</p>
              <div className="label">Experience</div>
              <textarea className="textarea" rows={3} value={chefForm.experience} onChange={e=> setChefForm({...chefForm, experience:e.target.value})} />
              <div className="label">Bio</div>
              <textarea className="textarea" rows={3} value={chefForm.bio} onChange={e=> setChefForm({...chefForm, bio:e.target.value})} />
              <div className="label">Serving areas (postal codes)</div>
              <input className="input" value={chefForm.serving_areas} onChange={e=> setChefForm({...chefForm, serving_areas:e.target.value})} />
              <div className="label">Profile picture (optional)</div>
              <div>
                <input id="homeProfilePic" type="file" accept="image/jpeg,image/png,image/webp" style={{display:'none'}} onChange={e=> setChefForm({...chefForm, profile_pic: e.target.files?.[0]||null})} />
                <label htmlFor="homeProfilePic" className="btn btn-outline">Choose file</label>
                {chefForm.profile_pic && <span className="muted" style={{marginLeft:'.5rem'}}>{chefForm.profile_pic.name}</span>}
              </div>
              <div className="actions-row" style={{marginTop:'.6rem'}}>
                 <button className="btn btn-primary" disabled={submitting} onClick={async ()=>{
                  setSubmitting(true); setApplyMsg(null)
                  try{
                    const fd = new FormData()
                     fd.append('experience', chefForm.experience)
                     fd.append('bio', chefForm.bio)
                     fd.append('serving_areas', chefForm.serving_areas)
                     // Best effort: attach city/country if we have them on the user object
                     try{
                       const city = (user?.address?.city||'').trim()
                       const country = (user?.address?.country||'').trim()
                       if (city) fd.append('city', city)
                       if (country) fd.append('country', country)
                     }catch{}
                    if (chefForm.profile_pic) fd.append('profile_pic', chefForm.profile_pic)
                    const resp = await api.post('/chefs/api/chefs/submit-chef-request/', fd, { headers:{'Content-Type':'multipart/form-data'} })
                    if (resp.status===200 || resp.status===201){
                      setApplyMsg('Application submitted. We will notify you when approved.')
                    } else {
                      setApplyMsg('Submission failed. Please try again later.')
                    }
                   }catch(e){ setApplyMsg(e?.response?.data?.error || 'Submission failed. Please try again.') }
                  finally{ setSubmitting(false) }
                }}>{submitting?'Submitting…':'Submit Application'}</button>
                <button className="btn btn-outline" onClick={()=> setApplyOpen(false)}>Close</button>
              </div>
            </div>
          </aside>
        </>
      )}

      {/* Intro cards */}
      <section className="section" aria-labelledby="why">
        <h2 id="why" className="section-title">Why sautai?</h2>
        <div className="intro-cards" style={{marginTop:'.75rem'}}>
          <div className="card">
            <h3>🥘 Local Connection</h3>
            <p>Discover chefs in your neighborhood who prepare traditional favorites and exciting new meals while keeping culinary traditions alive.</p>
          </div>
          <div className="card">
            <h3>🧠 AI Meal Planning</h3>
            <p>Let our AI suggest balanced meal plans so you can focus on enjoying food and community.</p>
          </div>
          <div className="card">
            <h3>🥦 Health Tracking</h3>
            <p>Monitor your progress, track calories, and watch your health metrics improve with every meal.</p>
          </div>
        </div>
      </section>

      <div className="divider" />

      {/* Features with images (carousel on mobile) */}
      <section className="section" aria-labelledby="how">
        <h2 id="how" className="section-title">How sautai works for you</h2>
        <div className="feature-carousel" style={{ marginTop: '.5rem' }}>
          <Carousel
            ariaLabel="How sautai works carousel"
            autoPlay
            intervalMs={5500}
            pauseOnHover
            pauseOnTouch
            items={[
              (
                <FeatureRow
                  image="https://live.staticflickr.com/65535/54550764768_d565973881_b.jpg"
                  title="Effortless Meal Planning"
                  bullets={[
                    "<b>Customized Weekly Plans</b> – Meals tailored to your diet and preferences",
                    "<b>Ingredient Awareness</b> – Avoid allergens and disliked foods automatically",
                    "<b>One‑Click Adjustments</b> – Swap meals in seconds",
                    "<b>Chef Connections</b> – Connect with local chefs for preparation",
                  ]}
                />
              ),
              (
                <FeatureRow
                  image="https://live.staticflickr.com/65535/54550711849_2ac8954256_b.jpg"
                  title="Simple Health Monitoring"
                  bullets={[
                    "<b>Calorie & Nutrition Tracking</b> – Log and monitor daily intake",
                    "<b>Progress Visualization</b> – Clear, intuitive charts",
                    "<b>Mood & Energy Monitoring</b> – See how foods affect you",
                    "<b>Goal Setting</b> – Set targets and reach them",
                  ]}
                />
              ),
              (
                <FeatureRow
                  image="https://live.staticflickr.com/65535/54549653432_73f6b0bdfd_b.jpg"
                  title="Ongoing Support"
                  bullets={[
                    "<b>AI Nutrition Assistant</b> – Answers to all your nutrition questions",
                    "<b>Personalized Recommendations</b> – Suggestions that improve over time",
                    "<b>Emergency Supply Planning</b> – Healthy options for the unexpected",
                    "<b>Community Connection</b> – Learn from others on similar journeys",
                  ]}
                />
              ),
            ]}
          />
        </div>
      </section>

      <div className="divider" />

      {/* Steps */}
      <section className="section" aria-labelledby="steps">
        <h2 id="steps" className="section-title">Simple Steps to Better Health</h2>
        <div className="steps-grid" style={{marginTop:'.5rem'}}>
          {[
            ["1", "Sign Up", "Create your profile and tell us about your dietary needs and health goals."],
            ["2", "Get Your Plan", "Receive customized meal plans that match your preferences and nutritional requirements."],
            ["3", "Track Progress", "Log your meals and health metrics to monitor your journey toward better health."],
            ["4", "Adjust & Improve", "Refine your plans based on what works for you with the help of our AI assistant."],
          ].map(([num, title, desc]) => (
            <div key={title} className="card step">
              <div className="num" aria-hidden>{num}</div>
              <div>
                <h3 style={{margin:'0 0 .15rem'}}>{title}</h3>
                <p style={{margin:0, color:'var(--muted)'}}>{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="divider" />

      {/* CTA */}
      <section className="section" aria-labelledby="cta">
        <div className="cta">
          <div className="card">
            <h2 id="cta" style={{marginTop:0}}>Ready to Transform Your Relationship with Food?</h2>
            <p>Join a community that celebrates local chefs, from family recipes passed down through generations to brand new creations. Our AI-powered meal planning keeps things simple while you focus on sharing real food with real people.</p>
            <p style={{marginBottom:0}}>Start your journey to connected, tradition-rich meals today!</p>
          </div>
          <div className="actions">
            {!user && <Link to="/register" className="btn btn-primary" style={{textAlign:'center'}}>Create Free Account</Link>}
            {!user && <Link to="/chefs" className="btn btn-outline" style={{textAlign:'center'}}>Explore as Guest</Link>}
          </div>
        </div>
      </section>

      <section className="section" style={{paddingTop:0}}>
        <div style={{textAlign:'center'}}>
          <a href="https://www.buymeacoffee.com/sautai" target="_blank" rel="noreferrer">
            <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style={{height:60, width:217}} />
          </a>
        </div>
      </section>
    </div>
  )
}
