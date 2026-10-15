# AtliQ ContractIQ — MVP prototype

AI-assisted contract intelligence and risk-review workspace for AtliQ, built from the PRD (`../PRD capstone.docx`) and the dataset in `../Dataset/`.
It is **decision support only**: it never signs, approves, rejects, redlines or sends a contract.

> The original PRD and dataset are only **read**. Nothing in `Dataset/` is modified; all app data lives in `contractiq/data/`.
> No records were added to the dataset.

---

## 0. How to open the app (read this first)

**Double-click `Start ContractIQ.bat`** (in this `contractiq` folder). It sets things up on first run, starts the local
server and opens **http://127.0.0.1:8000** in your browser. Keep its window open while you work; close it to stop.

Do **not** double-click `frontend/index.html` or `frontend/dist/index.html`. That opens the page as `file://…`, and it
cannot work there:

* browsers block the app's JavaScript bundle (an ES module) when it is loaded from `file://` (CORS "origin null");
* the app is not static: contracts, analysis, search, saved reviews (SQLite), uploads and AI all come from the local
  Python/FastAPI server through `/api/...`, which does not exist on `file://`.

Opening either file directly now shows these instructions instead of a blank page. A standalone single-HTML version
is not supported without removing the backend features (reading the dataset, rules engine, database, uploads), so
the app is designed to be opened through the local server.

If the page is ever blank when served over http, press **Ctrl+F5**. `index.html` is served with no-cache headers and
the bundle files are content-hashed, so a hard refresh always picks up the current build.

### Project presentation

An interactive 12-slide deck about the project is built into the app at **http://127.0.0.1:8000/#/presentation**
(also linked as "Project presentation" in the sidebar). Keys: ←/→ (or PageUp/PageDown, Space) to move, Home/End,
**F** full screen, **N** speaker notes, **O** all slides, Esc to close panels. Source: `frontend/src/presentation/`.
It contains no images or diagrams by design; all facts come from the PRD, the discovery workbook, the dataset and the MVP.

## 1. Quick start (Windows, PowerShell)

Prerequisites: Python 3.11+ (tested on 3.14), Node.js 20+ (tested on 24 LTS) — Node is only needed to (re)build the UI.

```powershell
cd "C:\Users\Shubham\Desktop\Capstone Project\contractiq"

# backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# frontend (React + TypeScript + Vite) — build once
cd frontend
npm install
npm run build
cd ..

# run (serves API + built UI on http://127.0.0.1:8000)
.\.venv\Scripts\python run.py
```

Open http://127.0.0.1:8000.

### Optional: enable AI (otherwise the app runs in labelled demo mode)

```powershell
$env:GROQ_API_KEY = "<your Groq key>"          # or: $env:ANTHROPIC_API_KEY = "<key>"
.\.venv\Scripts\python run.py
```

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | – | Enables AI via Groq (`openai/gpt-oss-120b`) |
| `CONTRACTIQ_GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model id |
| `ANTHROPIC_API_KEY` | – | Enables AI via Anthropic (`claude-opus-5-5`) |
| `CONTRACTIQ_AI_PROVIDER` | auto | Force `groq` or `anthropic` when both keys exist |
| `CONTRACTIQ_AS_OF` | `2026-09-28` | Review date (the dataset README says to treat 2026-09-28 as "today") |
| `CONTRACTIQ_DATASET_DIR` | `../Dataset` | Where the source data is read from |
| `CONTRACTIQ_DATA_DIR` | `./data` | SQLite DB, uploads, extracted Markdown |
| `CONTRACTIQ_AI_REVIEW_CHARS` | `14000` | Max clause text sent per AI risk review (keeps within provider rate limits) |

Keys are read from the environment only. Never commit them or put them in files.

### Development mode (hot reload)

```powershell
# terminal 1
.\.venv\Scripts\python run.py
# terminal 2
cd frontend; npm run dev        # http://127.0.0.1:5173, proxies /api to :8000
```

### Tests

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```
25 regression tests run against the real dataset (no network): rules, conflicts, entity/companion checks, tracker data quality,
extraction errors, quote verification, append-only audit log, demo-mode behaviour, exports.

---

## 2. How the PRD and dataset are used

| Source | Used as |
|---|---|
| `contract_tracker.csv` (48 rows) | Contract register, imported read-only into SQLite on every start. Blanks stay blank; tracker data is labelled *metadata, not proof of execution*. |
| `signed_contracts/*.md` (17) | **Executed** evidence: commitment register (non-competes, exclusivity, MFN, IP assignments), conflict checks, obligations. |
| `incoming/*.md` (15) | **Drafts** under review: rules, conflicts, entity & companion checks. |
| `karandeep_contract_checklist.md` | Company preferences quoted on findings (labelled "unapproved personal checklist, March 2024"). |
| `negotiation_notes.md` | Precedents attached to findings, labelled *unverified*; deal-specific exceptions (e.g. Al Noor 10% LD cap) flagged as **not policy**. |
| `meeting_notes/*.md` | Searchable context; e.g. the $1M cyber-insurance figure is quoted as "meeting note, unverified". |
| `atliq_entities.md` | Entity / invoicing / currency rules (Inc = US clients, USD; Pvt Ltd = all other regions). |

PRD requirements → implementation: FR-1 upload + deal context · FR-2/3 prioritised findings with exact excerpt + section/page · FR-4 conflicts with both excerpts, status, rationale, missing facts ·
FR-5 evidence-type labels everywhere · FR-6 deal-specific exceptions surfaced as such · FR-7 entity/law checks + non-destructive corrections ·
FR-8 companion documents (present / draft / unverified / missing) · FR-9 grounded Q&A with refusal · FR-10 dispositions + notes in an append-only audit trail ·
FR-11/14 Markdown review summary and counsel escalation package · FR-12 extraction-quality warnings · FR-13 duplicate / conflicting tracker records surfaced, never auto-resolved ·
FR-16 no approve/sign/send capability anywhere.

---

## 3. Feature status

### Works (deterministic, runs locally, verified against the dataset)

* **Dashboard** — total contracts (48 rows, duplicate C-010/C-011 flagged), under review (9 + 2 with blank status), high-risk drafts / executed contracts, expirations within 90 days (C-042 CareBridge MSA 5 Oct, C-033 PixelCraft 19 Oct), possible conflicts, requested review deadlines parsed from tracker notes.
* **Contract register** — every tracker column, search + filters (status, entity, country, risk, data-quality issues), linked documents, row-level data-quality issues.
* **Document processing** — PDF (pypdf, per-page with page markers), DOCX (python-docx: heading styles → Markdown headings, tables → Markdown tables), Markdown/TXT. Clause segmentation keeps clause numbers, headings and page numbers. Export of extracted content as `.md`. Clear errors for corrupt PDFs, password-protected PDFs, legacy `.doc`, empty or image-only files.
* **Risk rules** (checklist-based): liquidated damages (rate, base, cap, client-delay exclusion, cumulative remedies), liability (uncapped, one-sided, multiples, carve-outs, mandatory-law style), indemnity (other party's negligence, broad one-way), payment (days, pay-when-paid, set-off, invoice forfeiture, discretionary FX), termination (convenience notice, work-in-progress payment), IP (pre-existing IP assignment, work-for-hire, contractor-retained IP, sole-owner warranty), confidentiality (one-way "mutual" NDA, residuals, perpetual), exclusivity / non-compete / MFN, data security (breach windows, cost burden, offshore limits, US-only subcontractors, AI-training limits), insurance vs. reported cover, governing law / forum / prevailing language. Buyer-side documents (freelancers, agencies) are assessed for fairness, per Karandeep's note.
* **Historical intelligence** — commitment register built only from executed contracts, with computed end dates (e.g. Al Noor non-compete active to 2029-09-14 = term end + 18 months; Orbit's expired 2025-06-30), Affiliate reach, waivers and their scope. Detected conflicts (each with both excerpts, rationale and facts still needed):
  Gulf Crown, BlueOrchid and (lower confidence) TravelHub vs Al Noor §12.1; Lakeshore rate card vs Crestline MFN §6.4; Datavane vs CloudSpan exclusivity §7.1; Rheinwerk PipeKit sole-owner warranty vs Northwind IP assignment §9.2; Rohan Iyer retained IP vs Acme ownership (chain of title). Negative results always state the searched corpus and the 13 signed contracts missing from the repository.
* **Entity & companion checks** — e.g. TravelHub (UAE client, contract names AtliQ Inc, invoices raised by Pvt Ltd), Marcus Reed (US contractor on India template); Harrington BAA draft-only, intercompany BAA not scoped to Harrington, missing BAA flow-down for Daniel Ortiz.
* **Obligations & deadlines** — expiries, auto-renewal notice dates, termination notice periods, incident-notification windows, insurance, invoice windows, confidentiality survival, restriction end dates, review deadlines; owner = "Unassigned" until set; date = "unverified" when inputs are missing; status/owner updates logged.
* **Human review** — dispositions (relevant / not relevant / resolved / needs info / escalate to counsel), notes, follow-up flag, reviewer + timestamp; append-only (DB triggers block updates/deletes); history per finding.
* **Exports** — review summary and counsel escalation package (`.md`) separating facts, interpretations, decisions, unresolved items and search coverage.
* **Q&A (demo mode)** — local BM25 search across clauses, negotiation notes and tracker rows; returns ranked passages with evidence types and related rule findings, or an explicit "insufficient evidence" message.

### AI features (real when a key is set; never simulated)

* **Grounded Q&A** — question + retrieved excerpts sent to the provider; every citation is verified verbatim against its source passage and unverifiable citations are removed; passages from other documents are marked so they are not attributed to the contract asked about.
* **AI risk review** — a capped set of risk-relevant clauses is sent; AI findings are shown separately, labelled "AI interpretation", and kept only if their quote is found verbatim in the contract.
* Both require a key **and** per-request consent in the UI that names the provider. Every AI call is logged (`ai_runs` table: what was sent, provider, model, result).
* **Demo mode** (no key): clearly labelled in the header, workspace and Q&A; rule findings are never presented as AI output.

### Simulated / heuristic (be aware)

* Clause classification and value extraction use deterministic patterns tuned on this dataset. They will miss phrasings not seen here; low-confidence items are marked.
* Document ↔ tracker linking is heuristic (counterparty + type + date) and shows its match basis.
* Sector/geography matching for conflicts is keyword-based and always lists the legal interpretation still needed.

### Incomplete / not in this MVP

* OCR: code path exists (`pytesseract` + `pypdfium2` + Tesseract binary) but those are **not installed**; scanned pages are reported as unreadable instead. The dataset's scanned contract (Orbit) is already OCR text and is flagged for OCR errors.
* No user accounts / permission filtering (PRD access-control requirements); single local user with a free-text reviewer name.
* No versioned/approved checklist management, no feedback-learning loop (FR-15), no authoritative-record confirmation workflow for duplicates (FR-13 is surfaced, not workflow-enforced).
* Word automatic numbering is not recoverable from DOCX text (a warning is shown).
* Groq free-tier rate limits can reject an AI review shortly after other AI calls; the app retries once and then shows the error.

---

## 4. Architecture

```
contractiq/
├── backend/            FastAPI + SQLite (Python)
│   ├── config.py       env-based settings
│   ├── corpus.py       dataset loading, evidence types, party detection, tracker linking
│   ├── clauses.py      Markdown → citable clauses (numbers, headings, pages)
│   ├── extraction.py   PDF / DOCX / MD → Markdown, error + quality reporting, optional OCR
│   ├── rules.py        checklist risk rules → findings (fact / interpretation / recommendation)
│   ├── commitments.py  commitment register + cross-agreement conflict detection
│   ├── checks.py       entity / currency / law, companion documents, tracker data quality
│   ├── obligations.py  obligations & deadlines
│   ├── search.py       local BM25 index
│   ├── llm.py          optional Groq / Anthropic calls, consent gate, verbatim quote verification
│   ├── engine.py       orchestration, Q&A, exports
│   ├── db.py           SQLite: tracker import, uploads, findings, append-only review log, AI audit log
│   └── app.py          REST API + serves the built UI
├── frontend/           React + TypeScript + Vite (lucide-react icons)
├── tests/test_core.py  regression tests on the real dataset
└── run.py              start on 127.0.0.1:8000
```

Design notes: rules for policy decisions, retrieval before generation, severity separate from confidence, executed contracts outrank notes and tracker rows, and "no conflict found" is always qualified by search coverage (PRD §5, §7.3).
UI follows the ui-ux-pro-max guidance: trust-oriented navy palette, SVG icons, visible focus, ≥4.5:1 contrast, severity shown with text + icon (not colour alone), reduced-motion support, light/dark themes, responsive down to 375 px.

## 5. Data protection

* Server binds to `127.0.0.1` only. Documents are processed locally.
* Nothing leaves the machine unless an AI key is configured **and** the user ticks a consent box for that specific request; the UI names the provider and what is sent.
* Contract text is passed to the model as delimited data with instructions to ignore embedded instructions.
* The dataset is synthetic (per its README). Treat real contracts according to your provider's data-retention terms before enabling AI.
