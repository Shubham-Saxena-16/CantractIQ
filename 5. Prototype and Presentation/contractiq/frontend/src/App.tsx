import { createContext, useContext, useEffect, useState } from 'react'
import { BookOpenCheck, CalendarClock, FileSearch, FileUp, Gauge, GitCompareArrows, ListChecks, Menu, MessageSquareText, ShieldCheck, ShieldAlert, TableProperties, Bot, Database, Presentation as Presentation_ } from 'lucide-react'
import { api, type Meta } from './api'
import Dashboard from './pages/Dashboard'
import Register from './pages/Register'
import Workspace from './pages/Workspace'
import Commitments from './pages/Commitments'
import Obligations from './pages/Obligations'
import Ask from './pages/Ask'
import Upload from './pages/Upload'
import ReviewQueue from './pages/ReviewQueue'
import DataQuality from './pages/DataQuality'
import DocumentsPage from './pages/Documents'
import Presentation from './presentation/Presentation'

interface Ctx { meta: Meta | null; reviewer: string; setReviewer: (s: string) => void; go: (h: string) => void }
export const AppCtx = createContext<Ctx>({ meta: null, reviewer: '', setReviewer: () => {}, go: () => {} })
export const useApp = () => useContext(AppCtx)

function readLS(k: string, d: string) { try { return localStorage.getItem(k) ?? d } catch { return d } }
function writeLS(k: string, v: string) { try { localStorage.setItem(k, v) } catch { /* storage unavailable */ } }

function useHash() {
  const [hash, setHash] = useState(() => window.location.hash.slice(1) || '/')
  useEffect(() => {
    const on = () => { setHash(window.location.hash.slice(1) || '/'); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return hash
}

const NAV = [
  { to: '/', label: 'Dashboard', icon: Gauge },
  { to: '/register', label: 'Contract register', icon: TableProperties },
  { to: '/documents', label: 'Review workspace', icon: FileSearch },
  { to: '/queue', label: 'Findings & decisions', icon: ListChecks },
  { to: '/commitments', label: 'Commitments & conflicts', icon: GitCompareArrows },
  { to: '/obligations', label: 'Obligations & deadlines', icon: CalendarClock },
  { to: '/ask', label: 'Ask the contracts', icon: MessageSquareText },
  { to: '/upload', label: 'Upload contract', icon: FileUp },
  { to: '/data-quality', label: 'Tracker data quality', icon: Database },
  { to: '/presentation', label: 'Project presentation', icon: Presentation_ },
]

export default function App() {
  const hash = useHash()
  const [meta, setMeta] = useState<Meta | null>(null)
  const [metaErr, setMetaErr] = useState<string | null>(null)
  const [reviewer, setReviewerState] = useState(() => readLS('ciq.reviewer', 'Karandeep'))
  const [open, setOpen] = useState(false)
  const setReviewer = (s: string) => { setReviewerState(s); writeLS('ciq.reviewer', s) }
  const go = (h: string) => { window.location.hash = h }

  useEffect(() => { api.meta().then(setMeta).catch(e => setMetaErr(String(e.message || e))) }, [])
  useEffect(() => { setOpen(false) }, [hash])

  const [path, ...rest] = hash.split('/').filter(Boolean)
  const param = decodeURIComponent(rest.join('/'))
  // The presentation is a full-screen deck, rendered outside the app shell. It works without the API.
  if (path === 'presentation') return <Presentation key={hash} initial={param} />
  let page
  switch (path) {
    case undefined: page = <Dashboard />; break
    case 'register': page = <Register />; break
    case 'documents': page = <DocumentsPage />; break
    case 'doc': page = <Workspace docId={param.split('?')[0]} />; break
    case 'queue': page = <ReviewQueue />; break
    case 'commitments': page = <Commitments />; break
    case 'obligations': page = <Obligations />; break
    case 'ask': page = <Ask initialDoc={param || null} />; break
    case 'upload': page = <Upload />; break
    case 'data-quality': page = <DataQuality />; break
    default: page = <div className="state">Page not found. <a href="#/">Go to dashboard</a></div>
  }
  const active = '/' + (path ?? '')
  return (
    <AppCtx.Provider value={{ meta, reviewer, setReviewer, go }}>
      <div className="shell">
        <nav className={`sidebar ${open ? 'open' : ''}`} aria-label="Main">
          <div className="brand">
            <BookOpenCheck size={26} aria-hidden />
            <div><b>AtliQ ContractIQ</b><small>Contract intelligence MVP</small></div>
          </div>
          <div className="nav">
            {NAV.map(n => {
              const isActive = n.to === active || (n.to === '/documents' && active === '/doc')
              return (
                <a key={n.to} href={'#' + n.to} aria-current={isActive ? 'page' : undefined}>
                  <n.icon size={17} aria-hidden />{n.label}
                </a>
              )
            })}
          </div>
          <div className="foot">
            <ShieldCheck size={14} aria-hidden style={{ verticalAlign: '-2px' }} /> Decision support only. ContractIQ never signs, approves or sends contracts.
          </div>
        </nav>
        <div className="main">
          <header className="topbar">
            <button className="btn menu-btn" onClick={() => setOpen(o => !o)} aria-label="Open navigation"><Menu size={18} /></button>
            {meta ? (
              meta.ai.available
                ? <span className="badge sev-Low" title={meta.ai.disclosure}><Bot size={12} aria-hidden />AI available · {meta.ai.provider} · {meta.ai.model} · consent asked per request</span>
                : <span className="badge sev-Medium" title={meta.ai.disclosure}><ShieldAlert size={12} aria-hidden />DEMO MODE — AI disabled, rules + local search only</span>
            ) : metaErr ? <span className="badge sev-Critical">Server unreachable</span> : <span className="muted small">Connecting…</span>}
            {meta && <span className="badge tag" title="All date logic uses this review date (dataset README: treat today as 2026-09-28)">Review date {meta.as_of}</span>}
            <span className="spacer" />
            <label className="row small" htmlFor="reviewer">Reviewer
              <input id="reviewer" type="text" value={reviewer} onChange={e => setReviewer(e.target.value)} style={{ width: 140 }} aria-describedby="rv-hint" />
            </label>
            <span id="rv-hint" className="sr-only">Name recorded with each review decision</span>
          </header>
          <main className="content">
            {metaErr && <div className="banner err" role="alert" style={{ marginBottom: 16 }}>Cannot reach the ContractIQ API: {metaErr}. Start it with <code>python run.py</code>.</div>}
            {page}
          </main>
        </div>
      </div>
    </AppCtx.Provider>
  )
}
