"""Loads the user's dataset (read-only): contract tracker, contract documents and notes.

Every document is tagged with an *evidence type* so the UI never presents a draft, a note or a
tracker row as a binding obligation (PRD FR-5 / context rule "executed agreements outrank notes").
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .clauses import Clause, split_clauses, plain
from .config import DATASET_DIR

EVIDENCE_LABELS = {
    "executed": "Executed contract",
    "draft": "Draft (not executed)",
    "uploaded": "Uploaded document (execution status unverified)",
    "negotiation_note": "Negotiation note (unreviewed, unverified)",
    "meeting_note": "Meeting note (internal, unverified)",
    "company_reference": "Company reference document",
    "checklist": "Company preference (unapproved personal checklist)",
    "tracker": "Tracker row (metadata only — not proof of execution)",
}

TRACKER_COLUMNS = ["contract_id", "counterparty", "doc_type", "atliq_entity", "client_country", "requested_by",
                   "received_date", "status", "signed_date", "expiry_date", "value_usd", "file_location",
                   "restrictive_clauses", "notes"]

STOP_TOKENS = {"inc", "pvt", "ltd", "llc", "group", "co", "the", "and", "&", "gmbh", "systems", "technologies",
               "hospitality", "hotels", "resorts", "intercompany", "private", "limited", "capital", "clinics"}


@dataclass
class Document:
    doc_id: str
    path: str | None
    filename: str
    kind: str                     # executed | draft | uploaded | negotiation_note | meeting_note | ...
    title: str
    text: str
    provenance: str = ""
    doc_date: str | None = None
    clauses: list[Clause] = field(default_factory=list)
    atliq_term: str | None = None          # how the contract refers to AtliQ, e.g. "Contractor"
    counterparty_term: str | None = None
    counterparty_name: str | None = None
    atliq_entity: str | None = None        # "AtliQ Inc" | "AtliQ Technologies Pvt Ltd" | None
    atliq_role: str = "supplier"           # supplier | buyer | partner | nda
    tracker_ids: list[str] = field(default_factory=list)
    tracker_match_basis: str = ""
    quality: list[dict] = field(default_factory=list)
    upload_context: dict = field(default_factory=dict)

    @property
    def evidence_label(self) -> str:
        return EVIDENCE_LABELS.get(self.kind, self.kind)

    @property
    def is_contract(self) -> bool:
        return self.kind in ("executed", "draft", "uploaded")

    def summary(self) -> dict:
        return {
            "doc_id": self.doc_id, "filename": self.filename, "kind": self.kind, "evidence_label": self.evidence_label,
            "title": self.title, "provenance": self.provenance, "doc_date": self.doc_date,
            "atliq_term": self.atliq_term, "counterparty_term": self.counterparty_term,
            "counterparty_name": self.counterparty_name, "atliq_entity": self.atliq_entity,
            "atliq_role": self.atliq_role, "tracker_ids": self.tracker_ids,
            "tracker_match_basis": self.tracker_match_basis, "quality": self.quality,
            "clause_count": len(self.clauses), "upload_context": self.upload_context,
        }


# ---------------------------------------------------------------- tracker

def load_tracker(path: Path | None = None) -> list[dict]:
    path = path or DATASET_DIR / "contract_tracker.csv"
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        row = {c: (r.get(c) or "").strip() for c in TRACKER_COLUMNS}
        row["value_usd_num"] = _num(row["value_usd"])
        out.append(row)
    return out


def _num(s: str):
    try:
        return float(s.replace(",", "")) if s else None
    except ValueError:
        return None


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------- documents

FIRST_ITALIC_RE = re.compile(r"^\*\((.+?)\)\*\s*$")


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+)$", line)
        if m:
            return plain(m.group(1))
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("*(") and len(s) < 90 and s.upper() == s and re.search(r"[A-Z]{4}", s):
            return plain(s)
    return fallback


def _provenance(text: str) -> str:
    for line in text.splitlines()[:5]:
        m = FIRST_ITALIC_RE.match(line.strip())
        if m:
            return m.group(1)
    return ""


DEFINED_TERM_RE = re.compile(r'(?:\(|hereinafter(?:\s+referred\s+to\s+as)?)[^()"“\n]{0,60}?["“](?:\*\*)?([^*"”\n]{2,40}?)(?:\*\*)?["”]')
ENTITYISH_RE = re.compile(r"\b(inc\.?|ltd|limited|llc|l\.l\.c|corporation|company|gmbh|co\.|pte|individual|residing|"
                          r"resident|nonprofit|incorporated|joint stock|freelance|proprietor|s/o|aged)\b", re.I)
SKIP_TERMS = {"agreement", "party", "parties", "effective date", "services", "purpose", "msa", "nda",
              "proposed transaction", "confidential information", "gst", "indemnifying party"}


def entity_in(text: str) -> str | None:
    low = text.lower()
    inc = bool(re.search(r"atliq inc\b", low))
    pvt = bool(re.search(r"atliq techn[o0]logies (pvt|private)", low))
    if inc and pvt:
        return "Both entities named"
    return "AtliQ Inc" if inc else "AtliQ Technologies Pvt Ltd" if pvt else None


def detect_parties(doc: Document) -> None:
    head = doc.text[:6000]
    prev = 0
    for m in DEFINED_TERM_RE.finditer(head):
        term = m.group(1).strip()
        window = head[prev:m.start()]
        prev = m.end()
        if term.lower() in SKIP_TERMS or "date" in term.lower():
            continue
        if not ENTITYISH_RE.search(window) and "atliq" not in window.lower():
            continue
        names = re.findall(r"\*\*([^*]{3,120})\*\*", window)
        last = names[-1] if names else window[-400:]
        is_atliq = bool(re.search(r"atliq", last, re.I))
        if is_atliq and not doc.atliq_term:
            doc.atliq_term = term
            doc.atliq_entity = entity_in(last if names else window[-600:])
        elif not is_atliq and not doc.counterparty_term:
            doc.counterparty_term = term
            nm = re.findall(r"\*\*([^*]{3,80})\*\*", window)
            cands = [plain(x).rstrip(",") for x in nm if ENTITYISH_RE.search(x) or x.isupper()]
            if cands:
                doc.counterparty_name = cands[-1]
    if not doc.atliq_entity:
        doc.atliq_entity = entity_in(head[:3000])
    t = doc.title.lower()
    if "intercompany" in doc.filename.lower() or doc.atliq_entity == "Both entities named" and "subcontractor" in t:
        doc.atliq_role = "intercompany"
    elif "non-disclosure" in t or "nondisclosure" in t:
        doc.atliq_role = "nda"
    elif any(k in t for k in ("contractor", "subcontractor", "vendor")):
        doc.atliq_role = "buyer"
    elif "partnership" in t:
        doc.atliq_role = "partner"
    elif "waiver" in doc.filename.lower() or "consent" in t:
        doc.atliq_role = "letter"


def quality_warnings(doc: Document) -> list[dict]:
    """Extraction-quality signals (PRD FR-12). Unreadable text must never be reported as 'not found'."""
    w = []
    text = doc.text
    if re.search(r"scanned|OCR", doc.provenance, re.I):
        w.append({"level": "warning", "code": "ocr_source",
                  "message": "Text comes from OCR of a scanned copy. Numbers and names may be misread; "
                             "verify any extracted value against the signed original."})
    illeg = len(re.findall(r"\[illegible\]", text, re.I))
    if illeg:
        w.append({"level": "warning", "code": "illegible",
                  "message": f"{illeg} illegible span(s) in the extracted text. Clauses touching these spans "
                             "cannot be verified; absence of a term there must not be read as 'not found'."})
    confusable = re.findall(r"\b(?=[A-Za-z]*\d)(?=\d*[A-Za-z])[A-Za-z0-9]{3,}\b", text)
    confusable = [c for c in confusable if re.search(r"[0O][A-Z]|[A-Z]0|\bl\d|\dl\b", c) and not re.match(r"^[A-Z]{1,4}\d+$|^\d+[A-Za-z]{1,3}$", c)]
    if len(confusable) >= 3:
        w.append({"level": "warning", "code": "ocr_confusables",
                  "message": f"Possible OCR character confusions (e.g. {', '.join(sorted(set(confusable))[:5])})."})
    if len(text.strip()) < 400:
        w.append({"level": "error", "code": "little_text",
                  "message": "Very little text was extracted. The document may be scanned or image-only."})
    if "attached separately" in text.lower():
        w.append({"level": "info", "code": "missing_attachment",
                  "message": "The document refers to schedules/exhibits 'attached separately' that are not in "
                             "this file; their terms were not reviewed."})
    return w


def load_document(path: Path, kind: str) -> Document:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"(\d{4}-\d{2}-\d{2})_", path.name)
    doc = Document(doc_id=path.stem, path=str(path), filename=path.name, kind=kind,
                   title=_title(text, path.stem), text=text, provenance=_provenance(text),
                   doc_date=m.group(1) if m else None)
    doc.clauses = split_clauses(text)
    if doc.is_contract:
        detect_parties(doc)
    doc.quality = quality_warnings(doc) if doc.is_contract else []
    return doc


def load_corpus() -> list[Document]:
    docs: list[Document] = []
    for sub, kind in (("signed_contracts", "executed"), ("incoming", "draft")):
        for p in sorted((DATASET_DIR / sub).glob("*.md")):
            docs.append(load_document(p, kind))
    for p in sorted((DATASET_DIR / "meeting_notes").glob("*.md")):
        docs.append(load_document(p, "meeting_note"))
    extra = {"negotiation_notes.md": "negotiation_note", "karandeep_contract_checklist.md": "checklist",
             "atliq_entities.md": "company_reference"}
    for name, kind in extra.items():
        p = DATASET_DIR / name
        if p.exists():
            docs.append(load_document(p, kind))
    return docs


# ---------------------------------------------------------------- linking documents <-> tracker

DOC_TYPE_KEYS = [
    ("baa", ["baa", "business associate"]), ("nda", ["nda", "non-disclosure", "nondisclosure"]),
    ("waiver", ["waiver", "consent"]), ("sow", ["sow", "statement of work"]),
    ("contractor", ["contractor"]), ("subcontractor", ["subcontractor"]),
    ("partnership", ["partnership"]), ("pilot", ["pilot"]), ("msa", ["msa", "services agreement", "master"]),
]


def _type_tags(s: str) -> set[str]:
    s = s.lower()
    tags = {k for k, keys in DOC_TYPE_KEYS if any(x in s for x in keys)}
    if "subcontractor" in tags:
        tags.discard("contractor")
    return tags


def cp_tokens(name: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+", name.lower())
    return [t for t in toks if t not in STOP_TOKENS and len(t) > 2]


def link_documents(docs: list[Document], tracker: list[dict]) -> None:
    """Match each contract document to tracker rows by counterparty, document type and date.

    The match basis is recorded and shown in the UI; it is a heuristic, not a verified link.
    """
    for doc in docs:
        if not doc.is_contract:
            continue
        if doc.upload_context.get("tracker_id"):
            doc.tracker_ids = [doc.upload_context["tracker_id"]]
            doc.tracker_match_basis = "Selected by user at upload"
            continue
        fname = doc.filename.lower().replace("-", "_")
        ftags = _type_tags(fname.replace("_", " ") + " " + doc.title)
        best, best_score, basis = None, 0, ""
        for row in tracker:
            toks = cp_tokens(row["counterparty"])
            if not toks:
                continue
            if "intercompany" in row["counterparty"].lower():
                hit = "intercompany" in fname
            else:
                hit = toks[0] in fname or (len(toks) > 1 and all(t in fname for t in toks[:2]))
            if not hit:
                continue
            score, why = 10, [f"counterparty '{row['counterparty']}'"]
            rtags = _type_tags(row["doc_type"])
            if rtags & ftags:
                score += 5
                why.append(f"type '{row['doc_type']}'")
            elif rtags and ftags:
                score -= 3
            dates = {row["signed_date"], row["received_date"]}
            if doc.doc_date and doc.doc_date in dates:
                score += 8
                why.append(f"date {doc.doc_date}")
            if score > best_score:
                best, best_score, basis = row, score, ", ".join(why)
        if best and best_score >= 15:
            doc.tracker_ids = [best["contract_id"]]
            doc.tracker_match_basis = "Heuristic match on " + basis
            if not doc.counterparty_name or doc.counterparty_name.lower() in ("client", "company", "customer"):
                doc.counterparty_name = best["counterparty"]
        elif best:
            doc.tracker_ids = []
            doc.tracker_match_basis = f"No confident tracker match (closest: {best['contract_id']})"


# ---------------------------------------------------------------- negotiation notes

def parse_negotiation_entries(doc: Document) -> list[dict]:
    """Split Jay's reconstruction into one entry per past negotiation."""
    entries, cur = [], None
    for line in doc.text.splitlines():
        m = re.match(r"^\*\*(.+?)\*\*\s*$", line.strip())
        if m:
            if cur:
                entries.append(cur)
            cur = {"title": m.group(1), "lines": []}
            continue
        if cur is not None and line.strip().startswith("-"):
            cur["lines"].append(line.strip()[1:].strip())
        elif cur is not None and line.strip().startswith("---"):
            entries.append(cur)
            cur = None
    if cur:
        entries.append(cur)
    for e in entries:
        e["text"] = "\n".join(e["lines"])
        e["is_exception"] = bool(re.search(r"exception|one-off|only —|only -|not our new standard", e["text"], re.I))
        e["outcome"] = ("walked away / not signed" if re.search(r"didn't sign|lost|walked away", e["title"] + e["text"], re.I)
                        else "signed")
        e["counterparty_tokens"] = cp_tokens(e["title"].split("—")[0])
    return entries
