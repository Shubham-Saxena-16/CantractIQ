import { useEffect, useState, type ReactNode } from 'react'
import { AlertCircle, AlertOctagon, AlertTriangle, CheckCircle2, FileText, Info, Inbox, Bot, Quote } from 'lucide-react'
import type { Severity } from './api'

export function SeverityBadge({ s }: { s: Severity | string | null | undefined }) {
  if (!s) return <span className="badge tag">No findings</span>
  const Icon = s === 'Critical' ? AlertOctagon : s === 'High' ? AlertTriangle : s === 'Medium' ? AlertCircle : Info
  return <span className={`badge sev-${s}`}><Icon size={12} aria-hidden />{s}</span>
}

export function EvidenceTag({ label }: { label: string }) {
  const exec = label.startsWith('Executed')
  return <span className={`badge ${exec ? 'ok' : 'tag'}`} title="Evidence type">{exec ? <CheckCircle2 size={12} aria-hidden /> : <FileText size={12} aria-hidden />}{label}</span>
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return <div className="state" role="status" aria-live="polite"><div className="spinner" aria-hidden />{label}</div>
}

export function ErrorState({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="banner err" role="alert">
      <AlertOctagon size={18} aria-hidden />
      <div><b>Something went wrong.</b> {error} {onRetry && <button className="btn sm" onClick={onRetry} style={{ marginLeft: 8 }}>Retry</button>}</div>
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="state"><Inbox size={28} aria-hidden /><b>{title}</b>{children && <div className="small">{children}</div>}</div>
}

export function Fact({ label, refText, excerpt, evidence, onJump }: { label?: string; refText?: string | null; excerpt: string; evidence?: string; onJump?: () => void }) {
  return (
    <div>
      <div className="fact-head">
        <Quote size={12} aria-hidden />{label ?? 'Extracted from contract'}{refText && <> · <span className="mono">{refText}</span></>}
        {evidence && <EvidenceTag label={evidence} />}
        {onJump && <button className="btn sm ghost" onClick={onJump}>Show in document</button>}
      </div>
      <div className="fact">{excerpt.replace(/\*\*/g, '')}</div>
    </div>
  )
}

export function AiLabel() {
  return <span className="badge tag"><Bot size={12} aria-hidden />AI interpretation</span>
}

/** Small generic data loader with loading / error / reload states. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    fn().then(d => { if (alive) setData(d) }).catch(e => { if (alive) setError(String(e.message || e)) }).finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  return { data, error, loading, reload: () => setTick(t => t + 1), setData }
}

export const fmtMoney = (v: number | null | undefined) =>
  v === null || v === undefined ? null : (v < 0 ? '-$' : '$') + Math.abs(v).toLocaleString('en-US')

export function Blank({ v, label = 'not recorded' }: { v: string | null | undefined; label?: string }) {
  return v ? <>{v}</> : <span className="blank">{label}</span>
}

export const DISPOSITION_LABELS: Record<string, string> = {
  relevant: 'Relevant', not_relevant: 'Not relevant', resolved: 'Resolved', needs_info: 'Needs information', escalate_counsel: 'Escalate to counsel',
}
