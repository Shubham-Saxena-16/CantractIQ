import { useState } from 'react'
import { BookMarked, ClipboardCheck, Flag, History, Lightbulb, Scale } from 'lucide-react'
import { api, type Finding, type Review } from './api'
import { DISPOSITION_LABELS, Fact, SeverityBadge, EvidenceTag } from './components'
import { useApp } from './App'

export function ReviewControls({ f, onSaved }: { f: Finding; onSaved: (r: Review) => void }) {
  const { reviewer, meta } = useApp()
  const [disp, setDisp] = useState(f.review?.disposition ?? '')
  const [note, setNote] = useState('')
  const [follow, setFollow] = useState(!!f.review?.follow_up)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)
  const [hist, setHist] = useState<any[] | null>(null)
  const save = async () => {
    if (!reviewer.trim()) { setErr('Enter your name in the Reviewer box at the top first.'); return }
    setBusy(true); setErr(null); setOk(null)
    try {
      const r = await api.review(f.id, { disposition: disp || undefined, note: note || undefined, follow_up: follow, reviewer: reviewer.trim() })
      onSaved(r.review); setNote(''); setOk('Saved to the audit trail.')
      if (hist) setHist(await api.history(f.id))
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="card-pad" style={{ background: 'var(--surface-2)', borderRadius: 6, padding: 12 }}>
      <div className="section-label"><ClipboardCheck size={13} aria-hidden />Human review</div>
      <div className="row">
        <label className="field" style={{ flex: '1 1 180px' }}>Disposition
          <select value={disp} onChange={e => setDisp(e.target.value)}>
            <option value="">— choose —</option>
            {(meta?.dispositions ?? Object.keys(DISPOSITION_LABELS)).map(d => <option key={d} value={d}>{DISPOSITION_LABELS[d] ?? d}</option>)}
          </select></label>
        <label className="row small" style={{ marginTop: 18 }}><input type="checkbox" checked={follow} onChange={e => setFollow(e.target.checked)} /><Flag size={13} aria-hidden />Follow-up</label>
      </div>
      <label className="field" style={{ marginTop: 8 }}>Note (optional)
        <textarea rows={2} value={note} onChange={e => setNote(e.target.value)} placeholder="Reasoning, questions for counsel, next steps…" /></label>
      <div className="row" style={{ marginTop: 8 }}>
        <button className="btn primary sm" onClick={save} disabled={busy}>{busy ? 'Saving…' : 'Save decision'}</button>
        <button className="btn sm ghost" onClick={async () => setHist(hist ? null : await api.history(f.id))}><History size={13} aria-hidden />{hist ? 'Hide' : 'Show'} history</button>
        {f.review?.reviewer && <span className="muted small">Last: {DISPOSITION_LABELS[f.review.disposition ?? ''] ?? 'note only'} by {f.review.reviewer}, {f.review.created_at?.replace('T', ' ').slice(0, 16)} UTC</span>}
        {ok && <span className="small" role="status" style={{ color: 'var(--ok)' }}>{ok}</span>}
        {err && <span className="small" role="alert" style={{ color: 'var(--crit)' }}>{err}</span>}
      </div>
      {hist && (hist.length === 0 ? <p className="muted small" style={{ marginTop: 8 }}>No decisions recorded yet.</p> :
        <ol className="small" style={{ marginTop: 8, paddingLeft: 18 }}>{hist.map(h =>
          <li key={h.id}>{h.created_at.replace('T', ' ').slice(0, 16)} — <b>{h.reviewer}</b>: {DISPOSITION_LABELS[h.disposition] ?? '(no disposition)'}{h.follow_up ? ' · follow-up' : ''}{h.note && <> — “{h.note}”</>}</li>)}</ol>)}
      <p className="muted small" style={{ marginTop: 6 }}>Decisions are append-only; earlier decisions are never overwritten. Recording a decision does not approve or sign anything.</p>
    </div>
  )
}

export default function FindingCard({ f, onJump, defaultOpen = false }: { f: Finding; onJump?: (idx: number) => void; defaultOpen?: boolean }) {
  const [review, setReview] = useState(f.review)
  const c = f.conflict
  return (
    <details className="finding" open={defaultOpen}>
      <summary>
        <SeverityBadge s={f.severity} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="ftitle">{f.title}</div>
          <div className="meta">{f.category_label} · {f.fact?.ref ?? 'no single clause'} · confidence {f.confidence} · {f.perspective}</div>
        </div>
        {review?.disposition && <span className="badge ok">{DISPOSITION_LABELS[review.disposition]}</span>}
        {review?.follow_up ? <span className="badge sev-High"><Flag size={11} aria-hidden />Follow-up</span> : null}
      </summary>
      <div className="body">
        <div className="section-label">Fact — from the contract</div>
        {f.fact ? <Fact refText={f.fact.ref} excerpt={f.fact.excerpt} evidence={f.evidence_label}
          onJump={onJump && f.fact.clause_idx !== undefined ? () => onJump(f.fact!.clause_idx!) : undefined} />
          : <p className="muted small">This finding is not tied to a single clause (see interpretation).</p>}
        {f.related_facts?.length > 0 && f.related_facts.map((r, i) => <Fact key={i} label="Related clause" refText={r.ref} excerpt={r.excerpt}
          onJump={onJump && r.clause_idx !== undefined ? () => onJump(r.clause_idx!) : undefined} />)}
        {Object.keys(f.extracted || {}).length > 0 && (
          <div className="chips small">{Object.entries(f.extracted).filter(([, v]) => v !== null && v !== '' && v !== undefined).map(([k, v]) =>
            <span key={k} className="badge tag">{k.replace(/_/g, ' ')}: {String(v)}</span>)}</div>)}

        {c && (<>
          <div className="section-label"><Scale size={13} aria-hidden />Prior commitment</div>
          <Fact label={`${c.prior_filename}`} refText={c.prior_ref} excerpt={c.prior_excerpt} evidence={c.prior_evidence_label} />
          {c.prior_definitions?.map((d, i) => <Fact key={i} label="Definition used by that clause" refText={d.ref} excerpt={d.excerpt} />)}
          <div className="kv small"><dt>Status</dt><dd>{c.prior_status}{c.prior_end ? ` until ${c.prior_end}` : ''} <span className="muted">({c.prior_end_basis})</span></dd>
            {c.matched_sectors && <><dt>Matched sector</dt><dd>{c.matched_sectors.join(', ')}</dd></>}
            {c.matched_geographies && <><dt>Matched geography</dt><dd>{c.matched_geographies.join(', ')}</dd></>}
            {c.prior_rate_rows && <><dt>Prior rate rows</dt><dd className="mono">{c.prior_rate_rows.join(' ; ')}</dd></>}
          </div>
          {c.waiver_assessment && c.waiver_assessment.length > 0 && c.waiver_assessment.map((w, i) =>
            <div key={i} className={`banner ${w.covers_this_deal ? 'info' : 'warn'}`}>Waiver on file: <b>{w.filename}</b> — {w.covers_this_deal ? 'appears to cover this counterparty (verify).' : 'does NOT name this counterparty.'} <span className="small">“{w.scope_excerpt.slice(0, 260)}”</span></div>)}
          {c.context?.map((x, i) => <div key={i} className="banner info small"><b>Context ({x.source}):</b> {x.text}</div>)}
          <div className="section-label">Facts still needed before treating this as a confirmed conflict</div>
          <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>{c.missing_facts.map((m, i) => <li key={i}>{m}</li>)}</ul>
        </>)}

        <div className="section-label"><Lightbulb size={13} aria-hidden />Interpretation — rule-based, not legal advice</div>
        <div className="interp">{f.interpretation}</div>
        <div className="section-label">Suggested next step</div>
        <div className="interp">{f.recommendation}</div>
        {f.checklist && (<>
          <div className="section-label"><BookMarked size={13} aria-hidden />Company preference</div>
          <div className="small">{f.checklist.items.map((it, i) => <div key={i}>“{it}”</div>)}<span className="muted">{f.checklist.evidence_label} ({f.checklist.source})</span></div>
        </>)}
        {f.precedents?.length > 0 && (<>
          <div className="section-label">Related negotiation history</div>
          {f.precedents.map((p, i) => (
            <div key={i} className="small" style={{ marginBottom: 4 }}>
              <b>{p.title}</b> {p.is_exception ? <span className="badge sev-High">Deal-specific exception — not policy</span> : <EvidenceTag label="Negotiation note (unverified)" />}
              <div className="muted">{p.excerpt}</div>
            </div>))}
        </>)}
        <ReviewControls f={{ ...f, review }} onSaved={setReview} />
      </div>
    </details>
  )
}
