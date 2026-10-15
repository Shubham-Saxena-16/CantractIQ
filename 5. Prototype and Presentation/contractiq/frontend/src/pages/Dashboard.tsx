import { AlertTriangle, CalendarClock, FileClock, Files, GitCompareArrows, Database, Scale } from 'lucide-react'
import { api } from '../api'
import { ErrorState, Loading, SeverityBadge, useLoad, EvidenceTag, Empty } from '../components'

export default function Dashboard() {
  const { data, error, loading, reload } = useLoad(() => api.dashboard())
  if (loading) return <Loading label="Analysing contract repository…" />
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return null
  const k = data.kpis
  const drafts = data.high_risk.filter((h: any) => h.kind !== 'executed')
  const executed = data.high_risk.filter((h: any) => h.kind === 'executed')
  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Contract dashboard</h1>
          <div className="sub">Built from contract_tracker.csv and the documents in Dataset/. Figures are as of {data.as_of}.</div>
        </div>
      </div>

      <div className="grid kpis">
        <a className="card kpi" href="#/register" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="icon"><Files size={18} aria-hidden /></div>
          <div><div className="value">{k.total_contracts}</div><div className="label">Total contracts (tracker rows)</div>
            <div className="hint">{k.suspected_duplicates.length ? `Incl. suspected duplicate rows ${k.suspected_duplicates.join(' / ')}` : 'No duplicates detected'}</div></div>
        </a>
        <a className="card kpi" href="#/documents" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="icon"><FileClock size={18} aria-hidden /></div>
          <div><div className="value">{k.under_review}</div><div className="label">Under review</div>
            <div className="hint">Tracker status "In review"{k.under_review_blank_status ? ` · +${k.under_review_blank_status} drafts with blank status` : ''}</div></div>
        </a>
        <a className="card kpi" href="#/queue" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="icon" style={{ color: 'var(--crit)' }}><AlertTriangle size={18} aria-hidden /></div>
          <div><div className="value">{k.high_risk_drafts}</div><div className="label">High-risk drafts</div>
            <div className="hint">Critical/High finding in a draft · {k.high_risk_executed} executed contracts also carry High+ exposure</div></div>
        </a>
        <a className="card kpi" href="#/obligations" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="icon"><CalendarClock size={18} aria-hidden /></div>
          <div><div className="value">{k.upcoming_expirations}</div><div className="label">Expiring in {k.expiry_window_days} days</div>
            <div className="hint">From tracker expiry dates (unverified)</div></div>
        </a>
        <a className="card kpi" href="#/commitments" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="icon"><GitCompareArrows size={18} aria-hidden /></div>
          <div><div className="value">{k.conflicts}</div><div className="label">Possible conflicts</div>
            <div className="hint">With executed commitments · need confirmation</div></div>
        </a>
        <a className="card kpi" href="#/queue" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="icon"><Scale size={18} aria-hidden /></div>
          <div><div className="value">{k.escalated}</div><div className="label">Escalated to counsel</div>
            <div className="hint">{k.follow_up} item(s) flagged for follow-up</div></div>
        </a>
      </div>

      <div className="grid two">
        <section className="card" aria-labelledby="hr-h">
          <div className="card-head"><h2 id="hr-h">Drafts needing attention</h2><span className="right muted small">Highest severity first</span></div>
          {drafts.length === 0 ? <Empty title="No high-risk drafts" /> : (
            <div className="table-wrap"><table className="data">
              <thead><tr><th>Contract</th><th>Risk</th><th>Critical</th><th>High</th><th>Conflicts</th></tr></thead>
              <tbody>{drafts.map((h: any) => (
                <tr key={h.doc_id} className="click" onClick={() => (window.location.hash = `/doc/${h.doc_id}`)}>
                  <td><a href={`#/doc/${h.doc_id}`}>{h.counterparty || h.title}</a><div className="muted small">{h.title} · {h.tracker_ids.join(', ') || 'no tracker row'}</div></td>
                  <td><SeverityBadge s={h.risk_level} /></td><td>{h.critical}</td><td>{h.high}</td><td>{h.conflicts || '—'}</td>
                </tr>))}</tbody>
            </table></div>)}
        </section>

        <div className="stack">
          <section className="card" aria-labelledby="dl-h">
            <div className="card-head"><h2 id="dl-h">Requested review deadlines</h2><span className="right badge tag">From tracker notes — unverified</span></div>
            {data.review_deadlines.length === 0 ? <Empty title="No deadlines found in tracker notes" /> : (
              <div className="table-wrap"><table className="data">
                <thead><tr><th>Due</th><th>Contract</th><th>Requested by</th></tr></thead>
                <tbody>{data.review_deadlines.map((o: any) => (
                  <tr key={o.id}><td className="nowrap">{o.due_date}</td><td>{o.title.replace('Review/signature deadline requested ', '')}<div className="muted small">{o.tracker_id}</div></td><td>{o.requested_by || '—'}</td></tr>
                ))}</tbody></table></div>)}
          </section>
          <section className="card" aria-labelledby="ex-h">
            <div className="card-head"><h2 id="ex-h">Upcoming & recent expirations</h2></div>
            {data.upcoming_expirations.length + data.recently_expired.length === 0 ? <Empty title="Nothing expiring" /> : (
              <div className="table-wrap"><table className="data">
                <thead><tr><th>Expiry</th><th>Contract</th><th>Status</th></tr></thead>
                <tbody>
                  {data.upcoming_expirations.map((r: any) => (
                    <tr key={r.contract_id}><td className="nowrap">{r.expiry_date}<div className="small" style={{ color: 'var(--high)' }}>in {r.days_left} days</div></td>
                      <td>{r.counterparty} — {r.doc_type}<div className="muted small">{r.contract_id} · {r.notes}</div></td><td>{r.status}</td></tr>))}
                  {data.recently_expired.map((r: any) => (
                    <tr key={r.contract_id}><td className="nowrap">{r.expiry_date}<div className="small muted">expired {r.days_ago} days ago</div></td>
                      <td>{r.counterparty} — {r.doc_type}<div className="muted small">{r.contract_id} · {r.notes}</div></td><td>{r.status} <span className="badge tag">stale?</span></td></tr>))}
                </tbody></table></div>)}
          </section>
        </div>
      </div>

      <div className="grid two">
        <section className="card" aria-labelledby="ex2-h">
          <div className="card-head"><h2 id="ex2-h">Executed contracts with High+ exposure</h2><span className="right muted small">"Do any other signed contracts have the same problem?"</span></div>
          <div className="table-wrap"><table className="data">
            <thead><tr><th>Contract</th><th>Evidence</th><th>Risk</th><th>Crit / High</th></tr></thead>
            <tbody>{executed.map((h: any) => (
              <tr key={h.doc_id} className="click" onClick={() => (window.location.hash = `/doc/${h.doc_id}`)}>
                <td><a href={`#/doc/${h.doc_id}`}>{h.counterparty || h.title}</a><div className="muted small">{h.title}</div></td>
                <td><EvidenceTag label={h.evidence_label} /></td><td><SeverityBadge s={h.risk_level} /></td><td>{h.critical} / {h.high}</td>
              </tr>))}</tbody></table></div>
        </section>
        <section className="card" aria-labelledby="dq-h">
          <div className="card-head"><h2 id="dq-h">Tracker status & data quality</h2><a className="right btn sm" href="#/data-quality"><Database size={14} aria-hidden />Details</a></div>
          <div className="card-pad stack">
            <div className="chips">{Object.entries(data.status_breakdown).map(([s, n]) => <span key={s} className="badge tag">{s}: {n as number}</span>)}</div>
            <div className="chips">{Object.entries(data.data_quality_counts).map(([c, n]) => <span key={c} className="badge sev-Medium">{c.replace(/_/g, ' ')}: {n as number}</span>)}</div>
            <p className="muted small">The tracker is treated as metadata only. A "Signed" status without an executed copy is reported as unverified, never as proof of execution.</p>
          </div>
        </section>
      </div>
    </div>
  )
}
