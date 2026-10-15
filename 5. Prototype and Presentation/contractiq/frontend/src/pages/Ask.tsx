import { useState } from 'react'
import { Bot, Search, ShieldAlert, AlertTriangle } from 'lucide-react'
import { api } from '../api'
import { EvidenceTag, Fact, Loading, SeverityBadge, useLoad } from '../components'
import { useApp } from '../App'

const EXAMPLES = [
  'What has AtliQ promised not to do in the GCC?',
  'What payment term does the Harrington agreement use?',
  'Is there a most favoured customer pricing commitment?',
  'Which entity will invoice TravelHub?',
  'Do we have a signed BAA with Harrington?',
]

export default function Ask({ initialDoc }: { initialDoc: string | null }) {
  const { meta } = useApp()
  const docs = useLoad(() => api.documents())
  const [docId, setDocId] = useState<string>(initialDoc ?? '')
  const [q, setQ] = useState('')
  const [useAi, setUseAi] = useState(false)
  const [consent, setConsent] = useState(false)
  const [res, setRes] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const aiOn = !!meta?.ai.available

  const ask = async (question = q) => {
    if (question.trim().length < 3) { setErr('Type a question first.'); return }
    setBusy(true); setErr(null); setRes(null)
    try { setRes(await api.ask({ question, doc_id: docId || null, use_ai: aiOn && useAi, consent })) }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="stack">
      <div className="page-head"><div><h1>Ask the contracts</h1>
        <div className="sub">Answers come only from the documents and tracker in this repository, with source references. If the evidence is not there, ContractIQ says so.</div></div></div>
      <div className="card card-pad stack">
        <div className="row">
          <label className="field" style={{ flex: '1 1 260px' }}>Scope
            <select value={docId} onChange={e => setDocId(e.target.value)}>
              <option value="">All contracts, notes and tracker</option>
              {(docs.data ?? []).map(d => <option key={d.doc_id} value={d.doc_id}>{d.counterparty_name || d.title} — {d.kind}</option>)}
            </select></label>
        </div>
        <form className="row" onSubmit={e => { e.preventDefault(); ask() }}>
          <label className="sr-only" htmlFor="q">Question</label>
          <input id="q" type="text" value={q} onChange={e => setQ(e.target.value)} placeholder="e.g. What is the liability cap?" style={{ flex: 1, minWidth: 220 }} />
          <button className="btn primary" type="submit" disabled={busy}><Search size={15} aria-hidden />Ask</button>
        </form>
        <div className="chips">{EXAMPLES.map(x => <button key={x} className="btn sm" onClick={() => { setQ(x); ask(x) }}>{x}</button>)}</div>
        {aiOn ? (
          <div className="banner ai small"><Bot size={16} aria-hidden /><div>
            <label className="row"><input type="checkbox" checked={useAi} onChange={e => setUseAi(e.target.checked)} />Generate an AI answer from the retrieved passages ({meta?.ai.provider} · {meta?.ai.model})</label>
            {useAi && <label className="row" style={{ marginTop: 4 }}><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />I confirm the question and the retrieved excerpts listed below (up to 13) may be sent to {meta?.ai.endpoint}.</label>}
          </div></div>
        ) : <div className="banner demo small"><ShieldAlert size={16} aria-hidden /><div><b>Demo mode:</b> no AI key configured. You will get ranked source passages and related rule findings, not a generated answer.</div></div>}
      </div>

      {busy && <Loading label="Searching the repository…" />}
      {err && <div className="banner err" role="alert">{err}</div>}
      {res && (
        <div className="stack" aria-live="polite">
          {res.ai_error && <div className="banner warn small">{res.ai_error}</div>}
          {res.mode === 'ai' && res.ai ? (
            <section className="card card-pad stack">
              <div className="row"><h2>Answer</h2><span className="badge tag"><Bot size={12} aria-hidden />AI-generated from cited passages</span>
                {res.ai.insufficient_evidence && <span className="badge sev-High"><AlertTriangle size={12} aria-hidden />Insufficient evidence</span>}</div>
              <div className="answer">{res.ai.answer}</div>
              {res.ai.interpretation_notes?.length > 0 && <div className="ai-block small"><b>Interpretation (not legal advice):</b><ul style={{ margin: 0, paddingLeft: 18 }}>{res.ai.interpretation_notes.map((n: string, i: number) => <li key={i}>{n}</li>)}</ul></div>}
              {res.ai.missing?.length > 0 && <div className="small"><b>What should be checked:</b><ul style={{ margin: 0, paddingLeft: 18 }}>{res.ai.missing.map((n: string, i: number) => <li key={i}>{n}</li>)}</ul></div>}
              <div className="section-label">Verified citations</div>
              {res.ai.citations.length === 0 ? <p className="muted small">No citation could be verified against the sources — treat the answer as unverified.</p> :
                res.ai.citations.map((c: any, i: number) => <Fact key={i} label={`${c.passage} · ${c.source}`} refText={c.ref} excerpt={c.quote} evidence={c.evidence_label} />)}
              <p className="muted small">{res.ai.verification}</p>
            </section>
          ) : (
            <div className={`banner ${res.insufficient_evidence ? 'warn' : 'demo'}`}>{res.insufficient_evidence ? <AlertTriangle size={18} aria-hidden /> : <ShieldAlert size={18} aria-hidden />}<div>{res.answer}</div></div>
          )}
          {res.related_findings?.length > 0 && <section className="card card-pad stack"><h2>Related findings in this contract</h2>
            {res.related_findings.map((f: any) => <div key={f.id} className="row"><SeverityBadge s={f.severity} /><a href={`#/doc/${res.doc_id}`}>{f.title}</a><span className="muted small mono">{f.ref}</span></div>)}</section>}
          <section className="card card-pad stack">
            <h2>Source passages {res.mode === 'ai' ? 'sent to the AI' : 'found'} ({res.passages.length})</h2>
            {res.passages.length === 0 ? <p className="muted">No matching passages.</p> : res.passages.map((p: any) => (
              <div key={p.n}>
                <div className="row small"><b>P{p.n}</b>{p.doc_id ? <a href={`#/doc/${p.doc_id}`}>{p.source}</a> : <span>{p.source}</span>}<span className="mono muted">{p.ref}</span><EvidenceTag label={p.evidence_label} /><span className="muted">match {Math.round(p.coverage * 100)}%</span></div>
                <div className="fact" style={{ marginTop: 4 }}>{p.text.replace(/\*\*/g, '').slice(0, 1200)}</div>
              </div>))}
          </section>
        </div>)}
    </div>
  )
}
