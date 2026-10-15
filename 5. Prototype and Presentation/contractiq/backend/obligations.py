"""Obligations and deadlines (PRD requirement 6).

Each obligation cites its source (contract clause or tracker row). Dates are only computed when the
inputs exist; otherwise the date is reported as "unverified". Owners are never guessed: every
obligation starts "Unassigned" until a reviewer sets one (stored in the DB, see db.py).
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta

from .clauses import plain
from .corpus import Document, parse_date
from .commitments import add_months

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _oid(*parts) -> str:
    return "O-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def _ob(doc_id, kind, title, description, due, due_basis, source, excerpt=None, ref=None, clause_idx=None, tracker_id=None,
        requested_by=None, recurring=False):
    return {"id": _oid(doc_id, kind, ref or title), "doc_id": doc_id, "tracker_id": tracker_id, "kind": kind, "title": title,
            "description": description, "due_date": due.isoformat() if due else None,
            "date_status": "computed" if due else "unverified", "due_basis": due_basis, "source": source,
            "excerpt": excerpt, "ref": ref, "clause_idx": clause_idx, "requested_by": requested_by, "recurring": recurring,
            "owner": "Unassigned", "status": "Open"}


def _note_deadline(note: str, received: date | None, as_of: date) -> date | None:
    m = re.search(r"\b(?:by|before|need by|sign by|wants? (?:it )?by)\s+(?:\w{3}\s+)?(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*", note, re.I)
    if not m:
        return None
    day, mon = int(m.group(1)), MONTHS[m.group(2).lower()[:3]]
    year = (received or as_of).year
    d = date(year, mon, day)
    if received and d < received:
        d = date(year + 1, mon, day)
    return d


def extract_obligations(doc: Document | None, tracker_row: dict | None, as_of: date) -> list[dict]:
    out = []
    did = doc.doc_id if doc else None
    tid = tracker_row["contract_id"] if tracker_row else None
    req = tracker_row["requested_by"] if tracker_row else None

    # Tracker-derived: review deadlines and expiry
    if tracker_row:
        if tracker_row["status"].lower() in ("in review", "draft", "awaiting client", "") and tracker_row["notes"]:
            d = _note_deadline(tracker_row["notes"], parse_date(tracker_row["received_date"]), as_of)
            if d:
                out.append(_ob(did, "review_deadline", f"Review/signature deadline requested ({tracker_row['counterparty']})",
                               "Deadline stated in the tracker notes by the requester. Not a contractual obligation.",
                               d, "parsed from tracker notes", f"tracker {tid} notes (unverified)", tracker_row["notes"],
                               tracker_id=tid, requested_by=req))
        exp = parse_date(tracker_row["expiry_date"])
        if exp:
            out.append(_ob(did, "expiry", f"Agreement expiry — {tracker_row['counterparty']} {tracker_row['doc_type']}",
                           "Expiry date as recorded in the tracker. Decide on renewal, extension or close-out.", exp,
                           "tracker expiry_date (unverified against contract)", f"tracker {tid}", tracker_id=tid, requested_by=req))

    if not doc:
        return out
    expiry = parse_date(tracker_row["expiry_date"]) if tracker_row else None
    for c in doc.clauses:
        t = plain(c.text)
        low = t.lower()
        # auto-renewal with non-renewal notice
        if re.search(r"renew(s|ing|al)? automatically|automatically renew|auto-renew", low):
            nd = re.search(r"\(?(\d{1,3})\)?\s*days'? (?:prior )?(?:written )?notice", t)
            due, basis = None, "term end date not known — unverified"
            if nd and expiry:
                due, basis = expiry - timedelta(days=int(nd.group(1))), f"expiry {expiry} minus {nd.group(1)} days' notice"
            out.append(_ob(did, "renewal_notice", "Auto-renewal: send non-renewal notice if not renewing",
                           f"Agreement renews automatically unless notice is given ({nd.group(0) if nd else 'notice period not parsed'}).",
                           due, basis, "contract", c.text, c.ref, c.idx, tid, req))
        # termination notice periods (informational, no due date)
        if re.search(r"terminat", low) and re.search(r"for convenience|without cause|for any reason", low):
            nd = re.search(r"\(?(\d{1,3})\)?\s*days'?\s*(?:prior\s+)?(?:written\s+)?notice", t)
            if nd:
                out.append(_ob(did, "termination_notice", f"Termination-for-convenience notice: {nd.group(1)} days",
                               "Notice period that applies if either side terminates for convenience (check which party holds the right).",
                               None, "event-driven (no fixed date)", "contract", c.text, c.ref, c.idx, tid, req))
        # incident notification windows
        m = re.search(r"within\s+(?:[a-z\-]+\s+)?\(?(\d{1,3})\)?\s*hours", t, re.I)
        if m and re.search(r"breach|incident|unauthori[sz]ed", low) and "notif" in low:
            out.append(_ob(did, "incident_notification", f"Notify security incidents within {m.group(1)} hours",
                           "Operational obligation for the delivery team and incident process.", None, "event-driven",
                           "contract", c.text, c.ref, c.idx, tid, req, recurring=True))
        # insurance maintenance
        if re.search(r"shall maintain[^.]{0,80}insurance|insurance of not less than|maintain, at its own expense", low):
            out.append(_ob(did, "insurance", "Maintain required insurance cover", "Keep certificates current for the term.",
                           None, "for the term", "contract", c.text, c.ref, c.idx, tid, req, recurring=True))
        # explicit expiry in text
        m = re.search(r"expir\w* on (\d{1,2} \w+ \d{4})", t)
        if m and not expiry:
            try:
                d = datetime.strptime(m.group(1), "%d %B %Y").date()
                out.append(_ob(did, "expiry", "Agreement expiry (from contract text)", "", d, "contract text", "contract",
                               c.text, c.ref, c.idx, tid, req))
            except ValueError:
                pass
        # invoice submission windows
        if re.search(r"invoices? not submitted within", low):
            nd = re.search(r"\(?(\d{1,3})\)?\s*days", t)
            out.append(_ob(did, "invoice_window", f"Submit invoices within {nd.group(1) if nd else '?'} days of acceptance",
                           "Late invoices are deemed waived.", None, "event-driven", "contract", c.text, c.ref, c.idx, tid, req, True))
        # confidentiality survival
        m = re.search(r"(?:survive|continue)[^.]{0,40}?(\w+)\s*\((\d{1,2})\)\s*years", t, re.I)
        if m and re.search(r"confidential|obligations in this clause", low):
            due, basis = None, "term end not known — unverified"
            if expiry:
                due, basis = add_months(expiry, 12 * int(m.group(2))), f"expiry {expiry} + {m.group(2)} years"
            out.append(_ob(did, "confidentiality_survival", f"Confidentiality survives {m.group(2)} years after termination",
                           "Information must stay protected after the agreement ends.", due, basis, "contract", c.text, c.ref, c.idx, tid, req))
    return out


def restriction_obligations(register: list[dict]) -> list[dict]:
    out = []
    for cm in register:
        if cm["type"] in ("non_compete", "exclusivity", "mfn_pricing"):
            due = parse_date(cm["end"])
            out.append({**_ob(cm["doc_id"], "restriction", f"{cm['label']} — {cm['counterparty']}",
                              f"AtliQ must not breach this commitment until it ends. Sectors: {', '.join(cm['sectors']) or 'n/a'}; "
                              f"geography: {', '.join(cm['geographies']) or 'any'}.", due, cm["end_basis"], "executed contract",
                              cm["excerpt"], cm["clause_ref"], cm["clause_idx"], cm["tracker_id"]),
                        "status": "Expired" if cm["status"] == "expired" else "Open"})
    return out
