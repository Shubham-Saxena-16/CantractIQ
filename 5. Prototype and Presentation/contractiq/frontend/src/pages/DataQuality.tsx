import { useMemo, useState } from 'react'
import { api } from '../api'
import { Empty, ErrorState, Loading, SeverityBadge, useLoad } from '../components'

export default function DataQuality() {
  const { data, error, loading, reload } = useLoad(() => api.dataQuality())
  const [code, setCode] = useState('')
  const rows = useMemo(() => (data?.issues ?? []).filter(i => !code || i.code === code), [data, code])
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />
  return (
    <div className="stack">
      <div className="page-head"><div><h1>Tracker data quality</h1>
        <div className="sub">Checks on contract_tracker.csv against the documents. Issues are reported for a person to reconcile — ContractIQ never edits the tracker or silently picks an authoritative row.</div></div></div>
      <div className="card">
        <div className="toolbar">
          <div className="chips">
            <button className={`btn sm ${code === '' ? 'primary' : ''}`} onClick={() => setCode('')}>All ({data!.issues.length})</button>
            {Object.entries(data!.counts).map(([c, n]) => <button key={c} className={`btn sm ${code === c ? 'primary' : ''}`} onClick={() => setCode(c)}>{c.replace(/_/g, ' ')} ({n})</button>)}
          </div>
        </div>
        {rows.length === 0 ? <Empty title="No issues" /> : <div className="table-wrap"><table className="data">
          <thead><tr><th>Severity</th><th>Row</th><th>Issue</th><th>Detail</th></tr></thead>
          <tbody>{rows.map((i, n) => <tr key={n}><td><SeverityBadge s={i.severity} /></td><td className="mono">{i.contract_id ?? (i.doc_id ? <a href={`#/doc/${i.doc_id}`}>document</a> : '—')}</td>
            <td>{i.code.replace(/_/g, ' ')}</td><td>{i.message}</td></tr>)}</tbody></table></div>}
      </div>
    </div>
  )
}
