import { useMemo, useState } from 'react'
import { Flag } from 'lucide-react'
import { api } from '../api'
import { DISPOSITION_LABELS, Empty, ErrorState, Loading, SeverityBadge, useLoad } from '../components'

export default function ReviewQueue() {
  const { data, error, loading, reload } = useLoad(() => api.queue())
  const [scope, setScope] = useState('drafts')
  const [sev, setSev] = useState('material')
  const [state, setState] = useState('')
  const rows = useMemo(() => (data ?? []).filter((r: any) =>
    (scope === 'all' || (scope === 'drafts' ? r.kind !== 'executed' : r.kind === 'executed')) &&
    (sev === '' || (sev === 'material' ? ['Critical', 'High'].includes(r.severity) : r.severity === sev)) &&
    (state === '' || (state === 'open' ? !r.review?.disposition : state === 'follow' ? r.review?.follow_up : r.review?.disposition === state))
  ), [data, scope, sev, state])
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />
  const total = (data ?? []).length
  const reviewed = (data ?? []).filter((r: any) => r.review?.disposition).length
  return (
    <div className="stack">
      <div className="page-head"><div><h1>Findings & decisions</h1>
        <div className="sub">Every finding across all contracts, with the latest human decision. {reviewed} of {total} have a disposition. Open a contract to review findings in context.</div></div></div>
      <div className="card">
        <div className="toolbar">
          <select aria-label="Scope" value={scope} onChange={e => setScope(e.target.value)}><option value="drafts">Drafts & uploads</option><option value="executed">Executed contracts</option><option value="all">All documents</option></select>
          <select aria-label="Severity" value={sev} onChange={e => setSev(e.target.value)}><option value="material">Critical + High</option><option value="">All severities</option>{['Critical', 'High', 'Medium', 'Low'].map(s => <option key={s}>{s}</option>)}</select>
          <select aria-label="Review state" value={state} onChange={e => setState(e.target.value)}><option value="">Any review state</option><option value="open">Not yet reviewed</option><option value="follow">Flagged for follow-up</option>
            {Object.entries(DISPOSITION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          <span className="muted small">{rows.length} shown</span>
        </div>
        {rows.length === 0 ? <Empty title="Nothing here" /> : <div className="table-wrap"><table className="data">
          <thead><tr><th>Severity</th><th>Finding</th><th>Contract</th><th>Source ref</th><th>Confidence</th><th>Decision</th></tr></thead>
          <tbody>{rows.map((r: any) => (
            <tr key={r.id} className="click" onClick={() => (window.location.hash = `/doc/${r.doc_id}`)}>
              <td><SeverityBadge s={r.severity} /></td>
              <td><b>{r.title}</b><div className="muted small">{r.category_label}</div></td>
              <td>{r.counterparty || r.doc_title}<div className="muted small">{r.kind}</div></td>
              <td className="mono small">{r.ref ?? '—'}</td><td>{r.confidence}</td>
              <td>{r.review?.disposition ? <span className="badge ok">{DISPOSITION_LABELS[r.review.disposition]}</span> : <span className="badge tag">Not reviewed</span>}
                {r.review?.follow_up ? <span className="badge sev-High" style={{ marginLeft: 4 }}><Flag size={11} aria-hidden />Follow-up</span> : null}
                {r.review?.reviewer && <div className="muted small">{r.review.reviewer}</div>}</td>
            </tr>))}</tbody></table></div>}
      </div>
    </div>
  )
}
