import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, Bot, Download, FileWarning, MessageSquareText, ShieldAlert } from 'lucide-react'
import { api, exportUrl, type Analysis, type Clause, type DocDetail } from '../api'
import { AiLabel, Blank, Empty, ErrorState, EvidenceTag, Fact, Loading, SeverityBadge, useLoad } from '../components'
import FindingCard from '../FindingCard'
import { useApp } from '../App'

type Tab = 'findings' | 'conflicts' | 'entity' | 'companions' | 'obligations' | 'ai' | 'context'

export default function Workspace({ docId }: { docId: string }) {
  const doc = useLoad(() => api.document(docId), [docId])
  const an = useLoad(() => api.analysis(docId), [docId])
  const [tab, setTab] = useState<Tab>('findings')
  const [hl, setHl] = useState<number | null>(null)
  const viewer = useRef<HTMLDivElement>(null)

  const jump = (idx: number) => {
    setHl(idx)
    const el = document.getElementById(`clause-${idx}`)
    if (el && viewer.current) {
      viewer.current.scrollTo({ top: el.offsetTop - viewer.current.offsetTop - 12, behavior: 'smooth' })
      el.focus({ preventScroll: true })
    }
  }

  if (doc.loading || an.loading) return <Loading label="Loading contract and analysis…" />
  if (doc.error) return <ErrorState error={doc.error} onRetry={doc.reload} />
  if (an.error) return <ErrorState error={an.error} onRetry={an.reload} />
  const d = doc.data!, a = an.data!
  const flagged = new Set(a.findings.map(f => f.fact?.clause_idx).filter((x): x is number => x !== undefined))

  const tabs: [Tab, string, number?][] = [
    ['findings', 'Findings', a.findings.length], ['conflicts', 'Prior commitments', a.conflicts.length],
    ['entity', 'Entity & law', a.entity.filter(e => !['ok', 'info'].includes(e.status)).length],
    ['companions', 'Companion docs', a.companions.filter(c => c.status !== 'present').length],
    ['obligations', 'Obligations', a.obligations.length], ['ai', 'AI review'], ['context', 'Deal context'],
  ]
  return (
    <div className="stack">
      <div className="page-head">
        <div style={{ minWidth: 0 }}>
          <a href="#/documents" className="small row"><ArrowLeft size={14} aria-hidden />All documents</a>
          <h1 style={{ marginTop: 4 }}>{d.counterparty_name || d.title}</h1>
          <div className="row" style={{ marginTop: 6 }}>
            <span className="muted">{d.title}</span><EvidenceTag label={d.evidence_label} />
            {d.tracker_ids.map(t => <span key={t} className="badge tag mono">{t}</span>)}
            <span className="muted small mono">{d.filename}</span>
          </div>
          {d.provenance && <div className="muted small" style={{ marginTop: 4 }}>Source note: {d.provenance}</div>}
        </div>
        <div className="actions">
          <a className="btn" href={`#/ask/${encodeURIComponent(docId)}`}><MessageSquareText size={15} aria-hidden />Ask about this contract</a>
          <a className="btn" href={exportUrl(docId, 'summary')} download><Download size={15} aria-hidden />Review summary (.md)</a>
          <a className="btn" href={exportUrl(docId, 'escalation')} download><Download size={15} aria-hidden />Counsel package (.md)</a>
          <a className="btn" href={exportUrl(docId, 'extracted')} download><Download size={15} aria-hidden />Extracted text (.md)</a>
        </div>
      </div>

      {!a.mode.available && <div className="banner demo"><ShieldAlert size={18} aria-hidden /><div><b>Demo mode.</b> Findings below come from deterministic rules applied to the extracted text — no AI model was used and nothing was sent externally. Each finding quotes the exact clause it relies on.</div></div>}
      {a.quality.length > 0 && <div className="banner warn"><FileWarning size={18} aria-hidden /><div><b>Extraction quality warnings</b><ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>{a.quality.map((q, i) => <li key={i}>{q.message}</li>)}</ul></div></div>}

      <div className="doc-layout">
        <div className="card">
          <div className="tabs" role="tablist" aria-label="Analysis sections">
            {tabs.map(([k, l, n]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{l}{n !== undefined && <span className="badge tag">{n}</span>}</button>)}
          </div>
          <div className="card-pad">
            {tab === 'findings' && <FindingsTab a={a} onJump={jump} />}
            {tab === 'conflicts' && <ConflictsTab a={a} onJump={jump} />}
            {tab === 'entity' && <EntityTab a={a} onJump={jump} />}
            {tab === 'companions' && <CompanionsTab a={a} />}
            {tab === 'obligations' && <ObligationsTab a={a} onJump={jump} />}
            {tab === 'ai' && <AiTab docId={docId} onJump={jump} />}
            {tab === 'context' && <ContextTab d={d} reload={doc.reload} />}
          </div>
        </div>
        <section className="card" aria-label="Contract text">
          <div className="card-head"><h2>Contract text</h2><span className="right muted small">{d.clause_count} clauses · flagged clauses have a left border</span></div>
          <div className="viewer" ref={viewer}><ClauseList clauses={d.clauses} hl={hl} flagged={flagged} /></div>
        </section>
      </div>
    </div>
  )
}

function ClauseList({ clauses, hl, flagged }: { clauses: Clause[]; hl: number | null; flagged: Set<number> }) {
  let lastHeading = ''
  return <>{clauses.map(c => {
    const showHead = c.heading && c.heading !== lastHeading
    lastHeading = c.heading
    return (
      <div key={c.idx}>
        {showHead && <div className="clause-heading">{c.heading}</div>}
        <div id={`clause-${c.idx}`} tabIndex={-1} className={`clause ${hl === c.idx ? 'hl' : ''} ${flagged.has(c.idx) ? 'flag' : ''}`}>
          <div className="cref">{c.ref}{c.page ? '' : ''}</div>
          {c.kind === 'table' ? <pre className="mono" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{c.text}</pre> : c.text.replace(/\*\*/g, '')}
        </div>
      </div>)
  })}</>
}

function FindingsTab({ a, onJump }: { a: Analysis; onJump: (i: number) => void }) {
  const [sev, setSev] = useState('')
  const [cat, setCat] = useState('')
  const [hideReviewed, setHide] = useState(false)
  const cats = useMemo(() => Array.from(new Set(a.findings.map(f => f.category_label))).sort(), [a])
  const list = a.findings.filter(f => (!sev || f.severity === sev) && (!cat || f.category_label === cat) && (!hideReviewed || !f.review?.disposition))
  return (
    <div className="stack">
      <div className="row">
        <select aria-label="Severity" value={sev} onChange={e => setSev(e.target.value)}><option value="">All severities</option>{['Critical', 'High', 'Medium', 'Low'].map(s => <option key={s}>{s}</option>)}</select>
        <select aria-label="Category" value={cat} onChange={e => setCat(e.target.value)}><option value="">All categories</option>{cats.map(c => <option key={c}>{c}</option>)}</select>
        <label className="row small"><input type="checkbox" checked={hideReviewed} onChange={e => setHide(e.target.checked)} />Hide reviewed</label>
        <span className="muted small right">Sorted by severity, then confidence</span>
      </div>
      {list.length === 0 ? <Empty title="No findings match">{a.findings.length === 0 ? 'The rules found no risk patterns. This does not prove the contract is risk-free — read it, and check the extraction warnings.' : null}</Empty>
        : list.map((f, i) => <FindingCard key={f.id} f={f} onJump={onJump} defaultOpen={i === 0} />)}
    </div>
  )
}

function ConflictsTab({ a, onJump }: { a: Analysis; onJump: (i: number) => void }) {
  return (
    <div className="stack">
      <div className="banner info small">{a.coverage.statement}</div>
      {a.conflicts.length === 0 ? <Empty title="No conflict with executed commitments was found">This is a qualified negative — see coverage above and the commitments considered below.</Empty> :
        a.findings.filter(f => f.conflict).map(f => <FindingCard key={f.id} f={f} onJump={onJump} defaultOpen />)}
      <details><summary className="small" style={{ cursor: 'pointer' }}>Commitments considered ({a.considered.length})</summary>
        <ul className="small">{a.considered.map((c, i) => <li key={i}>{c.commitment}: <b>{c.result}</b>{c.detail && <span className="muted"> — {c.detail}</span>}</li>)}</ul></details>
      {a.coverage.not_in_repository.length > 0 && <details><summary className="small" style={{ cursor: 'pointer' }}>Signed per tracker but not in repository — not searched ({a.coverage.not_in_repository.length})</summary>
        <ul className="small">{a.coverage.not_in_repository.map((x, i) => <li key={i}>{x}</li>)}</ul></details>}
    </div>
  )
}

function EntityTab({ a, onJump }: { a: Analysis; onJump: (i: number) => void }) {
  if (a.entity.length === 0) return <Empty title="Entity checks do not apply to this document" />
  return (
    <div className="stack">
      <p className="muted small">Rules from atliq_entities.md (finance): AtliQ Inc serves US clients only and invoices in USD; AtliQ Technologies Pvt Ltd serves all other regions (INR/USD/EUR). Checklist: governing law India for Pvt Ltd, US for Inc. Use “Deal context” to record corrections; extracted values are never overwritten.</p>
      {a.entity.map((e, i) => (
        <div key={i} className="finding" style={{ padding: 12 }}>
          <div className="row"><b>{e.check}</b>
            <span className={`badge ${e.status === 'ok' ? 'ok' : e.status === 'info' ? 'tag' : `sev-${e.severity}`}`}>{e.status}</span>
            <span>{e.value ?? <span className="blank">not found</span>}</span>{e.expected && <span className="muted small">expected: {e.expected}</span>}</div>
          <div className="small" style={{ marginTop: 4 }}>{e.note}</div>
          {e.fact && <div style={{ marginTop: 6 }}><Fact refText={e.fact.ref} excerpt={e.fact.excerpt} onJump={e.fact.clause_idx !== undefined ? () => onJump(e.fact!.clause_idx!) : undefined} /></div>}
        </div>))}
    </div>
  )
}

function CompanionsTab({ a }: { a: Analysis }) {
  if (a.companions.length === 0) return <Empty title="No companion documents expected">Based on detected signals (PHI/HIPAA, EU personal data, client NDA, contractor flow-down).</Empty>
  return (
    <div className="stack">
      <p className="muted small">Tracker-only evidence is shown as <b>unverified</b>; only an executed copy in the repository counts as present.</p>
      <div className="table-wrap"><table className="data"><thead><tr><th>Document</th><th>Status</th><th>Why expected</th><th>Evidence</th></tr></thead>
        <tbody>{a.companions.map((c, i) => <tr key={i}><td><b>{c.document}</b></td>
          <td><span className={`badge ${c.status === 'present' ? 'ok' : c.status === 'missing' ? 'sev-High' : 'sev-Medium'}`}>{c.status}</span><div className="small">{c.label}</div></td>
          <td className="small">{c.why}</td><td className="small">{c.evidence ?? <span className="blank">none</span>}{c.evidence_label && <div className="muted">{c.evidence_label}</div>}</td></tr>)}</tbody></table></div>
    </div>
  )
}

function ObligationsTab({ a, onJump }: { a: Analysis; onJump: (i: number) => void }) {
  if (a.obligations.length === 0) return <Empty title="No obligations or deadlines extracted" />
  return (
    <div className="stack">
      <p className="muted small">Owners are never guessed — unassigned items say so. Manage owners and status on the <a href="#/obligations">Obligations page</a>.</p>
      {a.obligations.map(o => (
        <div key={o.id} className="finding" style={{ padding: 12 }}>
          <div className="row"><b>{o.title}</b><span className="badge tag">{o.due_date ?? 'date unverified'}</span>
            <span className={`badge ${o.owner === 'Unassigned' ? 'sev-Medium' : 'ok'}`}>Owner: {o.owner}</span><span className="badge tag">{o.status}</span></div>
          <div className="muted small">{o.description} · basis: {o.due_basis} · source: {o.source}</div>
          {o.excerpt && <div style={{ marginTop: 6 }}><Fact refText={o.ref} excerpt={o.excerpt} onJump={o.clause_idx !== undefined && o.clause_idx !== null ? () => onJump(o.clause_idx!) : undefined} /></div>}
        </div>))}
    </div>
  )
}

function AiTab({ docId, onJump }: { docId: string; onJump: (i: number) => void }) {
  const { meta } = useApp()
  const [res, setRes] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [consent, setConsent] = useState(false)
  useEffect(() => { setRes(null); setErr(null) }, [docId])
  if (!meta?.ai.available) return (
    <div className="banner demo"><Bot size={18} aria-hidden /><div><b>AI review is not available (demo mode).</b> No AI API key is configured, so ContractIQ shows deterministic rule findings only and does not pretend they are AI output. Set <code>GROQ_API_KEY</code> or <code>ANTHROPIC_API_KEY</code> and restart to enable it.</div></div>)
  const run = async () => {
    setBusy(true); setErr(null)
    try { setRes(await api.aiReview(docId)) } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="stack">
      <div className="banner ai"><Bot size={18} aria-hidden /><div>
        <b>External processing notice.</b> Running AI review sends a capped selection (about 14,000 characters) of the most risk-relevant clauses of this contract to <b>{meta.ai.endpoint}</b> (model {meta.ai.model}). Only the clause text is sent. Results are interpretations; any finding whose quote cannot be matched verbatim in the contract is discarded.
        <label className="row" style={{ marginTop: 8 }}><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />I confirm these excerpts may be sent to {meta.ai.provider} for this request.</label>
        <button className="btn primary sm" style={{ marginTop: 8 }} onClick={run} disabled={!consent || busy}>{busy ? 'Analysing…' : 'Run AI risk review'}</button>
      </div></div>
      {busy && <Loading label="Waiting for the AI provider…" />}
      {err && <div className="banner err" role="alert">AI review failed: {err}</div>}
      {res && (<>
        <div className="banner info small">{res.verification} Provider: {res.provider} · {res.model} · {res.sent_clause_count} clauses sent.</div>
        {res.findings.length === 0 ? <Empty title="No verified AI findings" /> : res.findings.map((f: any, i: number) => (
          <div key={i} className="finding" style={{ padding: 12 }}>
            <div className="row"><SeverityBadge s={f.severity} /><b>{f.title}</b><AiLabel /><span className="muted small">{f.category}</span></div>
            <div style={{ marginTop: 6 }}><Fact label="Verified quote from contract" refText={f.ref} excerpt={f.quote} onJump={() => onJump(f.clause_idx)} /></div>
            <div className="ai-block small" style={{ marginTop: 6 }}><b>AI interpretation (not legal advice):</b> {f.explanation}<br /><b>Suggestion:</b> {f.recommendation}</div>
          </div>))}
      </>)}
    </div>
  )
}

function ContextTab({ d, reload }: { d: DocDetail; reload: () => void }) {
  const { reviewer } = useApp()
  const [field, setField] = useState('atliq_entity')
  const [value, setValue] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const t = d.tracker[0]
  const save = async () => {
    try { await api.correct(d.doc_id, { field, value, reviewer }); setMsg('Correction recorded.'); setValue(''); reload() } catch (e: any) { setMsg(e.message) }
  }
  return (
    <div className="stack">
      <div className="section-label">Extracted from the contract</div>
      <dl className="kv">
        <dt>Counterparty</dt><dd><Blank v={d.counterparty_name} label="not identified" /></dd>
        <dt>AtliQ entity</dt><dd><Blank v={d.atliq_entity} label="not identified" /></dd>
        <dt>AtliQ is called</dt><dd><Blank v={d.atliq_term} label="not identified" /> · counterparty called <Blank v={d.counterparty_term} label="not identified" /></dd>
        <dt>AtliQ's role</dt><dd>{d.atliq_role}</dd>
        <dt>Tracker link</dt><dd>{d.tracker_ids.join(', ') || 'none'} <span className="muted small">({d.tracker_match_basis})</span></dd>
      </dl>
      <div className="section-label">Tracker row {t ? t.contract_id : ''} (metadata — not proof of execution)</div>
      {t ? <dl className="kv">
        {(['doc_type', 'atliq_entity', 'client_country', 'requested_by', 'received_date', 'status', 'signed_date', 'expiry_date', 'value_usd', 'file_location', 'restrictive_clauses', 'notes'] as const).map(k =>
          <Fragment key={k}><dt>{k.replace(/_/g, ' ')}</dt><dd><Blank v={t[k]} label="blank" /></dd></Fragment>)}
      </dl> : <p className="muted small">No tracker row is linked to this document.</p>}
      {d.upload_context && Object.keys(d.upload_context).length > 0 && <>
        <div className="section-label">Context entered at upload</div>
        <dl className="kv">{Object.entries(d.upload_context).map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{Array.isArray(v) ? (v.length ? `not provided: ${v.join(', ')}` : '—') : String(v)}</dd></Fragment>)}</dl></>}
      <div className="section-label">Reviewer corrections (kept alongside, never overwriting extracted values)</div>
      {d.corrections.length === 0 ? <p className="muted small">None yet.</p> : <ul className="small">{d.corrections.map((c, i) => <li key={i}><b>{c.field}</b> → {c.value || '(cleared)'} — {c.reviewer}, {c.created_at.slice(0, 16)}</li>)}</ul>}
      <div className="row">
        <select aria-label="Field" value={field} onChange={e => setField(e.target.value)}>
          {['counterparty', 'atliq_entity', 'client_country', 'governing_law', 'currency', 'invoice_entity', 'doc_type', 'deadline'].map(f => <option key={f}>{f}</option>)}</select>
        <input type="text" aria-label="Corrected value" value={value} onChange={e => setValue(e.target.value)} placeholder="Corrected value" />
        <button className="btn sm" onClick={save} disabled={!reviewer}>Record correction</button>{msg && <span className="small">{msg}</span>}
      </div>
    </div>
  )
}
