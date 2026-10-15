// Slide content for the AtliQ ContractIQ project presentation.
// Sources: PRD capstone.docx (PRD), 1.Problem Discovery & User Research.xlsx (Discovery), Dataset/ files, and the
// implemented MVP in this repository. Planned capabilities are labelled "Planned"; targets are labelled "Target".
import { useState, type CSSProperties, type ReactNode } from 'react'

export interface SlideDef { id: string; title: string; notes: string[]; render: () => ReactNode }

const rv = (i: number): { className: string; style: CSSProperties } => ({ className: 'rv', style: { '--i': i } as CSSProperties })

function Expander({ title, children, defaultOpen = false }: { title: ReactNode; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="xp">
      <button className="xp-btn" aria-expanded={open} onClick={() => setOpen(o => !o)}>{title}<span className="sign" aria-hidden>+</span></button>
      <div className={`xp-body ${open ? 'open' : ''}`} aria-hidden={!open}><div><div className="xp-inner">{children}</div></div></div>
    </div>
  )
}

const Src = ({ children }: { children: ReactNode }) => <div className="src"><b>Source:</b> {children}</div>

/* ------------------------------------------------------------------ 1. Title */
function TitleSlide() {
  return (
    <div className="title-slide" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', flex: 1 }}>
      <div {...rv(0)}><div className="kicker">Capstone project · Product review</div></div>
      <h1 {...rv(1)} className="big rv">AtliQ <em>ContractIQ</em></h1>
      <p {...rv(2)} className="sub rv">AI-Powered Contract Intelligence &amp; Risk Analysis</p>
      <p {...rv(3)} className="tagline rv">Find the risky clause, the conflicting promise and the missing document before signature, with the exact source text on screen and a human making every decision.</p>
      <div {...rv(4)} className="meta-grid rv">
        <div><b>Product manager</b>Shubham Saxena</div>
        <div><b>Primary user</b>Karandeep, CEO &amp; contract signatory</div>
        <div><b>PRD</b>V1.0 draft · 10 Oct 2026</div>
        <div><b>Status</b>Working MVP on the AtliQ dataset</div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ 2. Problem */
function ProblemSlide() {
  return (
    <>
      <div {...rv(0)}><div className="kicker">Problem discovery</div><h1 className="st">Contract knowledge lives in one person's memory</h1></div>
      <p {...rv(1)} className="lede rv">AtliQ lacks a centralized, standardized contract-review process. Obligations, risk clauses, past negotiation decisions and document requirements are spread across files, with interpretation depending on the CEO's memory and limited time.</p>
      <div {...rv(2)} className="cols c3 rv">
        <div className="pcard primary"><div className="stat">~5 → ~9</div><div className="stat-label">contracts per month, last year vs this year, all reviewed and signed by one person</div></div>
        <div className="pcard primary"><div className="stat">3–4 hrs</div><div className="stat-label">for Karandeep to review one client-paper MSA properly, usually after 10 pm</div></div>
        <div className="pcard primary"><div className="stat">0</div><div className="stat-label">registers of what AtliQ has already promised (non-competes, exclusivity, pricing, IP)</div></div>
      </div>
      <div {...rv(3)} className="cols c2 rv" style={{ marginTop: 16 }}>
        <div className="pcard warn"><h3>Missed risk costs money</h3>
          <p className="muted">Brightwater Insurance (signed Nov 2025): an uncapped delay clause under English law led to an $18,400 damages claim, a <b>$9,000</b> settlement credit and <b>$14,200</b> in counsel fees, after a 19-day delay caused by the client's own security review.</p></div>
        <div className="pcard warn"><h3>Slow review costs revenue</h3>
          <p className="muted">ShopSwift: an SOW sat 9 days waiting for review and the client's budget slipped a quarter. "We lost that one to our own queue."</p></div>
      </div>
      <div {...rv(4)} className="rv" style={{ marginTop: 14 }}>
        <Expander title="Root cause: the 5 Whys from discovery">
          <ol className="clean" style={{ paddingLeft: '1.2em' }}>
            <li>Contract review is reactive: information is searched only when a deal or issue arises.</li>
            <li>Contracts, amendments, SOWs, NDAs and emails sit across folders, inboxes and spreadsheets with inconsistent metadata.</li>
            <li>Key risks, obligations and exceptions are not extracted into a searchable, structured form after signing.</li>
            <li>There is no consistent way to compare new terms with prior agreements, approved exceptions and restrictions.</li>
            <li>No contract-governance model defines how agreements are submitted, reviewed, stored, linked, monitored and escalated.</li>
          </ol>
        </Expander>
      </div>
      <Src>Discovery workbook (problem statement, 5 Whys); meeting notes 2026-09-22 and 2026-04-14; Karandeep's checklist note; dataset README.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 3. Persona */
function PersonaSlide() {
  const goals = [
    'Close new deals safely and efficiently without unnecessary delays.',
    "Identify important contractual risks and protect AtliQ's financial interests and IP.",
    'Quickly retrieve existing commitments and past negotiation decisions before accepting new terms.',
    "Ensure new agreements do not conflict with existing customer commitments or AtliQ's ability to deliver.",
    'Track important deadlines, compliance requirements and post-signature obligations.',
    'Make confident, evidence-backed decisions and know when external legal advice is necessary.',
  ]
  return (
    <>
      <div {...rv(0)}><div className="kicker">Target persona</div><h1 className="st">Karandeep, CEO and contract signatory</h1></div>
      <div className="cols c-2-1">
        <div>
          <p {...rv(1)} className="lede rv" style={{ marginBottom: 14 }}>Reviews and signs every contract for both AtliQ entities (AtliQ Technologies Pvt Ltd, India, and AtliQ Inc, USA). AtliQ has no legal team and no head of contracts.</p>
          <div {...rv(2)} className="pcard accent rv"><h3>Goals</h3>
            <ul className="clean">{goals.map(g => <li key={g}>{g}</li>)}</ul></div>
        </div>
        <div className="stack" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div {...rv(3)} className="pcard rv"><h3>Responsibilities</h3>
            <ul className="clean">
              <li>Reads MSAs, SOWs, NDAs, BAAs, partner, vendor and freelancer agreements</li>
              <li>Decides: sign, negotiate, escalate to counsel or reject</li>
              <li>Balances legal exposure with sales deadlines</li>
            </ul></div>
          <div {...rv(4)} className="rv">
            <blockquote className="q">"Have we already agreed to something that conflicts with this deal?"<cite>Empathy map: thinks</cite></blockquote>
          </div>
          <div {...rv(5)} className="rv">
            <Expander title="Who else is involved">
              <ul className="clean">
                <li><b>Sales</b>: Bhavin, Dhaval, Jay. They bring contracts in and need status and blockers.</li>
                <li><b>CTO</b>: Pranav confirms scope, staffing and reuse.</li>
                <li><b>Finance / Operations</b>: entity, invoicing, currency, tracker.</li>
                <li><b>External counsel</b>: Mehta Rao (India), Calloway Stern (US), for selected matters.</li>
              </ul>
            </Expander>
          </div>
        </div>
      </div>
      <Src>Discovery workbook (persona, goals, empathy map); PRD §4.1; atliq_entities.md; dataset README.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 4. Pain points */
const PAINS = [
  { t: 'Risks buried in long contracts', d: 'Important risks and obligations are buried in lengthy, complex contracts and are hard to identify quickly.',
    e: 'Brightwater post-mortem: "I signed it at the airport. English law, uncapped LD — I didn\'t even see it." The delay clause had no exclusion for client-caused delay.', s: 'meeting_notes/2026-04-14_brightwater_postmortem.md' },
  { t: 'Information is scattered', d: 'Contract information sits across folders, emails and tools, so previous commitments and negotiated terms are hard to retrieve.',
    e: 'In the 22 Sep meeting nobody could find the Al Noor contract. Karandeep found it in his email only after 20 minutes on a later call with counsel.', s: 'meeting_notes 2026-09-22 and 2026-09-25' },
  { t: 'Related documents are not linked', d: 'MSAs, SOWs, NDAs, amendments and renewals are not always linked, raising the risk of conflicting obligations or missed changes.',
    e: 'Harrington is three documents (NDA signed, MSA and BAA in review). The tracker has a likely duplicate row (C-010/C-011), and 13 rows marked "Signed" have no executed copy in the repository.', s: 'meeting_notes/2026-09-27_harrington_huddle.md; contract_tracker.csv' },
  { t: 'Limited time, manual review', d: 'Manual review makes it hard to assess risk consistently while running the company.',
    e: '"I review everything myself, usually after 10 pm … When I\'m rushed I sign things I would never have agreed to on a normal day."', s: 'karandeep_contract_checklist.md (Sept 2026 note)' },
  { t: 'Unclear ownership of deadlines', d: 'Deadlines, renewals and post-signature obligations are tracked manually with no clear owner.',
    e: 'After the queue meeting: "No owner, order of review, or deadline per contract was agreed." The dataset README notes there is no register of obligations AtliQ has taken on.', s: 'meeting_notes/2026-09-22_internal_contract_queue.md; Dataset README' },
  { t: 'Dependence on external counsel', d: 'Uncertain interpretations lead to costly and slower reliance on outside counsel.',
    e: 'Mehta Rao quoted ₹1,20,000 and 5–7 working days for Gulf Crown + Al Noor. A US BAA review cost $3,800. Karandeep: "it\'s $210k, but Mehta Rao takes a week."', s: 'meeting_notes 2026-09-25 and 2026-09-22; negotiation_notes.md' },
]
function PainSlide() {
  const [sel, setSel] = useState(0)
  const p = PAINS[sel]
  return (
    <>
      <div {...rv(0)}><div className="kicker">Pain points</div><h1 className="st">Six problems Karandeep faces</h1>
        <p className="lede">Select a pain point to see the evidence for it in AtliQ's own files.</p></div>
      <div {...rv(1)} className="picker rv">
        <div className="pick-list" role="tablist" aria-label="Pain points">
          {PAINS.map((x, i) => (
            <button key={x.t} role="tab" aria-selected={sel === i} className="pick" onClick={() => setSel(i)}>
              <span className="pn">{String(i + 1).padStart(2, '0')}</span><span className="pt">{x.t}</span>
            </button>))}
        </div>
        <div key={sel} className="panel swap" role="tabpanel">
          <h3>{p.t}</h3>
          <p>{p.d}</p>
          <div className="lab">Evidence from the dataset</div>
          <blockquote className="q">{p.e}<cite>{p.s}</cite></blockquote>
        </div>
      </div>
      <Src>Pain points from the Discovery workbook; evidence quoted from the dataset files named in each panel.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 5. Current workflow */
const WORKFLOW = [
  ['Receive the agreement', 'By email or file share, often with a deadline. Identify the type, counterparty, entity, value and start date from the filename or email.', 'Locate the right version; gather context from several people.'],
  ['Read the full contract', 'Payment, liability, indemnity, liquidated damages, termination, IP, confidentiality, exclusivity, governing law, insurance, data.', 'Clauses hide in boilerplate, schedules and cross-references.'],
  ['Compare against the checklist and memory', 'A short checklist last edited March 2024, plus recollection of past negotiations.', 'Exceptions and rejected positions live in old emails or memory.'],
  ['Search for conflicts with past agreements', 'Old signed contracts, inboxes, Jay\'s negotiation notes, tracker rows.', 'Hard to tell if a past position was policy, a one-off exception or a draft.'],
  ['Check entity, geography, currency and law', 'AtliQ Inc for US clients, Pvt Ltd for everyone else.', 'Entity/invoice mismatches caused payment delays twice in 2025.'],
  ['Check companion documents', 'NDA, HIPAA BAA, GDPR DPA, matching freelancer/vendor terms.', 'The tracker may say a document exists without proving it was signed.'],
  ['Reconcile the tracker', 'Status, dates, file locations, duplicates.', 'Blanks, duplicates and stale statuses create false confidence.'],
  ['Decide', 'Sign, request changes, escalate to counsel, or reject. Communicate and track follow-ups.', 'Decision rationale is kept informally, if at all.'],
]
function WorkflowSlide() {
  return (
    <>
      <div {...rv(0)}><div className="kicker">Current workflow</div><h1 className="st">Today's review: eight manual steps</h1>
        <p className="lede">Each step relies on manual searches, historical documents, colleagues' memory and, for some deals, external counsel. Open a step to see where it breaks down.</p></div>
      <div className="cols c2">
        <div>{WORKFLOW.slice(0, 4).map(([t, d, pain], i) => (
          <div key={t} {...rv(1 + i)} className="rv" style={{ marginBottom: 8, ...rv(1 + i).style }}>
            <Expander title={<><span className="pn" style={{ font: '700 .85em var(--mono)', color: 'var(--accent)' }}>{i + 1}</span> {t}</>}>
              <p>{d}</p><p><b>Manual effort:</b> {pain}</p></Expander></div>))}</div>
        <div>{WORKFLOW.slice(4).map(([t, d, pain], i) => (
          <div key={t} {...rv(5 + i)} className="rv" style={{ marginBottom: 8, ...rv(5 + i).style }}>
            <Expander title={<><span className="pn" style={{ font: '700 .85em var(--mono)', color: 'var(--accent)' }}>{i + 5}</span> {t}</>}>
              <p>{d}</p><p><b>Manual effort:</b> {pain}</p></Expander></div>))}</div>
      </div>
      <div {...rv(9)} className="cols c3 rv" style={{ marginTop: 12 }}>
        <div className="pcard"><h3>Manual searches</h3><p className="muted">Contracts were scattered across drives, inboxes and laptops before being collected.</p></div>
        <div className="pcard"><h3>Colleagues</h3><p className="muted">"A lot of the 'why' is only in K's head." (Jay)</p></div>
        <div className="pcard"><h3>External counsel</h3><p className="muted">"I can't advise on one in isolation." Counsel asked for every signed contract with restrictions.</p></div>
      </div>
      <Src>PRD §2.1 Current State (steps 1–8); negotiation_notes.md; meeting notes 2026-09-25; atliq_entities.md.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 6. Proposed solution */
function SolutionSlide() {
  return (
    <>
      <div {...rv(0)}><div className="kicker">Proposed solution</div><h1 className="st">An evidence-first contract review workspace</h1></div>
      <p {...rv(1)} className="lede rv">ContractIQ analyses an incoming agreement, flags material risks and deviations from AtliQ's preferences, surfaces possible conflicts with prior signed commitments, and checks entity and companion documents, always showing the source text it relied on.</p>
      <div className="cols c2">
        <div {...rv(2)} className="pcard accent rv"><h3>Design principles (PRD §5, §7.3)</h3>
          <ul className="clean">
            <li><b>Evidence first:</b> every finding quotes the exact clause and its section.</li>
            <li><b>Executed contracts outrank</b> drafts, negotiation notes and tracker rows, and each is labelled.</li>
            <li><b>Rules for policy, AI for language:</b> checklist checks are deterministic; AI is optional and grounded.</li>
            <li><b>Deal-specific exceptions stay scoped</b> and are never treated as policy.</li>
            <li><b>"No conflict found" is not "no conflict exists":</b> search coverage is always disclosed.</li>
          </ul></div>
        <div {...rv(3)} className="pcard warn rv"><h3>What it deliberately does not do</h3>
          <ul className="clean">
            <li>Sign, approve, reject, redline, negotiate or send contracts</li>
            <li>Give legal advice or enforceability conclusions</li>
            <li>Treat a tracker row or a note as proof of a binding obligation</li>
            <li>Send documents to an AI service without explicit, per-request consent</li>
          </ul>
          <p className="muted" style={{ marginTop: 10 }}>Karandeep stays the decision-maker; the tool shortens the search and makes the evidence visible.</p></div>
      </div>
      <div {...rv(4)} className="rv" style={{ marginTop: 14 }}>
        <Expander title="Why AI is justified, and what its limits are">
          <p>Contract review means reading long agreements, interpreting legal language and searching scattered history: repetitive work that is hard to do consistently under deadline pressure (PRD §2.4).</p>
          <p><b>Limits:</b> models can misread or invent text. ContractIQ therefore keeps AI output separate and labelled, drops any AI citation that cannot be matched word-for-word in the source, answers "insufficient evidence" when retrieval is weak, and runs in a clearly labelled demo mode (rules + local search) when no AI key is configured.</p>
        </Expander>
      </div>
      <Src>PRD §1 Executive Summary, §2.4 JTBD, §5 Model Strategy, §7.2–7.3; MVP implementation.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 7. Core features */
type Status = 'Implemented' | 'Partly implemented' | 'Planned'
const FEATURES: { t: string; s: string; status: Status; detail: string[]; plan?: string }[] = [
  { t: 'Contract dashboard', s: 'Register, KPIs, deadlines, data quality', status: 'Implemented',
    detail: ['All 48 tracker rows, searchable and filterable; blanks shown as blank, never filled in.', 'KPIs: total, under review, high-risk drafts, expirations within 90 days, possible conflicts.', 'Tracker issues surfaced, e.g. duplicate C-010/C-011, 13 "Signed" rows with no executed copy.'] },
  { t: 'Document conversion', s: 'PDF and DOCX to Markdown', status: 'Partly implemented',
    detail: ['PDF (per page, with page references) and DOCX (headings and tables preserved) converted to Markdown; export as .md.', 'Clause numbers, headings and pages kept for citations; extraction warnings shown.', 'Clear errors for corrupt, password-protected, legacy .doc and image-only files.'],
    plan: 'OCR for scanned PDFs: code path exists but Tesseract is not installed, so scanned pages are reported as unreadable.' },
  { t: 'Risk analysis', s: 'Checklist-based clause risks', status: 'Implemented',
    detail: ['Deterministic rules for liquidated damages, liability, indemnity, payment, termination, IP, confidentiality, exclusivity, data security, insurance, governing law.', 'Each finding: exact clause, rule-based interpretation, suggested next step, checklist line, related negotiation history.', 'Optional AI risk review (Groq or Anthropic) with per-request consent; AI findings kept only if their quote is found verbatim.'] },
  { t: 'Historical intelligence', s: 'What has AtliQ already promised?', status: 'Implemented',
    detail: ['Commitment register built only from the 17 executed contracts: non-competes, exclusivity, MFN pricing, IP assignments, with end dates and waivers.', 'Flags 6 potential conflicts in incoming drafts, e.g. Gulf Crown vs the Al Noor GCC hospitality non-compete; Lakeshore rates vs the Crestline most-favoured pricing clause.', 'Each conflict lists the facts still needed; matching is keyword-based and needs legal confirmation.'] },
  { t: 'Contract Q&A', s: 'Questions answered from the documents', status: 'Implemented',
    detail: ['Local search across clauses, negotiation notes and tracker rows, each result labelled by evidence type.', 'With an AI key and consent: a generated answer whose citations are verified word-for-word; otherwise ranked passages (demo mode).', 'Says "insufficient evidence" when the sources do not support an answer.'] },
  { t: 'Obligation tracking', s: 'Deadlines, renewals, notice periods', status: 'Partly implemented',
    detail: ['Extracts expiries, auto-renewal notice dates, termination notice periods, incident-notification windows, insurance, restriction end dates and review deadlines.', 'Owners start as "Unassigned" and dates without a source are "unverified"; updates are logged.'],
    plan: 'Reminders and notifications are not implemented.' },
]
function FeaturesSlide() {
  const [open, setOpen] = useState<number | null>(null)
  const cls = (s: Status) => s === 'Implemented' ? 'chip ok' : s === 'Planned' ? 'chip plan' : 'chip part'
  return (
    <>
      <div {...rv(0)}><div className="kicker">Core features</div><h1 className="st">Six capabilities, with honest status labels</h1>
        <p className="lede">Click a card for what it does today and what is still planned.</p></div>
      <div className="fgrid">
        {FEATURES.map((f, i) => (
          <button key={f.t} {...rv(1 + i)} className="fcard rv" aria-expanded={open === i} aria-controls="feature-detail" onClick={() => setOpen(open === i ? null : i)}>
            <span className={cls(f.status)}>{f.status}</span>
            <span className="ft">{f.t}</span><span className="fs">{f.s}</span>
            <span className="more">{open === i ? 'Hide details' : 'Show details'}</span>
          </button>))}
      </div>
      <div id="feature-detail" aria-live="polite" style={{ marginTop: 12 }}>
        {open !== null ? (
          <div key={open} className="panel swap">
            <h3>{FEATURES[open].t} <span className={cls(FEATURES[open].status)} style={{ marginLeft: 8 }}>{FEATURES[open].status}</span></h3>
            <ul className="clean">{FEATURES[open].detail.map(d => <li key={d}>{d}</li>)}</ul>
            {FEATURES[open].plan && <p style={{ marginTop: 10 }}><span className="chip plan">Planned</span> {FEATURES[open].plan}</p>}
          </div>) : <p className="muted" style={{ fontSize: '.85em' }}>Also implemented: human review with an append-only audit trail, Markdown review summaries and counsel escalation packages.</p>}
      </div>
      <Src>MVP in this repository (contractiq/), tested against the AtliQ dataset.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 8. User journey */
const JOURNEY = [
  ['Upload the contract', 'PDF, DOCX or Markdown, plus deal context: counterparty, type, intended entity, geography, deadline. Fields left blank are stored as "not provided", never guessed.'],
  ['Extraction and quality check', 'Text is converted with clause numbers, headings and page references. Unreadable pages, OCR issues and missing schedules are flagged, never reported as "clause not found".'],
  ['Automated checks', 'Checklist rules, entity/currency/governing-law checks, companion-document status (present, draft, unverified, missing) and conflicts with executed commitments.'],
  ['Review findings with evidence', 'Sorted by severity and confidence. Each shows the exact clause (one click jumps to it in the document), separated from the interpretation and the suggested next step.'],
  ['Ask follow-up questions', 'Grounded Q&A over the contract and history, with source references or an explicit "insufficient evidence".'],
  ['Record decisions', 'Relevant, not relevant, resolved, needs information or escalate to counsel, with notes and follow-up flags, saved in an append-only audit trail with reviewer and timestamp.'],
  ['Export', 'Review summary or counsel escalation package (.md) with excerpts, decisions, unresolved items and search coverage.'],
  ['Human decision, outside the tool', 'Karandeep signs, negotiates, escalates or rejects. ContractIQ has no sign, approve or send function.'],
]
function JourneySlide() {
  const [step, setStep] = useState(0)
  return (
    <>
      <div {...rv(0)}><div className="kicker">User journey</div><h1 className="st">From upload to a human-approved decision</h1>
        <p className="lede">Step through the review flow. Use the step buttons or "Next step".</p></div>
      <div {...rv(1)} className="picker rv">
        <div className="pick-list" role="tablist" aria-label="Journey steps">
          {JOURNEY.map(([t], i) => (
            <button key={t} role="tab" aria-selected={step === i} className="pick" onClick={() => setStep(i)}>
              <span className="pn">{i + 1}</span><span className="pt">{t}</span>
            </button>))}
        </div>
        <div key={step} className="panel swap" role="tabpanel">
          <div className="kicker">Step {step + 1} of {JOURNEY.length}</div>
          <h3>{JOURNEY[step][0]}</h3>
          <p>{JOURNEY[step][1]}</p>
          {step === JOURNEY.length - 1 && <p><span className="chip risk">Human in control</span> The tool supports the decision; it never makes it.</p>}
          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button className="deck-tbtn" disabled={step === 0} onClick={() => setStep(s => s - 1)}>Previous step</button>
            <button className="deck-tbtn" disabled={step === JOURNEY.length - 1} onClick={() => setStep(s => s + 1)}>Next step</button>
          </div>
        </div>
      </div>
      <Src>MVP screens: Upload, Review workspace, Ask the contracts, Findings &amp; decisions; PRD §4.2 user stories, FR-1 to FR-16.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 9. Harrington example */
const RISKS = [
  { k: 'Liquidated damages', sev: 'Critical', ref: '§11.2 and §11.3',
    quote: '11.2 … if Contractor fails to achieve any Delivery Date, Contractor shall pay Client, as liquidated damages, an amount equal to two percent (2%) of the Total Contract Value for each calendar day from the Delivery Date until the date the applicable Deliverable is accepted.\n11.3 … Liquidated damages under this Article are in addition to and not in lieu of Client\'s right to recover its actual damages …',
    pref: 'LDs → cap it. never open ended',
    why: 'No cap was found in Article 11, the rate is daily and based on the whole contract value, there is no exclusion for client-caused delay, and LDs are cumulative with actual damages. Illustrative arithmetic only: 2% of the stated $210,000 Total Contract Value is $4,200 per calendar day.',
    check: 'Whether a cap exists elsewhere (e.g. exhibits not in this file); a counter-proposal in line with past deals (negotiation notes: 0.5% of the affected milestone per week, capped at 5%, client delays excluded).' },
  { k: 'Liability', sev: 'Critical', ref: '§10.2 and §10.3',
    quote: '10.2 … CLIENT\'S AGGREGATE LIABILITY ARISING OUT OF OR RELATING TO THIS AGREEMENT SHALL NOT EXCEED THE FEES ACTUALLY PAID BY CLIENT TO CONTRACTOR UNDER THIS AGREEMENT.\n10.3 … NOTHING IN THIS AGREEMENT SHALL LIMIT OR EXCLUDE CONTRACTOR\'S LIABILITY FOR ANY LOSSES, WHETHER DIRECT OR INDIRECT …',
    pref: 'liability → 1x fees. NOT unlimited',
    why: 'The cap protects only the client; AtliQ Inc (the "Contractor") appears to have no cap, including for indemnities, BAA breaches and data-security incidents. A related clause (§9.1) has AtliQ indemnify losses "regardless of whether" caused by the client\'s negligence.',
    check: 'Counsel view on a mutual cap; the precedent that AtliQ walked away from Kessler Mobility over unlimited liability (negotiation notes, unverified).' },
  { k: 'IP ownership', sev: 'High', ref: '§7.1 and §7.2',
    quote: '7.1 … All Deliverables shall be deemed "works made for hire" … and shall be the sole and exclusive property of Client from creation.\n7.2 … To the extent any Deliverable, or any Pre-Existing Materials incorporated into or necessary for the use of any Deliverable, does not qualify as a work made for hire, Contractor hereby irrevocably assigns … all right, title and interest therein …',
    pref: 'IP → client owns what we build for them, we keep our own stuff',
    why: 'AtliQ\'s pre-existing tools could be assigned to the client if incorporated, which may restrict reuse for other clients. Ownership also passes from creation, not on payment.',
    check: 'Which pre-existing tools would be used; a carve-out for background IP with a licence instead.' },
  { k: 'Payment terms', sev: 'High', ref: '§4.3, §4.2, §4.5',
    quote: '4.3 … Client shall pay each properly submitted, undisputed invoice within ninety (90) days after Client\'s receipt thereof.\n4.2 … Invoices not submitted within ninety (90) days after acceptance shall be deemed waived.\n4.5 … Client may set off … any amount owed by Contractor to Client under this Agreement or any other agreement.',
    pref: 'payment → 30 days, 45 max',
    why: '90 days is double the checklist maximum. Late invoices are forfeited, and set-off can reach amounts under other agreements.',
    check: 'Cash-flow impact; precedent: Trustline moved from 90 to 45 days (negotiation notes, unverified).' },
  { k: 'Termination', sev: 'High', ref: '§5.3',
    quote: '5.3 … Client may terminate this Agreement or any SOW … for any reason or no reason, upon seven (7) days\' written notice to Contractor. … Client shall have no obligation to pay for work in progress, unaccepted Deliverables, demobilization costs or anticipated profits.',
    pref: 'termination → they pay for work done',
    why: 'Only 7 days\' notice, one-sided, and work in progress would not be paid if the client terminates for convenience.',
    check: 'Payment for work performed to the termination date; a longer or mutual notice period.' },
]
function HarringtonSlide() {
  const [sel, setSel] = useState(0)
  const r = RISKS[sel]
  return (
    <>
      <div {...rv(0)}><div className="kicker">Example contract analysis</div><h1 className="st">Harrington Health Systems: draft MSA</h1>
        <p className="lede" style={{ marginBottom: 8 }}>US healthcare client · $210,000 · client's paper · requested by 1 Oct. Select a risk category.</p></div>
      <div {...rv(1)} className="rv" role="note" style={{ marginBottom: 10, fontSize: '.8em' }}>
        <span className="chip risk">Potential risks, not legal conclusions</span> <span className="muted">Clauses quoted from the draft (shortened with …). Severity comes from AtliQ's checklist rules; counsel and Karandeep decide.</span>
      </div>
      <div {...rv(2)} className="rv">
        <div className="htabs" role="tablist" aria-label="Risk categories">
          {RISKS.map((x, i) => (
            <button key={x.k} role="tab" aria-selected={sel === i} aria-controls="risk-panel" className="pick" onClick={() => setSel(i)}>
              <span className="pt">{x.k}</span>
              <span><span className={`chip ${x.sev === 'Critical' ? 'crit' : 'risk'}`}>{x.sev}</span> <span className="ps" style={{ display: 'inline' }}>{x.ref}</span></span>
            </button>))}
        </div>
        <div key={sel} id="risk-panel" className="panel swap split" role="tabpanel" aria-label={r.k}>
          <div>
            <div className="lab">Fact: from the contract · {r.ref}</div>
            <blockquote className="q verbatim">{r.quote}</blockquote>
            <div className="lab">AtliQ preference (Karandeep's checklist, March 2024)</div>
            <p style={{ margin: 0 }}>"{r.pref}"</p>
          </div>
          <div>
            <div className="lab">Interpretation: why it may matter</div>
            <p style={{ margin: 0 }}>{r.why}</p>
            <div className="lab">To verify before deciding</div>
            <p style={{ margin: 0 }}>{r.check}</p>
          </div>
        </div>
      </div>
      <div {...rv(3)} className="rv" style={{ marginTop: 10 }}>
        <Expander title="Also surfaced for this deal: documents, insurance and data">
          <ul className="clean">
            <li>The HIPAA Business Associate Agreement is <b>draft only</b>; the client wants it signed with the MSA.</li>
            <li>Cyber insurance required: $5M (§13.1). Karandeep mentioned AtliQ's policy is $1M (meeting note, unverified).</li>
            <li>No PHI outside the US without consent (§12.4). The existing intercompany BAA's schedule does not name Harrington.</li>
            <li>The freelancer agreement for Daniel Ortiz (brought in for Harrington) has no BAA terms.</li>
          </ul>
        </Expander>
      </div>
      <Src>incoming/…harrington_health_msa_draft.md; checklist; negotiation notes; meeting note 2026-09-27; tracker C-023. MVP: 18 findings (3 Critical, 9 High).</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 10. Architecture */
function ArchitectureSlide() {
  const rows: [string, string, string][] = [
    ['Frontend', 'React 19 + TypeScript + Vite', 'Dashboard, register, review workspace, Q&A, obligations, upload, and this presentation'],
    ['Backend / API', 'Python + FastAPI', 'Runs locally on 127.0.0.1:8000; serves the API and the built frontend'],
    ['Document processing', 'pypdf, python-docx, clause splitter', 'PDF/DOCX → Markdown with clause numbers, headings, pages; quality warnings'],
    ['Analysis engine', 'Deterministic rules + commitment register', 'Checklist rules, conflict detection, entity/companion checks, obligations'],
    ['Search', 'Local BM25 index', 'Clauses, negotiation notes and tracker rows; no external service'],
    ['AI (optional)', 'Groq (gpt-oss-120b) or Anthropic (Claude)', 'Grounded Q&A and AI risk review; consent per request; verbatim citation check'],
    ['Database', 'SQLite', 'Tracker import, uploads, findings, append-only review log, AI-call audit log'],
  ]
  return (
    <>
      <div {...rv(0)}><div className="kicker">Technology architecture</div><h1 className="st">A hybrid of rules and AI, running locally</h1>
        <p className="lede">Each layer is a separate module, so extraction, analysis, search and UI can evolve independently.</p></div>
      <div {...rv(1)} className="table-wrap rv">
        <table className="pt">
          <thead><tr><th>Layer</th><th>Technology</th><th>Responsibility</th></tr></thead>
          <tbody>{rows.map(r => <tr key={r[0]}><td><b>{r[0]}</b></td><td>{r[1]}</td><td>{r[2]}</td></tr>)}</tbody>
        </table>
      </div>
      <div {...rv(2)} className="cols c2 rv" style={{ marginTop: 12 }}>
        <Expander title="Why rules for policy and AI for language?">
          <p>PRD §5 recommends a hybrid architecture: checklist deviations, entity mismatches and document-status rules should be explainable and testable, so they are deterministic. Generation is constrained to retrieved evidence. Severity is kept separate from confidence.</p>
        </Expander>
        <Expander title="How data is protected">
          <p>The server listens only on this computer. Nothing leaves the machine unless an AI key is configured <b>and</b> the user ticks a consent box naming the provider. Contract text is passed to the model as data, with instructions to ignore any commands inside it. Every AI call is logged.</p>
        </Expander>
      </div>
      <Src>contractiq/backend (config, corpus, clauses, extraction, rules, commitments, checks, obligations, search, llm, engine, db, app); PRD §5.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 11. Success metrics */
function MetricsSlide() {
  const [view, setView] = useState<'target' | 'status'>('target')
  const rows: [string, string, string][] = [
    ['Response time', 'Evidence-backed findings within 5 minutes of uploading a supported contract', 'Analysis of the 32-document dataset completes at server start in about 1–2 seconds on the development laptop (informal observation, not a benchmark)'],
    ['Risk accuracy', '≥ 80% of High/Critical findings judged relevant by the reviewer', 'Not yet measured. Reviewer dispositions are captured in the app so this can be calculated in the pilot.'],
    ['Evidence quality', 'Zero material unsupported claims in exported summaries; ≥ 80% evidence-backed review completion', 'Every rule finding quotes its clause; AI citations that are not verbatim are removed. Not yet measured in a pilot.'],
    ['Conflict detection', 'Historical conflict detection rate (Discovery); conflict recall on an AtliQ gold set (PRD §5, threshold to be set)', '6 potential conflicts flagged in 15 drafts, each needing confirmation. Recall not measured; no gold set yet.'],
    ['Obligation tracking', 'Track deadlines, renewals and post-signature obligations (goal; no numeric target in the PRD)', '70 obligations and deadlines extracted; owners start as "Unassigned". Coverage not yet measured.'],
    ['Manual effort', '30% reduction in review-cycle time vs a measured manual baseline', 'Baseline not yet measured. Meeting notes: 3–4 hours per client-paper MSA.'],
  ]
  return (
    <>
      <div {...rv(0)}><div className="kicker">Success metrics</div><h1 className="st">How we will know it worked</h1>
        <p className="lede">PRD targets for a 90-day controlled internal pilot (planned Q1 2027). Toggle to compare targets with today's MVP status. No pilot results exist yet.</p></div>
      <div {...rv(1)} className="rv">
        <div className="seg" role="group" aria-label="Metric view">
          <button aria-pressed={view === 'target'} onClick={() => setView('target')}>Target (PRD / Discovery)</button>
          <button aria-pressed={view === 'status'} onClick={() => setView('status')}>MVP status today</button>
        </div>
      </div>
      <div {...rv(2)} className="table-wrap rv">
        <table className="pt swap" key={view}>
          <thead><tr><th style={{ width: '22%' }}>Metric</th><th>{view === 'target' ? 'Target' : 'Current status'}</th></tr></thead>
          <tbody>{rows.map(r => <tr key={r[0]} className="panel-row"><td><b>{r[0]}</b></td><td>{view === 'target' ? r[1] : r[2]}</td></tr>)}</tbody>
        </table>
      </div>
      <div {...rv(3)} className="rv" style={{ marginTop: 10 }}>
        <Expander title="Also tracked in discovery: reviewer adoption rate">
          <p>Whether Karandeep (and later sales, finance and counsel) actually use the workspace for each review. This needs the pilot; it cannot be measured on the dataset alone.</p>
        </Expander>
      </div>
      <Src>PRD §1 "How will we know it worked?", §2.4, §5; Discovery workbook success metrics; MVP observations on the dataset.</Src>
    </>
  )
}

/* ------------------------------------------------------------------ 12. Conclusion */
function ConclusionSlide() {
  return (
    <>
      <div {...rv(0)}><div className="kicker">Conclusion &amp; future scope</div><h1 className="st">Faster, more consistent reviews, with humans in charge</h1></div>
      <div className="cols c3">
        <div {...rv(1)} className="pcard accent rv"><h3>Value delivered</h3>
          <ul className="clean">
            <li>One place to see risks, prior commitments, entity issues and missing documents</li>
            <li>Every finding traceable to its source text and evidence type</li>
            <li>Decisions recorded in an audit trail; counsel gets a focused package</li>
            <li>Surfaces issues no one had listed, e.g. Al Noor's GCC non-compete vs Gulf Crown</li>
          </ul></div>
        <div {...rv(2)} className="pcard warn rv"><h3>Current limitations</h3>
          <ul className="clean">
            <li>Rules tuned on 32 synthetic documents; new wording may be missed</li>
            <li>Document–tracker linking and conflict matching are heuristic</li>
            <li>No OCR installed; no user accounts or access control</li>
            <li>13 signed contracts are missing from the repository, so their commitments are unknown</li>
            <li>AI depends on the provider and its rate limits; output is never legal advice</li>
          </ul></div>
        <div {...rv(3)} className="pcard primary rv"><h3>Next priorities</h3>
          <ol className="clean" style={{ paddingLeft: '1.2em' }}>
            <li>Build a gold evaluation set; measure precision, recall and citation validity</li>
            <li>Approved, versioned checklist owned by Karandeep</li>
            <li>Collect missing executed contracts and reconcile the tracker</li>
            <li>Access control, OCR and reviewer-feedback learning</li>
            <li>Controlled internal pilot (planned Q1 2027)</li>
          </ol></div>
      </div>
      <div {...rv(4)} className="rv" style={{ marginTop: 18, textAlign: 'center' }}>
        <p style={{ fontSize: '1.1em', fontWeight: 650 }}>ContractIQ shortens the search. Karandeep makes the call.</p>
        <a className="deck-tbtn" href="#/">Open the live ContractIQ app</a>
      </div>
      <Src>PRD §1, §5, §13 scope intent; README feature-status section of the MVP.</Src>
    </>
  )
}

export const SLIDES: SlideDef[] = [
  { id: 'title', title: 'AtliQ ContractIQ', render: () => <TitleSlide />, notes: [
    'Introduce the product: an AI-assisted contract review workspace for AtliQ, a company with no in-house legal team.',
    'Key message: it finds evidence, Karandeep makes decisions.',
    'Mention this is a working MVP built on the AtliQ dataset, not a mock-up.'] },
  { id: 'problem', title: 'Problem discovery', render: () => <ProblemSlide />, notes: [
    'Contract volume nearly doubled; one person reviews everything, usually late at night.',
    'Brightwater shows the cost of a missed clause; ShopSwift shows the cost of a slow queue.',
    'Open the 5 Whys to explain the root cause: no governance model or shared source of truth.'] },
  { id: 'persona', title: 'Target persona', render: () => <PersonaSlide />, notes: [
    'Karandeep signs for both entities. He has the commercial context but no legal support.',
    'Read the empathy-map question: it captures the core fear of conflicting commitments.',
    'Secondary users matter for adoption, but the MVP is built for Karandeep first.'] },
  { id: 'pains', title: 'Pain points', render: () => <PainSlide />, notes: [
    'Click through two or three pain points; each panel quotes AtliQ\'s own records as evidence.',
    'Emphasise that these come from discovery research and are backed by the dataset, not assumptions.'] },
  { id: 'workflow', title: 'Current workflow', render: () => <WorkflowSlide />, notes: [
    'Eight steps from PRD §2.1. Open step 4 (conflict search) and step 6 (companion documents): the hardest to do manually.',
    'Bottom cards: the four places knowledge lives today: files, colleagues, memory, counsel.'] },
  { id: 'solution', title: 'Proposed solution', render: () => <SolutionSlide />, notes: [
    'Evidence first, executed contracts outrank notes, rules for policy.',
    'Be explicit about what the tool will not do: no signing, no legal conclusions.',
    'Open the AI limits section to explain verbatim citation checks and demo mode.'] },
  { id: 'features', title: 'Core features', render: () => <FeaturesSlide />, notes: [
    'Click Historical intelligence and Document conversion. Point out the status chips: implemented vs partly implemented vs planned.',
    'OCR and reminders are the honest gaps.'] },
  { id: 'journey', title: 'User journey', render: () => <JourneySlide />, notes: [
    'Step through quickly; slow down at step 4 (evidence) and step 8 (human decision outside the tool).',
    'Optional: switch to the live app to show the Harrington workspace.'] },
  { id: 'harrington', title: 'Example: Harrington MSA', render: () => <HarringtonSlide />, notes: [
    'Walk through liquidated damages and liability first: both flagged Critical by the checklist rules.',
    'Stress the wording: "potential risk", "to verify". These are flags for review, not legal opinions.',
    'Open the bottom section: the BAA and insurance gap show why companion-document checks matter.'] },
  { id: 'architecture', title: 'Technology architecture', render: () => <ArchitectureSlide />, notes: [
    'Explain in plain language: a web app on top of a local Python service and a small database.',
    'AI is optional and consent-based; without a key the app runs in a labelled demo mode.'] },
  { id: 'metrics', title: 'Success metrics', render: () => <MetricsSlide />, notes: [
    'These are PRD targets for the pilot. Toggle to "MVP status" to be transparent that most are not yet measured.',
    'The next step to make them measurable is a gold evaluation set.'] },
  { id: 'conclusion', title: 'Conclusion & future scope', render: () => <ConclusionSlide />, notes: [
    'Summarise: value, honest limitations, prioritised next steps.',
    'Close with the line: ContractIQ shortens the search; Karandeep makes the call. Invite questions or a live demo.'] },
]
