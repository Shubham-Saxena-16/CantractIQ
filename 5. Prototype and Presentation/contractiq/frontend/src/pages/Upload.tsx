import { useRef, useState, type ChangeEvent } from 'react'
import { FileUp, CheckCircle2, AlertOctagon } from 'lucide-react'
import { api } from '../api'
import { useLoad } from '../components'

export default function Upload() {
  const tracker = useLoad(() => api.contracts())
  const [file, setFile] = useState<File | null>(null)
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [res, setRes] = useState<any>(null)
  const input = useRef<HTMLInputElement>(null)
  const [ctx, setCtx] = useState({ counterparty: '', doc_type: '', atliq_entity: '', country: '', deadline: '', tracker_id: '', atliq_role: '', notes: '', requested_by: '', value_usd: '' })
  const set = (k: keyof typeof ctx) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setCtx(c => ({ ...c, [k]: e.target.value }))

  const pick = (f: File | undefined | null) => {
    setErr(null); setRes(null)
    if (!f) return
    if (!/\.(pdf|docx|md|markdown|txt)$/i.test(f.name)) { setErr('Unsupported file type. Upload PDF, DOCX, Markdown or text.'); return }
    if (f.size > 25 * 1024 * 1024) { setErr('File is larger than 25 MB.'); return }
    setFile(f)
  }
  const submit = async () => {
    if (!file) { setErr('Choose a file first.'); return }
    const fd = new FormData()
    fd.append('file', file)
    Object.entries(ctx).forEach(([k, v]) => v && fd.append(k, v))
    setBusy(true); setErr(null)
    try { setRes(await api.upload(fd)) } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="stack">
      <div className="page-head"><div><h1>Upload a contract</h1>
        <div className="sub">PDF (text or scanned), DOCX, Markdown or text. The file is processed locally; nothing is sent to an external service. Fields you leave blank are stored as “not provided”, never inferred.</div></div></div>
      <div className="grid two">
        <div className="card card-pad stack">
          <div className={`dropzone ${drag ? 'drag' : ''}`} onDragOver={e => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
            onDrop={e => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]) }}>
            <FileUp size={28} aria-hidden />
            <p><b>Drop a contract here</b> or</p>
            <button className="btn" onClick={() => input.current?.click()}>Choose file</button>
            <input ref={input} type="file" accept=".pdf,.docx,.md,.markdown,.txt" hidden onChange={e => pick(e.target.files?.[0])} />
            {file && <p className="small" style={{ marginTop: 8 }}>Selected: <b>{file.name}</b> ({Math.round(file.size / 1024)} KB)</p>}
          </div>
          <p className="muted small">Scanned PDFs: pages without a text layer are OCR'd only if Tesseract is installed; otherwise they are reported as unreadable and excluded from analysis (never treated as “clause not found”).</p>
        </div>
        <div className="card card-pad stack">
          <h2>Deal context</h2>
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
            <label className="field">Counterparty<input type="text" value={ctx.counterparty} onChange={set('counterparty')} /></label>
            <label className="field">Contract type<input type="text" value={ctx.doc_type} onChange={set('doc_type')} placeholder="MSA, SOW, NDA…" /></label>
            <label className="field">Intended AtliQ entity<select value={ctx.atliq_entity} onChange={set('atliq_entity')}><option value="">Not provided</option><option>AtliQ Inc</option><option>AtliQ Technologies Pvt Ltd</option></select></label>
            <label className="field">Client geography<input type="text" value={ctx.country} onChange={set('country')} placeholder="e.g. USA, UAE" /></label>
            <label className="field">AtliQ's role<select value={ctx.atliq_role} onChange={set('atliq_role')}><option value="">Detect from document</option><option value="supplier">Supplier (client contract)</option><option value="buyer">Buyer (vendor / freelancer)</option><option value="partner">Partner</option><option value="nda">NDA party</option></select></label>
            <label className="field">Review deadline<input type="date" value={ctx.deadline} onChange={set('deadline')} /></label>
            <label className="field">Requested by<input type="text" value={ctx.requested_by} onChange={set('requested_by')} /></label>
            <label className="field">Value (USD)<input type="text" value={ctx.value_usd} onChange={set('value_usd')} /></label>
            <label className="field">Link to tracker row<select value={ctx.tracker_id} onChange={set('tracker_id')}><option value="">None</option>{(tracker.data ?? []).filter(r => !r.uploaded).map(r => <option key={r.contract_id} value={r.contract_id}>{r.contract_id} — {r.counterparty} {r.doc_type}</option>)}</select></label>
          </div>
          <label className="field">Notes<input type="text" value={ctx.notes} onChange={set('notes')} /></label>
          <div className="row"><button className="btn primary" onClick={submit} disabled={busy || !file}>{busy ? 'Extracting & analysing…' : 'Upload and analyse'}</button></div>
        </div>
      </div>
      {err && <div className="banner err" role="alert"><AlertOctagon size={18} aria-hidden /><div><b>Upload failed.</b> {err}</div></div>}
      {res && (
        <div className="card card-pad stack" role="status">
          <div className="row"><CheckCircle2 size={20} color="var(--ok)" aria-hidden /><h2>Processed</h2></div>
          <div className="small">Format: {res.info.format}{res.info.pages ? ` · ${res.info.pages} pages` : ''} · {res.clause_count} clauses identified · {res.findings} findings</div>
          {res.warnings.length > 0 && <div className="banner warn small"><div><b>Extraction warnings</b><ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>{res.warnings.map((w: any, i: number) => <li key={i}>[{w.level}] {w.message}</li>)}</ul></div></div>}
          <div className="row"><a className="btn primary" href={`#/doc/${res.doc_id}`}>Open review workspace</a><a className="btn" href={`/api/documents/${encodeURIComponent(res.doc_id)}/export/extracted.md`} download>Download extracted Markdown</a></div>
        </div>)}
    </div>
  )
}
