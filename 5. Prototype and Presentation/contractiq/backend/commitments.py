"""Historical contract intelligence: what has AtliQ already promised, and does a new deal collide with it?

* The commitment register is built ONLY from executed contracts (evidence type "Executed contract").
  Notes and tracker rows are attached as context, never as the commitment itself.
* A conflict is raised only when concrete evidence exists on both sides (matching sector/geography
  text, matching named asset, lower rate for the same role, ...). Each conflict lists the facts still
  needed to confirm it. A negative result is reported together with the searched corpus and its gaps.
"""
from __future__ import annotations

import calendar
import hashlib
import re
from datetime import date

from .clauses import Clause, plain
from .corpus import Document, cp_tokens, parse_date
from .rules import NUM_WORDS, restrictive_clauses

GCC = ["UAE", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman"]
EUROPE = ["Germany", "France", "Netherlands", "Spain", "Italy", "Ireland", "Belgium", "Austria", "Sweden", "Denmark",
          "Poland", "Finland", "Portugal", "UK", "Switzerland", "Norway"]
COUNTRY_PATTERNS = {
    "India": r"\bindia\b|\bmumbai\b|\bbengaluru\b|\bdelhi\b|\bchennai\b|\bhyderabad\b|\bjaipur\b|\bgoa\b",
    "UAE": r"united arab emirates|\buae\b|\bdubai\b|abu dhabi|ras al khaimah|sharjah",
    "Saudi Arabia": r"saudi|\bksa\b|riyadh|jeddah|dammam|al khobar|madinah|alula|abha",
    "Oman": r"\boman\b|muscat",
    "Qatar": r"\bqatar\b|\bdoha\b", "Kuwait": r"\bkuwait\b", "Bahrain": r"\bbahrain\b",
    "USA": r"united states|\bu\.s\.\b|\busa\b|texas|illinois|delaware|new jersey|california|ohio|houston|chicago",
    "UK": r"united kingdom|england|\blondon\b",
    "Germany": r"germany|munich|münchen|deutschland|\bdach\b",
    "Singapore": r"singapore",
}
REGION_PATTERNS = {
    "GCC": (r"\bgcc\b|gulf cooperation council|middle east", GCC),
    "Europe": (r"\beurope\b|european union|\beea\b|\beu\b", EUROPE),
}
SECTORS = {
    "hospitality": r"hotel|resort|hospitality|serviced apartment|guest analytics|revenue[- ]management",
    "travel booking": r"travel[- ]booking|online travel agenc|booking engine|fare search",
    "cloud data platform": r"lakehouse|data[- ]warehouse|unified analytics platform|competing platform|cloud data platform",
    "healthcare": r"\bpatient|\bclinic|\bhospitals?\b|\bphi\b|health system",
}


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def months_in(text: str) -> int | None:
    t = text.lower()
    for w, n in sorted(NUM_WORDS.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"\b{w}\b\s*(\([^)]*\)\s*)?months?", t):
            return n
    m = re.search(r"\((\d{1,2})\)\s*months?|\b(\d{1,2})\s*months?", t)
    if m:
        return int(m.group(1) or m.group(2))
    return None


def geographies(text: str) -> set[str]:
    t = text.lower()
    out = {c for c, p in COUNTRY_PATTERNS.items() if re.search(p, t)}
    for _, (p, members) in REGION_PATTERNS.items():
        if re.search(p, t):
            out |= set(members)
    return out


def sectors(text: str) -> dict[str, int]:
    t = text.lower()
    return {s: len(re.findall(p, t)) for s, p in SECTORS.items() if re.search(p, t)}


def _definitions_for(doc: Document, clause: Clause) -> list[Clause]:
    """Definition clauses for capitalised defined terms used in the clause (e.g. 'Hospitality Business')."""
    terms = set(re.findall(r"(?<![\w*])((?:[A-Z][a-z]+\s){0,3}(?:Business|Platform|Period|Territory|Account|GCC))\b", plain(clause.text)))
    out = []
    for c in doc.clauses:
        for term in terms:
            if re.search(rf'["“]\*?\*?{re.escape(term.strip())}\*?\*?["”]\s*(?:or [^\n]{{0,40}})?(means|has the meaning)', c.text):
                out.append(c)
    return out


def _cid(*parts) -> str:
    return "CM-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8]


def _term_end(doc: Document, tracker_by_id: dict) -> tuple[date | None, str]:
    for tid in doc.tracker_ids:
        row = tracker_by_id.get(tid)
        if row and parse_date(row["expiry_date"]):
            return parse_date(row["expiry_date"]), f"tracker {tid} expiry_date (tracker metadata, unverified)"
    m = re.search(r"expir\w* on (\d{1,2} \w+ \d{4})", doc.text)
    if m:
        try:
            from datetime import datetime
            return datetime.strptime(m.group(1), "%d %B %Y").date(), "contract text"
        except ValueError:
            pass
    return None, "unknown"


def build_register(docs: list[Document], tracker: list[dict], as_of: date) -> list[dict]:
    tracker_by_id = {r["contract_id"]: r for r in tracker}
    letters = [d for d in docs if d.kind == "executed" and d.atliq_role == "letter"]
    register = []
    for doc in docs:
        if doc.kind != "executed" or doc.atliq_role == "letter":
            continue
        term_end, term_src = _term_end(doc, tracker_by_id)
        start = parse_date(doc.doc_date)
        tracker_row = tracker_by_id.get(doc.tracker_ids[0]) if doc.tracker_ids else None

        def make(ctype, clause, scope_text, defs, binds_affiliates, tail_months, label, extra=None):
            end = None
            end_basis = ""
            if term_end:
                end = add_months(term_end, tail_months or 0)
                end_basis = f"term end {term_end.isoformat()} ({term_src})" + (f" + {tail_months} months" if tail_months else "")
            status = "unknown"
            if end:
                status = "active" if end >= as_of else "expired"
            waivers = []
            for L in letters:
                if any(t in L.text.lower() for t in cp_tokens(doc.counterparty_name or doc.doc_id)[:1]) and \
                        clause.number and re.search(rf"clause {re.escape(clause.number.split('.')[0])}\b", L.text, re.I):
                    scope = next((plain(c.text) for c in L.clauses if re.search(r"strictly limited|solely", plain(c.text), re.I)), "")
                    waivers.append({"doc_id": L.doc_id, "filename": L.filename, "scope_excerpt": scope,
                                    "covers": [p for p in re.findall(r"\*\*([^*]+)\*\*", L.text) if "LLC" in p or "Ltd" in p]})
            rec = {
                "id": _cid(doc.doc_id, ctype, clause.idx), "type": ctype, "label": label,
                "doc_id": doc.doc_id, "filename": doc.filename, "counterparty": doc.counterparty_name or doc.counterparty_term,
                "atliq_entity": doc.atliq_entity, "tracker_id": tracker_row["contract_id"] if tracker_row else None,
                "clause_ref": clause.ref, "clause_idx": clause.idx, "excerpt": clause.text,
                "definitions": [{"ref": d.ref, "excerpt": d.text} for d in defs],
                "sectors": sorted(sectors(scope_text)), "geographies": sorted(geographies(scope_text)),
                "binds_affiliates": binds_affiliates, "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None, "end_basis": end_basis or "no end date found — unverified",
                "status": status, "waivers": waivers, "evidence_label": doc.evidence_label,
                "tracker_restrictive_field": tracker_row["restrictive_clauses"] if tracker_row else None,
            }
            if extra:
                rec.update(extra)
            register.append(rec)

        for c in restrictive_clauses(doc):
            t = plain(c.text)
            if re.search(r"restricted period[\"”*\s]*means", t, re.I):
                continue
            defs = _definitions_for(doc, c)
            scope = t + " " + " ".join(plain(d.text) for d in defs)
            # include sibling clauses that refine the scope (e.g. 12.2 "services are provided in the GCC if...")
            sec = c.number.split(".")[0] if c.number else None
            sib = [x for x in doc.clauses if sec and x.number and x.number.split(".")[0] == sec and x is not c]
            scope_full = scope + " " + " ".join(plain(x.text) for x in sib if re.search(r"for the purposes of|for clarity|does not restrict", plain(x.text), re.I))
            mfn = bool(re.search(r"no less favou?rable|most[- ]favou?red", t, re.I))
            tail = None
            for d in defs + [c]:
                if re.search(r"restricted period|after|following|thereafter", plain(d.text), re.I):
                    tail = months_in(plain(d.text))
                    if tail:
                        break
            if re.search(r"during the term(?! and)", t, re.I) and not re.search(r"restricted period|after|following|thereafter", t, re.I):
                tail = 0
            if doc.atliq_role == "buyer":
                continue  # restrictions on AtliQ's contractors are not AtliQ's commitments
            ctype = "mfn_pricing" if mfn else ("exclusivity" if re.search(r"exclusiv|partner for any|act as", t, re.I) else "non_compete")
            label = {"mfn_pricing": "Most-favoured pricing (MFN)", "exclusivity": "Exclusivity",
                     "non_compete": "Non-compete / restrictive covenant"}[ctype]
            extra = {}
            if mfn:
                extra["rate_card"] = rate_card(doc)
            make(ctype, c, scope_full if not mfn else "", defs, bool(re.search(r"affiliates?", t, re.I)), tail, label, extra)

        for c in doc.clauses:
            t = plain(c.text)
            if re.search(r"(pre-existing|tools|frameworks|libraries)[^.]{0,200}(assign|vest in the client)", t, re.I) and \
                    not re.search(r"retains?", t, re.I) and doc.atliq_role != "buyer":
                assets = named_assets(doc)
                make("ip_assignment", c, "", [], False, None,
                     "IP in pre-existing materials assigned" + (f" (incl. {', '.join(assets)})" if assets else ""),
                     {"named_assets": assets, "end": None, "end_basis": "assignment is permanent", "status": "active"})
            if doc.atliq_role == "buyer" and re.search(r"(contractor|vendor)\s+(shall\s+)?retains?[^.]{0,80}(work product|ownership)", t, re.I):
                make("contractor_ip_retained", c, "", [], False, None, "Contractor retains IP in work product",
                     {"end": None, "end_basis": "ownership is permanent", "status": "active",
                      "tracker_note": tracker_row["notes"] if tracker_row else ""})
    # Fix records where a permanent status was overwritten by make()
    for r in register:
        if r["type"] in ("ip_assignment", "contractor_ip_retained"):
            r["status"], r["end"] = "active", None
    return register


def named_assets(doc: Document) -> list[str]:
    names = set()
    for m in re.finditer(r"proprietary[^.]{0,60}?\*\*([A-Z][A-Za-z0-9]{2,30})\*\*", doc.text):
        names.add(m.group(1))
    return sorted(names)


RATE_ROW_RE = re.compile(r"^\|\s*([A-Za-z][A-Za-z /&()-]{2,60}?)\s*\|\s*(?:USD\s*)?\$?\s*(\d{2,4}(?:\.\d+)?)\s*(?:/\s*hr|per hour)?\s*\|", re.M)


def rate_card(doc: Document) -> list[dict]:
    out = []
    for c in doc.clauses:
        if c.kind != "table":
            continue
        head = (c.heading + " " + c.text.splitlines()[0]).lower()
        if not re.search(r"rate", head):
            continue
        for m in RATE_ROW_RE.finditer(c.text):
            out.append({"role": m.group(1).strip(), "rate": float(m.group(2)), "clause_idx": c.idx, "ref": c.ref,
                        "row": m.group(0).strip()})
    return out


def _norm_role(r: str) -> str:
    r = r.lower()
    r = re.sub(r"\bsr\.?\b", "senior", r)
    r = re.sub(r"[^a-z ]", " ", r)
    return re.sub(r"\s+", " ", r).strip()


def _deal_clauses(doc: Document) -> list[Clause]:
    """Clauses that describe the deal, excluding AtliQ's own address/party block and signature blocks."""
    out = []
    for c in doc.clauses:
        t = c.text.lower()
        if "atliq" in t and re.search(r"registered office|principal (office|place)|cin\b|incorporated under", t):
            continue
        if re.search(r"signature|in witness whereof", c.heading.lower() + " " + t[:60]):
            continue
        if re.search(r"governing law|jurisdiction|dispute", c.heading, re.I):
            continue
        out.append(c)
    return out


def detect_conflicts(doc: Document, register: list[dict], tracker: list[dict], as_of: date,
                     docs_by_id: dict[str, Document]) -> dict:
    """Return {'conflicts': [...], 'considered': [...]} for one contract document."""
    conflicts, considered = [], []
    deal = _deal_clauses(doc)
    deal_text = " ".join(plain(c.text) for c in deal)
    deal_geo = geographies(deal_text)
    deal_sec = sectors(deal_text)
    doc_tracker = next((r for r in tracker if r["contract_id"] in doc.tracker_ids), None)
    doc_start = parse_date(doc.doc_date)

    used: set[int] = set()

    def evidence_lines(pattern: str, limit=3):
        scored = []
        for c in deal:
            n = len(re.findall(pattern, c.text, re.I))
            if n and c.idx not in used:
                scored.append((c.kind not in ("clause", "table"), -n, c.idx, c))
        ev = []
        for *_, c in sorted(scored)[:limit]:
            used.add(c.idx)
            ev.append({"ref": c.ref, "clause_idx": c.idx, "excerpt": c.text if len(c.text) < 900 else c.text[:900] + " …"})
        return ev

    if doc.atliq_role == "letter":
        return {"conflicts": [], "considered": []}
    own = set(cp_tokens(doc.counterparty_name or "")[:1])
    for cm in register:
        if cm["doc_id"] == doc.doc_id or (own and own & set(cp_tokens(cm["counterparty"] or "")[:1])):
            continue  # same counterparty: a related document, not a competing deal
        used.clear()
        status_note = f"{cm['label']} in {cm['filename']} ({cm['clause_ref']}) — status: {cm['status']}" + \
                      (f", until {cm['end']}" if cm["end"] else "")
        if cm["start"] and doc_start and doc.kind == "executed" and doc_start < parse_date(cm["start"]):
            continue
        base = {"commitment_id": cm["id"], "commitment_label": cm["label"], "prior_doc_id": cm["doc_id"],
                "prior_filename": cm["filename"], "prior_ref": cm["clause_ref"], "prior_excerpt": cm["excerpt"],
                "prior_definitions": cm["definitions"], "prior_counterparty": cm["counterparty"],
                "prior_status": cm["status"], "prior_end": cm["end"], "prior_end_basis": cm["end_basis"],
                "prior_evidence_label": cm["evidence_label"], "waivers": cm["waivers"],
                "new_doc_id": doc.doc_id, "new_evidence_label": doc.evidence_label}

        if cm["type"] in ("non_compete", "exclusivity"):
            sec_overlap = [s for s in cm["sectors"] if deal_sec.get(s, 0) >= 2]
            geo_overlap = sorted(set(cm["geographies"]) & deal_geo) if cm["geographies"] else []
            if cm["status"] == "expired":
                if sec_overlap:
                    considered.append({"commitment": status_note, "result": "Expired before the review date — no live conflict",
                                       "matched_sectors": sec_overlap})
                continue
            if not sec_overlap or (cm["geographies"] and not geo_overlap):
                considered.append({"commitment": status_note, "result": "No overlap found",
                                   "detail": f"sector overlap: {sec_overlap or 'none'}; geography overlap: {geo_overlap or 'none'}"})
                continue
            sec_pat = "|".join(SECTORS[s] for s in sec_overlap)
            geo_pat = "|".join(COUNTRY_PATTERNS[g] for g in geo_overlap if g in COUNTRY_PATTERNS)
            covered = []
            for w in cm["waivers"]:
                hit = any(tok in (doc.counterparty_name or "").lower() for p in w["covers"] for tok in cp_tokens(p)[:1])
                covered.append({**w, "covers_this_deal": hit})
            entity_note = ""
            if cm["binds_affiliates"]:
                entity_note = (f" The restriction binds AtliQ's Affiliates; AtliQ Inc is a wholly owned subsidiary of AtliQ Technologies "
                               f"Pvt Ltd (atliq_entities.md), so it applies whichever entity signs (this deal names {doc.atliq_entity or 'an unidentified entity'}).")
            operator = any(re.search(rf"(owns|operates|manages|franchises|develops and offers|offers)[^.]{{0,60}}({SECTORS[s]})", deal_text, re.I) for s in sec_overlap)
            conf = "High" if operator else "Medium"
            conflicts.append({**base,
                "id": "X-" + hashlib.sha1(f"{doc.doc_id}{cm['id']}".encode()).hexdigest()[:8],
                "type": cm["type"], "severity": "Critical" if conf == "High" else "High", "confidence": conf,
                "title": f"Possible conflict with {cm['label'].lower()} — {cm['counterparty']}",
                "matched_sectors": sec_overlap, "matched_geographies": geo_overlap,
                "new_evidence": evidence_lines(f"({sec_pat})") + (evidence_lines(f"({geo_pat})", 2) if geo_pat else []),
                "rationale": (f"The executed {cm['label'].lower()} ({cm['clause_ref']}) restricts work in sector(s) "
                              f"{', '.join(sec_overlap)} in {', '.join(geo_overlap) or 'the restricted territory'} until "
                              f"{cm['end'] or 'an unverified date'}. This draft describes work in the same sector "
                              f"({deal_sec[sec_overlap[0]]} mentions) touching {', '.join(geo_overlap)}." +
                              ("" if operator else " The counterparty is not described as operating in the sector itself; "
                               "whether it falls within the restricted definition needs interpretation.") + entity_note),
                "waiver_assessment": covered,
                "missing_facts": [
                    "Whether the services in this deal fall within the restricted service categories as defined (legal interpretation).",
                    "Whether the counterparty is a restricted business under the prior agreement's definitions.",
                    "Whether any written consent/waiver covers this specific engagement" +
                    (" — the waiver on file is limited to its named engagement." if covered and not any(w["covers_this_deal"] for w in covered) else "."),
                    "Confirmation of the prior agreement's actual term end (source: " + cm["end_basis"] + ").",
                ],
            })
        elif cm["type"] == "mfn_pricing":
            if cm["status"] == "expired" or doc.atliq_role not in ("supplier",):
                considered.append({"commitment": status_note, "result": "Not applicable" if cm["status"] != "expired" else "Expired"})
                continue
            new_rates = rate_card(doc)
            lower = []
            for nr in new_rates:
                for pr in cm.get("rate_card", []):
                    if _norm_role(nr["role"]) == _norm_role(pr["role"]) and nr["rate"] < pr["rate"]:
                        lower.append((nr, pr))
            if not new_rates:
                considered.append({"commitment": status_note, "result": "No rate card in this document — MFN not checkable from the text",
                                   "detail": "Check the commercial proposal / SOW pricing separately."})
                continue
            if not lower:
                considered.append({"commitment": status_note, "result": "No lower rate for a matching role"})
                continue
            conflicts.append({**base,
                "id": "X-" + hashlib.sha1(f"{doc.doc_id}{cm['id']}".encode()).hexdigest()[:8],
                "type": "mfn_pricing", "severity": "High", "confidence": "Medium",
                "title": f"Rates below the most-favoured-customer price promised to {cm['counterparty']}",
                "new_evidence": [{"ref": nr["ref"], "clause_idx": nr["clause_idx"], "excerpt": nr["row"]} for nr, _ in lower],
                "prior_rate_rows": [pr["row"] for _, pr in lower],
                "rationale": "; ".join(f"{nr['role']}: ${nr['rate']:.0f}/hr here vs ${pr['rate']:.0f}/hr under the MFN rate card"
                                       for nr, pr in lower) +
                             f". The MFN binds 'Supplier or its Affiliates' and runs until {cm['end'] or 'an unverified date'}.",
                "context": ([{"source": f"tracker {doc_tracker['contract_id']} notes (unverified)", "text": doc_tracker["notes"]}]
                            if doc_tracker and doc_tracker["notes"] else []),
                "missing_facts": ["Whether the services are 'substantially similar' to the MFN client's services (interpretation).",
                                  "Whether the MFN client's current rates were later amended (no amendment found in the repository).",
                                  "Whether lowering the MFN client's rates is the intended remedy, and its cost."],
            })
        elif cm["type"] == "ip_assignment":
            assets = cm.get("named_assets") or []
            hits = [a for a in assets if re.search(rf"\b{re.escape(a)}\b", doc.text)]
            if not hits:
                considered.append({"commitment": status_note, "result": "No named asset from the prior assignment appears in this document"})
                continue
            warrants = evidence_lines(r"sole owner|warrant", 2)
            conflicts.append({**base,
                "id": "X-" + hashlib.sha1(f"{doc.doc_id}{cm['id']}".encode()).hexdigest()[:8],
                "type": "ip_assignment", "severity": "High", "confidence": "Medium",
                "title": f"{', '.join(hits)}: rights may already be assigned to {cm['counterparty']}",
                "new_evidence": evidence_lines("|".join(map(re.escape, hits)), 2) + warrants,
                "rationale": (f"{cm['filename']} {cm['clause_ref']} assigns IP in pre-existing tools/materials incorporated into its "
                              f"deliverables, and that agreement's SOW used {', '.join(hits)}. This draft relies on AtliQ owning "
                              f"{', '.join(hits)}" + (" and contains an ownership warranty." if warrants else ".")),
                "context": ([{"source": f"tracker {doc_tracker['contract_id']} notes (unverified)", "text": doc_tracker["notes"]}]
                            if doc_tracker and doc_tracker["notes"] else []),
                "missing_facts": [f"Which {', '.join(hits)} components were incorporated in the prior deliverables.",
                                  "Whether the assignment covers the tool itself or only the copies incorporated (legal interpretation).",
                                  "Whether any licence-back from the prior client exists (none found in the repository)."],
            })
    return {"conflicts": conflicts, "considered": considered}


def historical_chain_issues(register: list[dict], tracker: list[dict], docs_by_id: dict[str, Document]) -> list[dict]:
    """Executed-vs-executed issues, e.g. a contractor kept IP in work that AtliQ delivered to a client who owns deliverables."""
    out = []
    for cm in register:
        if cm["type"] != "contractor_ip_retained":
            continue
        note = (cm.get("tracker_note") or "").lower()
        for row in tracker:
            toks = cp_tokens(row["counterparty"])
            if not toks or toks[0] not in note:
                continue
            client_doc = next((d for d in docs_by_id.values() if d.kind == "executed" and row["contract_id"] in d.tracker_ids), None)
            if not client_doc:
                continue
            ip = next((c for c in client_doc.clauses if re.search(r"intellectual property|deliverables", c.heading + c.text, re.I)
                       and re.search(r"(property of|vest in|belong to|own)[^.]{0,30}(the )?(client|company|customer)", plain(c.text), re.I)), None)
            if not ip:
                continue
            out.append({
                "id": "H-" + hashlib.sha1(f"{cm['id']}{client_doc.doc_id}".encode()).hexdigest()[:8],
                "type": "ip_chain_of_title", "severity": "Medium", "confidence": "Low",
                "title": f"Chain-of-title gap: {cm['counterparty'] or 'contractor'} kept IP in work possibly delivered to {client_doc.counterparty_name}",
                "a": {"doc_id": cm["doc_id"], "filename": cm["filename"], "ref": cm["clause_ref"], "excerpt": cm["excerpt"]},
                "b": {"doc_id": client_doc.doc_id, "filename": client_doc.filename, "ref": ip.ref, "excerpt": ip.text},
                "link_evidence": f"Tracker {row['contract_id']} / contractor row note: \"{cm.get('tracker_note')}\" (tracker note, unverified)",
                "missing_facts": ["Which deliverables the contractor actually worked on.",
                                  "Whether the AtliQ licence from the contractor is sufficient for the client's ownership clause."],
            })
    return out
