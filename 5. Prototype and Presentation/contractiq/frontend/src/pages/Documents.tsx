import { useMemo, useState } from 'react'
import { api } from '../api'
import { Empty, ErrorState, EvidenceTag, Loading, SeverityBadge, useLoad } from '../components'

export default function DocumentsPage() {
  const { data, error, loading, reload } = useLoad(() => api.documents())
  const [kind, setKind] = useState('pending')
  const [q, setQ] = useState('')
  const rows = useMemo(() => (data ?? []).filter(d =>
    (kind === 'all' || (kind === 'pending' ? d.kind !== 'executed' : d.kind === kind)) &&
    (!q || `${d.title} ${d.counterparty_name} ${d.filename}`.toLowerCase().includes(q.toLowerCase()))
  ), [data, kind, q])
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />
  return (
    <div className="stack">
      <div className="page-head"><div><h1>Review workspace</h1>
        <div className="sub">Pick a contract to review its findings, evidence, conflicts, companion documents and obligations.</div></div>
        <div className="actions"><a className="btn primary" href="#/upload">Upload a contract</a></div></div>
      <div className="card">
        <div className="toolbar">
          <div className="tabs" role="tablist" style={{ border: 0 }}>
            {[['pending', 'Drafts & uploads'], ['executed', 'Executed'], ['all', 'All']].map(([k, l]) =>
              <button key={k} role="tab" aria-selected={kind === k} onClick={() => setKind(k)}>{l}</button>)}
          </div>
          <input type="search" placeholder="Filter…" value={q} onChange={e => setQ(e.target.value)} aria-label="Filter documents" />
        </div>
        {rows.length === 0 ? <Empty title="No documents" /> : (
          <div className="table-wrap"><table className="data">
            <thead><tr><th>Document</th><th>Counterparty</th><th>Evidence type</th><th>Tracker</th><th>Risk</th><th>Findings</th><th>Unreviewed Crit/High</th><th>Quality</th></tr></thead>
            <tbody>{rows.map(d => {
              const n = Object.values(d.severity_counts).reduce((a, b) => a + b, 0)
              return (
                <tr key={d.doc_id} className="click" onClick={() => (window.location.hash = `/doc/${d.doc_id}`)}>
                  <td><a href={`#/doc/${d.doc_id}`}>{d.title}</a><div className="muted small mono">{d.filename}</div></td>
                  <td>{d.counterparty_name || <span className="blank">not identified</span>}</td>
                  <td><EvidenceTag label={d.evidence_label} /></td>
                  <td className="mono">{d.tracker_ids.join(', ') || <span className="blank">no match</span>}</td>
                  <td><SeverityBadge s={d.risk_level} /></td>
                  <td>{n}</td><td>{d.open_material || '—'}</td>
                  <td>{d.quality.length ? <span className="badge sev-Medium">{d.quality.length} warning{d.quality.length > 1 ? 's' : ''}</span> : <span className="muted">—</span>}</td>
                </tr>)
            })}</tbody></table></div>)}
      </div>
    </div>
  )
}
