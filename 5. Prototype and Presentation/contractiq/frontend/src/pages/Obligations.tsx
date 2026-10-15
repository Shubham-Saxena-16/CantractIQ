import { useMemo, useState } from 'react'
import { api, type Obligation } from '../api'
import { Empty, ErrorState, Fact, Loading, useLoad } from '../components'
import { useApp } from '../App'

const KIND_LABEL: Record<string, string> = {
  review_deadline: 'Review deadline', expiry: 'Expiry', renewal_notice: 'Renewal notice', termination_notice: 'Termination notice',
  incident_notification: 'Incident notification', insurance: 'Insurance', invoice_window: 'Invoice window',
  confidentiality_survival: 'Confidentiality survival', restriction: 'Restriction (commitment)',
}

function Row({ o, asOf }: { o: Obligation; asOf: string }) {
  const { reviewer } = useApp()
  const [owner, setOwner] = useState(o.owner === 'Unassigned' ? '' : o.owner)
  const [status, setStatus] = useState(o.status)
  const [msg, setMsg] = useState<string | null>(null)
  const [show, setShow] = useState(false)
  const save = async () => {
    try { await api.updateObligation(o.id, { owner: owner || undefined, status, reviewer }); setMsg('Saved') } catch (e: any) { setMsg(e.message) }
  }
  const passed = !!o.due_date && o.due_date < asOf
  const isEnd = ['expiry', 'restriction', 'confidentiality_survival'].includes(o.kind)
  const overdue = passed && !isEnd && !['Done', 'Not applicable', 'Expired'].includes(status)
  return (<>
    <tr>
      <td className="nowrap">{o.due_date ? <>{o.due_date}{overdue && <div className="small" style={{ color: 'var(--crit)' }}>past due</div>}
        {passed && isEnd && <div className="small muted">ended</div>}</> : <span className="badge sev-Medium">unverified</span>}</td>
      <td><b>{o.title}</b><div className="muted small">{KIND_LABEL[o.kind] ?? o.kind} · {o.counterparty ?? ''} {o.tracker_id && <span className="mono">({o.tracker_id})</span>}</div>
        {o.excerpt && <button className="btn sm ghost" onClick={() => setShow(s => !s)}>{show ? 'Hide' : 'Show'} source</button>}</td>
      <td className="small">{o.due_basis}<div className="muted">{o.source}</div></td>
      <td><input type="text" aria-label="Owner" placeholder="Unassigned" value={owner} onChange={e => setOwner(e.target.value)} style={{ width: 120 }} /></td>
      <td><select aria-label="Status" value={status} onChange={e => setStatus(e.target.value)}>{['Open', 'In progress', 'Done', 'Not applicable', 'Expired', 'Needs verification'].map(s => <option key={s}>{s}</option>)}</select></td>
      <td><button className="btn sm" onClick={save} disabled={!reviewer}>Save</button>{msg && <div className="small">{msg}</div>}</td>
    </tr>
    {show && o.excerpt && <tr><td colSpan={6}><Fact refText={o.ref} excerpt={o.excerpt} /></td></tr>}
  </>)
}

export default function Obligations() {
  const { meta } = useApp()
  const { data, error, loading, reload } = useLoad(() => api.obligations())
  const [kind, setKind] = useState('')
  const [onlyDated, setOnlyDated] = useState(false)
  const [unassigned, setUnassigned] = useState(false)
  const rows = useMemo(() => (data ?? []).filter(o => (!kind || o.kind === kind) && (!onlyDated || o.due_date) && (!unassigned || o.owner === 'Unassigned')), [data, kind, onlyDated, unassigned])
  if (loading) return <Loading />
  if (error) return <ErrorState error={error} onRetry={reload} />
  return (
    <div className="stack">
      <div className="page-head"><div><h1>Obligations & deadlines</h1>
        <div className="sub">Extracted from contract clauses and tracker rows. Dates are computed only when inputs exist; owners start as Unassigned and are never guessed. Updates are logged.</div></div></div>
      <div className="card">
        <div className="toolbar">
          <select aria-label="Type" value={kind} onChange={e => setKind(e.target.value)}><option value="">All types</option>{Object.entries(KIND_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          <label className="row small"><input type="checkbox" checked={onlyDated} onChange={e => setOnlyDated(e.target.checked)} />With dates only</label>
          <label className="row small"><input type="checkbox" checked={unassigned} onChange={e => setUnassigned(e.target.checked)} />Unassigned only</label>
          <span className="muted small">{rows.length} shown</span>
        </div>
        {rows.length === 0 ? <Empty title="No obligations match" /> : <div className="table-wrap"><table className="data">
          <thead><tr><th>Due</th><th>Obligation</th><th>Date basis / source</th><th>Owner</th><th>Status</th><th></th></tr></thead>
          <tbody>{rows.map(o => <Row key={o.id} o={o} asOf={meta?.as_of ?? ''} />)}</tbody></table></div>}
      </div>
    </div>
  )
}
