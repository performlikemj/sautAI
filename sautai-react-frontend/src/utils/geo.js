// Minimal country utilities for ISO 3166-1 alpha-2 selection/display
// We prefer using Intl.DisplayNames when available to resolve names

const COMMON_CODES = [
  'US','CA','MX','BR','AR','CL','CO','PE','VE','UY','EC','BO','PY',
  'GB','IE','FR','DE','ES','PT','IT','NL','BE','LU','CH','AT','SE','NO','DK','FI','IS','PL','CZ','SK','HU','RO','BG','GR','HR','SI','RS','UA','RU','BY','LT','LV','EE','TR',
  'AU','NZ',
  'JP','KR','CN','TW','HK','SG','MY','TH','VN','PH','ID','IN','PK','BD','LK','NP',
  'AE','SA','QA','KW','BH','OM','IL','EG','MA','TN','DZ','NG','GH','KE','ZA','ET',
  'NG','KE','TZ','UG','CM','SN',
]

function tryIntlName(code){
  try{
    if (typeof Intl !== 'undefined' && Intl.DisplayNames){
      const dn = new Intl.DisplayNames(['en'], { type:'region' })
      return dn.of(code) || null
    }
  }catch{}
  return null
}

const FALLBACK_NAMES = {
  US:'United States', CA:'Canada', MX:'Mexico', BR:'Brazil', AR:'Argentina', CL:'Chile', CO:'Colombia', PE:'Peru', VE:'Venezuela', UY:'Uruguay', EC:'Ecuador', BO:'Bolivia', PY:'Paraguay',
  GB:'United Kingdom', IE:'Ireland', FR:'France', DE:'Germany', ES:'Spain', PT:'Portugal', IT:'Italy', NL:'Netherlands', BE:'Belgium', LU:'Luxembourg', CH:'Switzerland', AT:'Austria', SE:'Sweden', NO:'Norway', DK:'Denmark', FI:'Finland', IS:'Iceland', PL:'Poland', CZ:'Czechia', SK:'Slovakia', HU:'Hungary', RO:'Romania', BG:'Bulgaria', GR:'Greece', HR:'Croatia', SI:'Slovenia', RS:'Serbia', UA:'Ukraine', RU:'Russia', BY:'Belarus', LT:'Lithuania', LV:'Latvia', EE:'Estonia', TR:'Turkey',
  AU:'Australia', NZ:'New Zealand',
  JP:'Japan', KR:'South Korea', CN:'China', TW:'Taiwan', HK:'Hong Kong', SG:'Singapore', MY:'Malaysia', TH:'Thailand', VN:'Vietnam', PH:'Philippines', ID:'Indonesia', IN:'India', PK:'Pakistan', BD:'Bangladesh', LK:'Sri Lanka', NP:'Nepal',
  AE:'United Arab Emirates', SA:'Saudi Arabia', QA:'Qatar', KW:'Kuwait', BH:'Bahrain', OM:'Oman', IL:'Israel', EG:'Egypt', MA:'Morocco', TN:'Tunisia', DZ:'Algeria', NG:'Nigeria', GH:'Ghana', KE:'Kenya', ZA:'South Africa', ET:'Ethiopia', TZ:'Tanzania', UG:'Uganda', CM:'Cameroon', SN:'Senegal'
}

export const COUNTRIES = Array.from(new Set(COMMON_CODES)).map(code => ({ code, name: tryIntlName(code) || FALLBACK_NAMES[code] || code }))

export function countryNameFromCode(code){
  const c = String(code||'').toUpperCase()
  if (!c || c.length !== 2) return code || ''
  return tryIntlName(c) || FALLBACK_NAMES[c] || c
}

export function codeFromCountryName(name){
  const target = String(name||'').toLowerCase().trim()
  if (!target) return ''
  for (const { code, name: n } of COUNTRIES){
    if (String(n||'').toLowerCase() === target) return code
  }
  return ''
}


