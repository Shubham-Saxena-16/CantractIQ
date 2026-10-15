"""Structured validation checks (PRD FR-7, FR-8, FR-13):

* entity_checks      — contracting entity vs client geography, invoicing entity, currency, governing law
* companion_checks   — NDA / BAA / DPA / flow-down documents: present, draft-only, unverified or missing
* tracker_quality    — duplicates, blanks, stale statuses, missing files, tracker vs contract mismatches

Rules come from atliq_entities.md (finance fact sheet) and the checklist; each result quotes its basis.
"""
from __future__ import annotations

import re
from datetime import date

from .clauses import plain
from .corpus import Document, cp_tokens, parse_date
from .commitments import COUNTRY_PATTERNS, geographies

US_STATES = (r"alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|"
             r"indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|"
             r"montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|"
             r"oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|"
             r"west virginia|wisconsin|wyoming")


def governing_law(doc: Document) -> tuple[str | None, object]:
    for c in doc.clauses:
        t = plain(c.text)
        m = re.search(r"governed by[^.]{0,60}?(?:the )?laws?(?: and regulations in force)?(?: of| in)\s+(?:the\s+)?([A-Z][\w .,'()-]{2,80}?)(?:[,.;]|\s+without|\s+and\b|$)", t)
        if m:
            return m.group(1).strip(), c
        m = re.search(r"(german|english|indian|singapore) law (shall )?(govern|applies)|laws of the federal republic of germany", t, re.I)
        if m:
            return m.group(0), c
    return None, None


def law_country(law: str | None) -> str | None:
    if not law:
        return None
    l = law.lower()
    if re.search(US_STATES + r"|united states", l):
        return "USA"
    if "india" in l:
        return "India"
    if re.search(r"england|english|wales|united kingdom", l):
        return "UK"
    if re.search(r"dubai|difc|emirates|uae", l):
        return "UAE"
    if "saudi" in l or "kingdom" in l:
        return "Saudi Arabia"
    if "german" in l:
        return "Germany"
    if "singapore" in l:
        return "Singapore"
    return law


def forum(doc: Document):
    for c in doc.clauses:
        t = plain(c.text)
        if re.search(r"arbitrat|courts?|jurisdiction|venue", t, re.I) and re.search(r"dispute|action|jurisdiction|seat", t, re.I) \
                and re.search(r"governing law|dispute|jurisdiction|venue", c.heading + t[:80], re.I):
            m = re.search(r"(singapore international arbitration centre|siac|lcia|london court|difc|dubai courts|onshore dubai|riyadh|"
                          r"harris county|travis county|san francisco|munich|mumbai|pune|bengaluru|new delhi|chennai|london|franklin county|"
                          r"courts of [A-Z][\w ]+|seat of arbitration[^.]{0,30})", t, re.I)
            if m:
                return m.group(0), c
    return None, None


def entity_basis(entities_doc: Document | None) -> list[str]:
    if not entities_doc:
        return []
    return [plain(l) for l in entities_doc.text.splitlines() if re.search(r"\| Serves \||Invoicing currenc|Mismatches between", l)]


def client_country(doc: Document, tracker_row: dict | None) -> tuple[str | None, str]:
    if tracker_row and tracker_row["client_country"] and "?" not in tracker_row["client_country"]:
        return tracker_row["client_country"].replace("USA", "USA"), f"tracker {tracker_row['contract_id']} client_country"
    # fall back to the counterparty's address in the party block
    win = doc.text[:2500]
    if doc.counterparty_name:
        i = win.find(doc.counterparty_name.split(",")[0][:15])
        if i >= 0:
            seg = win[i:i + 500].lower()
            for c, p in COUNTRY_PATTERNS.items():
                if re.search(p, seg):
                    return c, "counterparty address in the contract" + (" (tracker value was uncertain)" if tracker_row and "?" in tracker_row["client_country"] else "")
    return (tracker_row["client_country"] if tracker_row else None) or None, "not determined"


def norm_country(c: str | None) -> str | None:
    if not c:
        return None
    c = c.strip().rstrip("?")
    return {"US": "USA", "United States": "USA", "United Arab Emirates": "UAE", "Saudi": "Saudi Arabia", "Saudi Arabia": "Saudi Arabia"}.get(c, c)


def entity_checks(doc: Document, tracker_row: dict | None, entities_doc: Document | None) -> list[dict]:
    if not doc.is_contract or doc.atliq_role in ("letter",):
        return []
    rows = []
    basis = entity_basis(entities_doc)
    country, csrc = client_country(doc, tracker_row)
    country = norm_country(country)
    ent = doc.atliq_entity
    party_clause = next((c for c in doc.clauses if "atliq" in c.text.lower() and re.search(r"incorporated|delaware|cin|corporation|private limited|pvt ltd", plain(c.text), re.I)), None)

    def row(check, status, value, expected, sev, note, clause=None, source=None):
        rows.append({"check": check, "status": status, "value": value, "expected": expected, "severity": sev, "note": note,
                     "fact": {"ref": clause.ref, "excerpt": clause.text, "clause_idx": clause.idx} if clause else None,
                     "source": source})

    # 1. contracting entity vs geography
    if doc.atliq_role == "intercompany":
        row("Contracting entity", "info", ent, "Intercompany", "Info", "Intercompany agreement between AtliQ entities.", party_clause)
    elif not ent:
        row("Contracting entity", "missing", None, None, "Medium", "No AtliQ entity could be identified in the party block — unverified.", None)
    elif not country:
        row("Contracting entity", "unverified", ent, None, "Low", "Client/counterparty country unknown; cannot apply the entity rule.", party_clause)
    else:
        expected = "AtliQ Inc" if country == "USA" else "AtliQ Technologies Pvt Ltd"
        if doc.atliq_role == "partner":
            row("Contracting entity", "review", ent, expected, "Low",
                f"Partner agreement with a {country} company. The finance rule maps *client* geography to entity; for partnerships the "
                "territory served matters more — confirm with finance.", party_clause, csrc)
        elif ent == expected:
            row("Contracting entity", "ok", ent, expected, "Info", f"{country} counterparty ({csrc}) → {expected}.", party_clause, csrc)
        else:
            sev = "High"
            note = (f"{country} counterparty ({csrc}) but the contract names {ent}. Finance: AtliQ Inc serves US clients only; "
                    "AtliQ Technologies Pvt Ltd serves all other regions. Entity mismatches caused payment delays twice in 2025.")
            if doc.atliq_role == "buyer":
                note = (f"Contractor located in {country} ({csrc}) engaged by {ent}. Check which entity should engage them, the tax "
                        "treatment (e.g. TDS/GST vs US forms), currency and governing law — the tracker notes may say the template was reused.")
            row("Contracting entity", "mismatch", ent, expected, sev, note, party_clause, csrc)

    # 2. invoicing entity named elsewhere
    for c in doc.clauses:
        t = plain(c.text)
        if re.search(r"invoice", t, re.I):
            from .corpus import entity_in
            inv = entity_in(t)
            if inv and ent and inv != ent and inv != "Both entities named":
                row("Invoicing entity", "mismatch", inv, ent, "High",
                    f"Invoices are to be raised by {inv}, but the contracting party is {ent}. The entity named in the contract "
                    "determines invoicing, tax regime and bank account (finance fact sheet).", c)
                break

    # 3. currency
    pay_text = " ".join(plain(c.text) for c in doc.clauses if re.search(r"fee|payment|invoice|remuneration|rate", c.heading + c.text[:80], re.I))
    curr = sorted({k for k, p in {"USD": r"USD|US\$|\$\d|United States Dollars", "EUR": r"EUR|€|euro", "INR": r"INR|₹|Indian Rupees|rupees"}.items()
                   if re.search(p, pay_text)})
    if curr:
        allowed = {"AtliQ Inc": {"USD"}, "AtliQ Technologies Pvt Ltd": {"INR", "USD", "EUR"}}.get(ent or "", None)
        bad = [c for c in curr if allowed is not None and c not in allowed]
        if bad:
            row("Currency", "mismatch", ", ".join(curr), ", ".join(sorted(allowed)), "Medium",
                f"{ent} invoices in {', '.join(sorted(allowed))} (finance fact sheet); contract uses {', '.join(bad)}.")
        elif len(curr) > 1:
            row("Currency", "review", ", ".join(curr), None, "Low", "More than one currency appears in payment terms — check which applies.")
        else:
            row("Currency", "ok", curr[0], None, "Info", "Within the entity's invoicing currencies.")

    # 4. governing law vs entity (checklist: "gov law → ours (India for Pvt Ltd, US for Inc)")
    law, lc = governing_law(doc)
    lcountry = law_country(law)
    fr, fc = forum(doc)
    if not law and re.search(r"statement of work|business associate|exhibit", doc.title, re.I):
        row("Governing law", "info", None, None, "Info", "Subordinate document — governing law is normally set by the main agreement it references.")
    elif not law:
        illeg = any(q["code"] == "illegible" for q in doc.quality)
        row("Governing law", "missing" if not illeg else "unverified", None, None, "Low",
            "No governing-law clause found in the extracted text" + (" (extraction has illegible spans)." if illeg else "."))
    else:
        exp = "USA" if ent == "AtliQ Inc" else "India" if ent == "AtliQ Technologies Pvt Ltd" else None
        if exp and lcountry != exp:
            row("Governing law", "deviation", law, f"{exp} law (checklist)", "Medium",
                f"Checklist preference is {'US' if exp == 'USA' else 'Indian'} law for {ent}. Foreign law may require local counsel "
                "for any dispute (Brightwater: English law dispute, $14.2k counsel fees).", lc, "karandeep_contract_checklist.md")
        else:
            row("Governing law", "ok", law, f"{exp} law" if exp else None, "Info", "Consistent with checklist preference.", lc)
    if fr:
        lf = fr.lower()
        far = (lcountry == "USA" and re.search(r"singapore|siac|lcia|london", lf)) or \
              (lcountry and lcountry != "Singapore" and re.search(r"singapore|siac", lf) and lcountry != "Singapore")
        row("Dispute forum", "review" if far else "ok", fr, None, "Medium" if far else "Info",
            ("Forum is in a different country from the governing law — disputes would be run in a third jurisdiction." if far
             else "Forum identified."), fc)
    lang = next((c for c in doc.clauses if re.search(r"(arabic|german) (text|version) shall prevail", plain(c.text), re.I)), None)
    if lang:
        row("Language of record", "review", "Non-English text prevails", "English", "Medium",
            "A non-English version prevails over the English text AtliQ reviewed; the reviewed text may not be the binding one.", lang)
    return rows


# ---------------------------------------------------------------- companion documents

def _status_for(cp_name: str, kind_pat: str, docs: list[Document], tracker: list[dict], this_doc: Document) -> dict:
    toks = cp_tokens(cp_name)[:1]
    found_exec = [d for d in docs if d.kind == "executed" and d is not this_doc and toks and toks[0] in (d.filename + " " + (d.counterparty_name or "")).lower()
                  and re.search(kind_pat, d.title + " " + d.filename, re.I)]
    if found_exec:
        d = found_exec[0]
        return {"status": "present", "label": "Present — executed copy in repository", "evidence": d.filename, "evidence_label": d.evidence_label}
    rows = [r for r in tracker if toks and toks[0] in r["counterparty"].lower() and re.search(kind_pat, r["doc_type"], re.I)]
    signed_rows = [r for r in rows if r["status"].lower() == "signed"]
    drafts = [d for d in docs if d.kind in ("draft", "uploaded") and d is not this_doc and toks and toks[0] in d.filename.lower()
              and re.search(kind_pat, d.title + " " + d.filename, re.I)]
    if signed_rows:
        r = signed_rows[0]
        return {"status": "unverified", "label": "Unverified — tracker says Signed, but no executed copy is in the repository",
                "evidence": f"tracker {r['contract_id']} ({r['doc_type']}, signed {r['signed_date'] or '?'}, file: {r['file_location'] or 'not recorded'})",
                "evidence_label": "Tracker row (not proof of execution)"}
    if drafts:
        return {"status": "draft", "label": "Draft only — not executed", "evidence": drafts[0].filename, "evidence_label": drafts[0].evidence_label}
    if rows:
        r = rows[0]
        return {"status": "unverified", "label": f"Unverified — tracker row {r['contract_id']} status '{r['status'] or 'blank'}'",
                "evidence": f"tracker {r['contract_id']}", "evidence_label": "Tracker row (not proof of execution)"}
    return {"status": "missing", "label": "Missing — no document or tracker row found", "evidence": None, "evidence_label": None}


def companion_checks(doc: Document, docs: list[Document], tracker: list[dict]) -> list[dict]:
    if doc.kind not in ("draft", "uploaded", "executed") or doc.atliq_role in ("letter", "intercompany", "nda"):
        return []
    out = []
    text = doc.text
    cp = doc.counterparty_name or doc.counterparty_term or ""
    tracker_row = next((r for r in tracker if r["contract_id"] in doc.tracker_ids), None)
    country = norm_country(tracker_row["client_country"]) if tracker_row else None
    is_baa = re.search(r"business associate", doc.title, re.I)
    health = re.search(r"\bPHI\b|HIPAA|protected health information", text)
    eu_personal = (country in ("Germany", "France", "Netherlands", "UK") or re.search(r"GDPR|DSGVO", text)) and re.search(r"personal data", text, re.I)
    is_client = doc.atliq_role == "supplier"

    def add(req, why, status, basis_clause=None):
        out.append({"document": req, "why": why, **status,
                    "basis": {"ref": basis_clause.ref, "excerpt": basis_clause.text} if basis_clause else None})

    if is_client and not is_baa and doc.kind != "executed":
        add("NDA with " + (cp or "counterparty"), "Usually signed before data or architecture is exchanged (recommended, not mandatory).",
            _status_for(cp, r"\bNDA\b|non-?disclosure", docs, tracker, doc))
    if health and not is_baa and doc.atliq_role != "buyer":
        c = next((c for c in doc.clauses if re.search(r"\bBAA\b|business associate", plain(c.text), re.I)), None)
        add("HIPAA Business Associate Agreement", "The contract involves PHI / HIPAA.", _status_for(cp, r"\bBAA\b|business associate", docs, tracker, doc), c)
    if health and doc.atliq_role != "buyer":
        offshore = next((c for c in doc.clauses if re.search(r"outside the united states", plain(c.text), re.I)), None)
        sub_us = next((c for c in doc.clauses if re.search(r"subcontractor", plain(c.text), re.I) and re.search(r"located in the united states", plain(c.text), re.I)), None)
        inter = next((d for d in docs if d.kind == "executed" and d.atliq_role == "intercompany"), None)
        if offshore or sub_us:
            if inter:
                covers = cp_tokens(cp)[:1] and cp_tokens(cp)[0] in inter.text.lower()
                sched = next((c for c in inter.clauses if re.search(r"schedule|engagement", c.heading, re.I)), None)
                st = {"status": "present" if covers else "unverified",
                      "label": "Present — covers this engagement" if covers else
                               f"Unverified — intercompany BAA exists ({inter.filename}) but its engagement schedule does not name {cp}",
                      "evidence": inter.filename, "evidence_label": inter.evidence_label}
                if sub_us and not covers:
                    st["label"] += ". This client's terms also require subcontractors to be US-organised with US-located personnel, which AtliQ Technologies Pvt Ltd is not."
                add("Subcontractor BAA (AtliQ Inc ↔ AtliQ Technologies Pvt Ltd)", "PHI access is restricted offshore and delivery teams are in Pune.",
                    st, sched or (sub_us or offshore))
        # flow-down to contractors brought in for this client
        toks = cp_tokens(cp)[:1]
        for r in tracker:
            # only rows whose note says the contractor is brought in *for* this client (not merely mentioning it)
            if toks and re.search(rf"\b(for|on|to work on|staffed on)\s+{re.escape(toks[0])}\b", r["notes"], re.I) \
                    and re.search(r"contractor|subcontractor|vendor", r["doc_type"], re.I):
                cdoc = next((d for d in docs if r["contract_id"] in d.tracker_ids), None)
                has_baa_terms = bool(cdoc and re.search(r"business associate|HIPAA|\bPHI\b", cdoc.text))
                add(f"Business-associate flow-down for {r['counterparty']} ({r['contract_id']})",
                    f"Tracker note links this {r['doc_type'].lower()} to {cp}: \"{r['notes']}\"",
                    {"status": "present" if has_baa_terms else "missing",
                     "label": "Contractor agreement contains BAA/HIPAA terms" if has_baa_terms else
                              "Missing — the contractor agreement has no BAA/HIPAA terms and no separate subcontractor BAA was found",
                     "evidence": cdoc.filename if cdoc else f"tracker {r['contract_id']}",
                     "evidence_label": cdoc.evidence_label if cdoc else "Tracker row"})
    if eu_personal:
        c = next((c for c in doc.clauses if re.search(r"art\.? ?28|data processing agreement|\bDPA\b|order processing", plain(c.text), re.I)), None)
        add("GDPR data processing agreement (DPA)", "Personal data of EU/UK data subjects may be processed.",
            _status_for(cp, r"\bDPA\b|data processing", docs, tracker, doc) if not c else
            {"status": "referenced", "label": "Referenced in the contract — confirm it is attached and executed", "evidence": c.ref,
             "evidence_label": doc.evidence_label}, c)
    if is_baa and doc.kind != "executed":
        main = next((d for d in docs if d is not doc and d.kind in ("draft", "executed") and cp_tokens(cp)[:1]
                     and cp_tokens(cp)[0] in d.filename.lower() and re.search(r"services|msa|master", d.title, re.I)), None)
        add("Main services agreement", "A BAA is an exhibit to the services agreement and should be signed together with it.",
            {"status": "draft" if main and main.kind == "draft" else "present" if main else "missing",
             "label": ("Draft only — " + main.filename) if main and main.kind == "draft" else ("Present — " + main.filename) if main else "Missing",
             "evidence": main.filename if main else None, "evidence_label": main.evidence_label if main else None})
    return out


# ---------------------------------------------------------------- tracker data quality

def tracker_quality(tracker: list[dict], docs: list[Document], register: list[dict], as_of: date) -> list[dict]:
    issues = []
    linked = {}
    for d in docs:
        for t in d.tracker_ids:
            linked.setdefault(t, []).append(d)

    def add(cid, code, sev, msg):
        issues.append({"contract_id": cid, "code": code, "severity": sev, "message": msg})

    seen = {}
    for r in tracker:
        key = (r["counterparty"].lower(), r["doc_type"].lower(), r["signed_date"])
        if key in seen and r["signed_date"]:
            add(r["contract_id"], "duplicate", "Medium",
                f"Possible duplicate of {seen[key]} (same counterparty, document type and signed date). Confirm which row is authoritative.")
            add(seen[key], "duplicate", "Medium", f"Possible duplicate: {r['contract_id']} has the same counterparty, type and signed date.")
        seen.setdefault(key, r["contract_id"])
        if not r["status"]:
            add(r["contract_id"], "blank_status", "Medium", "Status is blank." + (" A draft exists in incoming/ — likely under review." if any(d.kind == "draft" for d in linked.get(r["contract_id"], [])) else ""))
        if not r["atliq_entity"]:
            add(r["contract_id"], "blank_entity", "Low", "AtliQ entity is blank.")
        if "?" in r["client_country"] or not r["client_country"]:
            add(r["contract_id"], "uncertain_country", "Low", f"Client country is '{r['client_country'] or 'blank'}'.")
        if r["status"].lower() == "signed" and not r["file_location"]:
            add(r["contract_id"], "no_file_location", "Low", "Signed, but no file location recorded.")
        if r["atliq_entity"] and r["client_country"] and "intercompany" not in r["counterparty"].lower() \
                and r["doc_type"].lower() not in ("partnership agreement",):
            us = norm_country(r["client_country"]) == "USA"
            if (us and r["atliq_entity"] == "Pvt Ltd") or (not us and r["atliq_entity"] == "Inc"):
                add(r["contract_id"], "entity_geo_mismatch", "High",
                    f"Tracker entity '{r['atliq_entity']}' does not match client country '{r['client_country']}' under the finance entity rule.")
        exp = parse_date(r["expiry_date"])
        if r["status"].lower() == "signed" and exp and exp < as_of:
            add(r["contract_id"], "expired", "Low", f"Expired {exp.isoformat()} but status still 'Signed' — renewal or close-out not recorded.")
        if r["status"].lower() == "signed" and r["contract_id"] not in linked:
            embedded = None
            if r["doc_type"].upper().startswith("SOW"):
                embedded = next((d for d in docs if d.kind == "executed" and cp_tokens(r["counterparty"])[:1]
                                 and cp_tokens(r["counterparty"])[0] in d.filename and re.search(r"statement of work", plain(d.text), re.I)), None)
            add(r["contract_id"], "executed_copy_missing", "Medium" if (r["value_usd_num"] or 0) >= 25000 else "Low",
                "Tracker says Signed, but no executed copy is in the repository." +
                (f" Possibly embedded in {embedded.filename} (unverified)." if embedded else ""))
        regs = [c for c in register if c["tracker_id"] == r["contract_id"] and c["type"] in ("non_compete", "exclusivity", "mfn_pricing", "ip_assignment")]
        if regs and (not r["restrictive_clauses"] or r["restrictive_clauses"].lower() == "none"):
            add(r["contract_id"], "restrictions_understated", "High",
                f"restrictive_clauses is '{r['restrictive_clauses'] or 'blank'}', but the executed contract contains: "
                + "; ".join(f"{c['label']} ({c['clause_ref'].split(' (')[0]})" for c in regs) + ".")
        for d in linked.get(r["contract_id"], []):
            ent_map = {"AtliQ Inc": "Inc", "AtliQ Technologies Pvt Ltd": "Pvt Ltd"}
            if d.atliq_entity in ent_map and r["atliq_entity"] and ent_map[d.atliq_entity] != r["atliq_entity"]:
                add(r["contract_id"], "tracker_vs_contract_entity", "High",
                    f"Tracker entity '{r['atliq_entity']}' but {d.filename} names {d.atliq_entity}.")
    for d in docs:
        if d.is_contract and not d.tracker_ids:
            issues.append({"contract_id": None, "doc_id": d.doc_id, "code": "untracked_document", "severity": "Medium",
                           "message": f"{d.filename} has no confident tracker match. {d.tracker_match_basis}"})
    return issues
