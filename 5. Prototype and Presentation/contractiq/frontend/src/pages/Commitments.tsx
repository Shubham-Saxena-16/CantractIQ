import { useState } from 'react'
import { AlertTriangle, History } from 'lucide-react'
import { api } from '../api'
import { Empty, ErrorState, EvidenceTag, Fact, Loading, SeverityBadge, useLoad } from '../components'

export default function Commitments() {
  const { data, error, loading, reload } = useLoad(() => api.commitments())
  const [tab, setTab] = useState<'register' | 'conflicts' | 'history' | 'precedents'>('conflicts')
  if (loading) return <Loading label="Building commitment register…" />
  if (error) return <ErrorState error={error} onRetry={reload} />
  const reg = data.register as any[]
  return (
    <div className="stack">
      <div className="page-head"><div><h1>Commitments & conflicts</h1>
        <div className="sub">“What has AtliQ already promised not to do?” — built only from executed contracts. Notes and tracker rows appear as context, never as the commitment.</div></div></div>
      <div className="banner info small"><AlertTriangle size={16} aria-hidden /><div>{data.coverage.statement} “No conflict found” is not “no conflict exists”.
        {data.coverage.not_in_repository.length > 0 && <details><summary style={{ cursor: 'pointer' }}>Missing executed copies ({data.coverage.not_in_repository.length})</summary><ul>{data.coverage.not_in_repository.map((x: string) => <li key={x}>{x}</li>)}</ul></details>}</div></div>
      <div className="card">
        <div className="tabs" role="tablist">
          {([['conflicts', `Possible conflicts (${data.conflicts.length})`], ['register', `Commitment register (${reg.length})`], ['history', `Issues between signed contracts (${data.historical.length})`], ['precedents', `Negotiation history (${data.precedents.length})`]] as const).map(([k, l]) =>
            <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{l}</button>)}
        </div>
        <div className="card-pad stack">
          {tab === 'register' && (reg.length === 0 ? <Empty title="No commitments found" /> : reg.map(c => (
            <div key={c.id} className="finding" style={{ padding: 12 }}>
              <div className="row"><b>{c.label}</b><span className="muted">— {c.counterparty}</span>
                <span className={`badge ${c.status === 'active' ? 'sev-High' : c.status === 'expired' ? 'tag' : 'sev-Medium'}`}>{c.status}{c.end ? ` until ${c.end}` : ''}</span>
                {c.binds_affiliates && <span className="badge sev-Medium">Binds Affiliates</span>}<EvidenceTag label={c.evidence_label} /></div>
              <div className="muted small" style={{ margin: '4px 0' }}>Entity: {c.atliq_entity ?? 'unknown'} · Sectors: {c.sectors.join(', ') || '—'} · Geography: {c.geographies.join(', ') || 'not limited / not stated'} · End basis: {c.end_basis}
                {c.tracker_id && <> · Tracker {c.tracker_id} restrictive_clauses: <b>{c.tracker_restrictive_field || 'blank'}</b></>}</div>
              <Fact label={c.filename} refText={c.clause_ref} excerpt={c.excerpt} />
              {c.definitions.map((d: any, i: number) => <Fact key={i} label="Definition" refText={d.ref} excerpt={d.excerpt} />)}
              {c.rate_card?.length > 0 && <div className="small">Rate card under MFN: {c.rate_card.map((r: any) => `${r.role} $${r.rate}`).join(' · ')}</div>}
              {c.named_assets?.length > 0 && <div className="small">Named assets in that agreement: <b>{c.named_assets.join(', ')}</b></div>}
              {c.waivers.map((w: any, i: number) => <div key={i} className="banner info small">Waiver/consent on file: {w.filename} — “{w.scope_excerpt.slice(0, 300)}”</div>)}
              <a className="small" href={`#/doc/${c.doc_id}`}>Open source contract</a>
            </div>)))}
          {tab === 'conflicts' && (data.conflicts.length === 0 ? <Empty title="No possible conflicts detected" /> : data.conflicts.map((c: any) => (
            <div key={c.id} className="finding" style={{ padding: 12 }}>
              <div className="row"><SeverityBadge s={c.severity} /><b>{c.title}</b><span className="badge tag">confidence {c.confidence}</span></div>
              <div className="small" style={{ margin: '6px 0' }}>New: <a href={`#/doc/${c.new_doc_id}`}>{c.new_counterparty || c.new_title}</a> <span className="muted">({c.new_filename})</span></div>
              <div className="grid two">
                <div>{c.new_evidence.slice(0, 2).map((e: any, i: number) => <Fact key={i} label="New agreement (draft)" refText={e.ref} excerpt={e.excerpt} />)}</div>
                <div><Fact label={`Prior: ${c.prior_filename}`} refText={c.prior_ref} excerpt={c.prior_excerpt} evidence={c.prior_evidence_label} /></div>
              </div>
              <div className="interp small" style={{ marginTop: 8 }}><b>Rationale (rule-based interpretation):</b> {c.rationale}</div>
              <div className="small" style={{ marginTop: 6 }}><b>Facts needed to confirm:</b><ul style={{ margin: 0, paddingLeft: 18 }}>{c.missing_facts.map((m: string, i: number) => <li key={i}>{m}</li>)}</ul></div>
            </div>)))}
          {tab === 'history' && (data.historical.length === 0 ? <Empty title="No issues between executed contracts detected" /> : data.historical.map((h: any) => (
            <div key={h.id} className="finding" style={{ padding: 12 }}>
              <div className="row"><History size={16} aria-hidden /><SeverityBadge s={h.severity} /><b>{h.title}</b><span className="badge tag">confidence {h.confidence}</span></div>
              <div className="grid two" style={{ marginTop: 8 }}><Fact label={h.a.filename} refText={h.a.ref} excerpt={h.a.excerpt} /><Fact label={h.b.filename} refText={h.b.ref} excerpt={h.b.excerpt} /></div>
              <div className="small muted" style={{ marginTop: 6 }}>Link: {h.link_evidence}</div>
              <ul className="small">{h.missing_facts.map((m: string, i: number) => <li key={i}>{m}</li>)}</ul>
            </div>)))}
          {tab === 'precedents' && <>
            <p className="muted small">Jay's reconstruction (negotiation_notes.md): incomplete and unreviewed. It records what happened, not whether it was right. Exceptions apply only to their deal.</p>
            {data.precedents.map((p: any, i: number) => (
              <div key={i} className="finding" style={{ padding: 12 }}>
                <div className="row"><b>{p.title}</b>{p.is_exception && <span className="badge sev-High">Contains deal-specific exception</span>}<span className="badge tag">{p.outcome}</span></div>
                <ul className="small" style={{ margin: '6px 0 0', paddingLeft: 18 }}>{p.lines.map((l: string, j: number) => <li key={j}>{l}</li>)}</ul>
              </div>))}</>}
        </div>
      </div>
    </div>
  )
}
