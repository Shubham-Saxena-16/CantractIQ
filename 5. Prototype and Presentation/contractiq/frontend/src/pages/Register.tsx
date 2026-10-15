import { Fragment, useMemo, useState } from 'react'
import { Search, X } from 'lucide-react'
import { api, type ContractRow } from '../api'
import { Blank, Empty, ErrorState, Loading, SeverityBadge, fmtMoney, useLoad } from '../components'

const uniq = (rows: ContractRow[], k: keyof ContractRow) => Array.from(new Set(rows.map(r => String(r[k] ?? '')))).sort()

export default function Register() {
  const { data, error, loading, reload } = useLoad(() => api.contracts())
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [entity, setEntity] = useState('')
  const [country, setCountry] = useState('')
  const [risk, setRisk] = useState('')
  const [onlyIssues, setOnlyIssues] = useState(false)
  const [open, setOpen] = useState<string | null>(null)

  const rows = useMemo(() => {
    if (!data) return []
    const ql = q.toLowerCase()
    return data.filter(r =>
      (!ql || [r.contract_id, r.counterparty, r.doc_type, r.notes, r.file_location, r.requested_by, r.restrictive_clauses].join(' ').toLowerCase().includes(ql)) &&
      (!status || (r.status || '(blank)') === status) && (!entity || (r.atliq_entity || '(blank)') === entity) &&
      (!country || (r.client_country || '(blank)') === country) &&
      (!risk || (risk === 'none' ? !r.risk_level : r.risk_level === risk)) && (!onlyIssues || r.data_quality.length > 0))
  }, [data, q, status, entity, country, risk, onlyIssues])

  if (loading) return <Loading label="Loading contract register…" />
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return null
  const opt = (k: keyof ContractRow) => uniq(data, k).map(v => <option key={v} value={v || '(blank)'}>{v || '(blank)'}</option>)
  const clear = () => { setQ(''); setStatus(''); setEntity(''); setCountry(''); setRisk(''); setOnlyIssues(false) }

  return (
    <div className="stack">
      <div className="page-head">
        <div><h1>Contract register</h1>
          <div className="sub">All {data.length} rows of contract_tracker.csv, linked to the documents found in the repository. Blank fields are shown as blank — nothing is filled in.</div></div>
      </div>
      <div className="card">
        <div className="toolbar" role="search">
          <label className="row" style={{ flex: '1 1 260px' }}><Search size={16} aria-hidden /><span className="sr-only">Search</span>
            <input type="search" placeholder="Search counterparty, type, notes, file location…" value={q} onChange={e => setQ(e.target.value)} style={{ flex: 1 }} /></label>
          <select aria-label="Status" value={status} onChange={e => setStatus(e.target.value)}><option value="">All statuses</option>{opt('status')}</select>
          <select aria-label="AtliQ entity" value={entity} onChange={e => setEntity(e.target.value)}><option value="">All entities</option>{opt('atliq_entity')}</select>
          <select aria-label="Country" value={country} onChange={e => setCountry(e.target.value)}><option value="">All countries</option>{opt('client_country')}</select>
          <select aria-label="Risk" value={risk} onChange={e => setRisk(e.target.value)}>
            <option value="">Any risk</option>{['Critical', 'High', 'Medium', 'Low'].map(s => <option key={s}>{s}</option>)}<option value="none">No document analysed</option></select>
          <label className="row small"><input type="checkbox" checked={onlyIssues} onChange={e => setOnlyIssues(e.target.checked)} />Data-quality issues only</label>
          <button className="btn sm" onClick={clear}><X size={14} aria-hidden />Clear</button>
          <span className="muted small" aria-live="polite">{rows.length} shown</span>
        </div>
        {rows.length === 0 ? <Empty title="No contracts match these filters" /> : (
          <div className="table-wrap"><table className="data">
            <thead><tr><th>ID</th><th>Counterparty</th><th>Type</th><th>AtliQ entity</th><th>Country</th><th>Status</th><th>Value (USD)</th>
              <th>Received</th><th>Signed</th><th>Expiry</th><th>Restrictive clauses (tracker)</th><th>Document</th><th>Risk</th><th>Flags</th></tr></thead>
            <tbody>{rows.map(r => (<Fragment key={r.contract_id}>
              <tr key={r.contract_id} className="click" onClick={() => setOpen(open === r.contract_id ? null : r.contract_id)} aria-expanded={open === r.contract_id}>
                <td className="mono nowrap">{r.uploaded ? 'upload' : r.contract_id}</td>
                <td><b>{r.counterparty || <span className="blank">blank</span>}</b><div className="muted small">{r.requested_by && `requested by ${r.requested_by}`}</div></td>
                <td>{r.doc_type || <span className="blank">blank</span>}</td>
                <td><Blank v={r.atliq_entity} label="blank" /></td><td><Blank v={r.client_country} label="blank" /></td>
                <td><Blank v={r.status} label="blank" /></td>
                <td className="nowrap">{fmtMoney(r.value_usd_num) ?? <span className="blank">blank</span>}</td>
                <td className="nowrap"><Blank v={r.received_date} label="—" /></td><td className="nowrap"><Blank v={r.signed_date} label="—" /></td>
                <td className="nowrap"><Blank v={r.expiry_date} label="—" /></td>
                <td><Blank v={r.restrictive_clauses} label="blank" /></td>
                <td>{r.documents.length ? r.documents.map(d => <div key={d.doc_id}><a href={`#/doc/${d.doc_id}`} onClick={e => e.stopPropagation()}>{d.kind === 'executed' ? 'Executed copy' : d.kind === 'draft' ? 'Draft' : 'Upload'}</a></div>)
                  : <span className="blank">not in repository</span>}</td>
                <td>{r.documents.length ? <SeverityBadge s={r.risk_level} /> : <span className="muted">—</span>}</td>
                <td>{r.data_quality.length ? <span className="badge sev-Medium">{r.data_quality.length} issue{r.data_quality.length > 1 ? 's' : ''}</span> : ''}</td>
              </tr>
              {open === r.contract_id && (
                <tr key={r.contract_id + '-x'}><td colSpan={14} style={{ background: 'var(--surface-2)' }}>
                  <dl className="kv">
                    <dt>Notes</dt><dd><Blank v={r.notes} label="no notes" /></dd>
                    <dt>File location</dt><dd><Blank v={r.file_location} label="not recorded" /></dd>
                    <dt>Documents</dt><dd>{r.documents.length ? r.documents.map(d => <div key={d.doc_id}><a href={`#/doc/${d.doc_id}`}>{d.filename}</a> <span className="muted small">({d.evidence_label})</span></div>) : 'No document for this row was found in the repository.'}</dd>
                    <dt>Data quality</dt><dd>{r.data_quality.length ? <ul style={{ margin: 0, paddingLeft: 18 }}>{r.data_quality.map((i, n) => <li key={n}><SeverityBadge s={i.severity} /> {i.message}</li>)}</ul> : 'No issues detected.'}</dd>
                  </dl>
                </td></tr>)}
            </Fragment>))}</tbody>
          </table></div>)}
      </div>
    </div>
  )
}
