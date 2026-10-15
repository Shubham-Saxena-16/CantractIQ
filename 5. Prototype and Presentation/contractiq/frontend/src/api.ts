// Thin typed client for the FastAPI backend. All calls go to the local server only.

export type Severity = 'Critical' | 'High' | 'Medium' | 'Low' | 'Info'

export interface Fact { ref: string; excerpt: string; clause_idx?: number; page?: number | null; heading?: string }
export interface Precedent { title: string; excerpt: string; is_exception: boolean; outcome: string; evidence_label: string }
export interface Review {
  disposition?: string; note?: string; follow_up?: number; reviewer?: string; created_at?: string; history_count?: number
}
export interface Conflict {
  id: string; type: string; severity: Severity; confidence: string; title: string; rationale: string
  prior_doc_id: string; prior_filename: string; prior_ref: string; prior_excerpt: string; prior_counterparty: string
  prior_status: string; prior_end: string | null; prior_end_basis: string; prior_evidence_label: string
  prior_definitions: { ref: string; excerpt: string }[]
  new_doc_id: string; new_evidence_label: string; new_evidence: Fact[]
  matched_sectors?: string[]; matched_geographies?: string[]; missing_facts: string[]
  waiver_assessment?: { filename: string; scope_excerpt: string; covers_this_deal: boolean }[]
  context?: { source: string; text: string }[]; prior_rate_rows?: string[]
  new_title?: string; new_filename?: string; new_kind?: string; new_counterparty?: string
}
export interface Finding {
  id: string; doc_id: string; rule: string; category: string; category_label: string; severity: Severity; title: string
  fact: Fact | null; related_facts: Fact[]; extracted: Record<string, unknown>; interpretation: string; recommendation: string
  checklist: { items: string[]; source: string; evidence_label: string } | null; precedents: Precedent[]
  confidence: string; perspective: string; source: string; evidence_label: string; review?: Review | null; conflict?: Conflict
}
export interface QualityWarning { level: string; code: string; message: string }
export interface TrackerRow {
  contract_id: string; counterparty: string; doc_type: string; atliq_entity: string; client_country: string; requested_by: string
  received_date: string; status: string; signed_date: string; expiry_date: string; value_usd: string; value_usd_num: number | null
  file_location: string; restrictive_clauses: string; notes: string
}
export interface DQIssue { contract_id: string | null; doc_id?: string; code: string; severity: Severity; message: string }
export interface ContractRow extends TrackerRow {
  documents: { doc_id: string; filename: string; kind: string; evidence_label: string }[]
  risk_level: Severity | null; data_quality: DQIssue[]; uploaded?: boolean
}
export interface DocOverview {
  doc_id: string; filename: string; kind: string; evidence_label: string; title: string; provenance: string; doc_date: string | null
  atliq_term: string | null; counterparty_term: string | null; counterparty_name: string | null; atliq_entity: string | null
  atliq_role: string; tracker_ids: string[]; tracker_match_basis: string; quality: QualityWarning[]; clause_count: number
  severity_counts: Record<Severity, number>; conflict_count: number; open_material: number; tracker: TrackerRow[]
  risk_level?: Severity | null; upload_context?: Record<string, unknown>
}
export interface Clause { idx: number; number: string | null; heading: string; text: string; page: number | null; line: number; kind: string; ref: string }
export interface DocDetail extends DocOverview {
  text: string; clauses: Clause[]; corrections: { field: string; value: string; reviewer: string; created_at: string }[]
  checklist_version: string
}
export interface EntityCheck { check: string; status: string; value: string | null; expected: string | null; severity: Severity; note: string; fact: Fact | null; source?: string | null }
export interface Companion { document: string; why: string; status: string; label: string; evidence: string | null; evidence_label: string | null; basis: Fact | null }
export interface Obligation {
  id: string; doc_id: string | null; tracker_id: string | null; kind: string; title: string; description: string; due_date: string | null
  date_status: string; due_basis: string; source: string; excerpt: string | null; ref: string | null; owner: string; status: string
  requested_by: string | null; note?: string; reviewer?: string; doc_title?: string | null; counterparty?: string | null; doc_kind?: string
  clause_idx?: number | null
}
export interface AiStatus { available: boolean; provider: string | null; model: string | null; endpoint: string | null; mode: string; disclosure: string }
export interface Analysis {
  doc_id: string; findings: Finding[]; conflicts: Conflict[]; considered: { commitment: string; result: string; detail?: string }[]
  entity: EntityCheck[]; companions: Companion[]; obligations: Obligation[]
  coverage: { executed_searched: string[]; not_in_repository: string[]; statement: string }; quality: QualityWarning[]; mode: AiStatus
}
export interface Meta {
  app: string; as_of: string; checklist_version: string; ai: AiStatus; dispositions: string[]; guardrail: string
  counts: { documents: number; tracker_rows: number }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, init)
  } catch {
    throw new Error('Cannot reach the ContractIQ server. Is it running on http://127.0.0.1:8000?')
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const j = await res.json()
      if (j.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch { /* not JSON */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

const post = <T,>(path: string, body: unknown) =>
  req<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  meta: () => req<Meta>('/api/meta'),
  dashboard: () => req<any>('/api/dashboard'),
  contracts: () => req<ContractRow[]>('/api/contracts'),
  documents: () => req<DocOverview[]>('/api/documents'),
  document: (id: string) => req<DocDetail>(`/api/documents/${encodeURIComponent(id)}`),
  analysis: (id: string) => req<Analysis>(`/api/documents/${encodeURIComponent(id)}/analysis`),
  review: (fid: string, body: { disposition?: string; note?: string; follow_up?: boolean; reviewer: string }) =>
    post<{ review: Review }>(`/api/findings/${fid}/review`, body),
  history: (fid: string) => req<any[]>(`/api/findings/${fid}/history`),
  queue: () => req<any[]>('/api/review-queue'),
  commitments: () => req<any>('/api/commitments'),
  obligations: () => req<Obligation[]>('/api/obligations'),
  updateObligation: (id: string, body: { owner?: string; status?: string; note?: string; reviewer: string }) =>
    post<any>(`/api/obligations/${id}`, body),
  ask: (body: { question: string; doc_id?: string | null; use_ai: boolean; consent: boolean }) => post<any>('/api/ask', body),
  aiReview: (id: string) => post<any>(`/api/documents/${encodeURIComponent(id)}/ai-review`, { consent: true }),
  correct: (id: string, body: { field: string; value: string; reviewer: string }) => post<any>(`/api/documents/${encodeURIComponent(id)}/corrections`, body),
  dataQuality: () => req<{ issues: DQIssue[]; counts: Record<string, number> }>('/api/data-quality'),
  upload: async (form: FormData) => req<any>('/api/upload', { method: 'POST', body: form }),
}

export const exportUrl = (id: string, kind: 'summary' | 'escalation' | 'extracted') =>
  `/api/documents/${encodeURIComponent(id)}/export/${kind}.md`
