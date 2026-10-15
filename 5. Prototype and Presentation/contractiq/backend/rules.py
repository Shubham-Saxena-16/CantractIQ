"""Deterministic clause-risk rules (PRD §5: "use deterministic rules for policy decisions").

Every finding carries:
  * fact            — the exact clause excerpt + section/page reference (extracted from the contract)
  * extracted       — values parsed from that excerpt (percentages, days, caps...)
  * interpretation  — why the rule fired (a rule-based reading, labelled as interpretation, not legal advice)
  * recommendation  — what a reviewer might check or ask for
  * checklist       — the matching line of Karandeep's checklist, quoted from the file
  * precedents      — related lines from negotiation notes, labelled unverified / deal-specific

Nothing here invents clause text: excerpts are always the clause text as extracted.
"""
from __future__ import annotations

import hashlib
import re

from .clauses import Clause, plain, section_of
from .corpus import Document

SEV_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}

CATEGORY_LABELS = {
    "liquidated_damages": "Liquidated damages / delay",
    "liability": "Limitation of liability",
    "indemnity": "Indemnity",
    "payment": "Payment terms",
    "termination": "Termination",
    "ip": "Intellectual property / reuse",
    "confidentiality": "Confidentiality / NDA",
    "exclusivity": "Exclusivity / non-compete / MFN",
    "data_security": "Data protection & security",
    "governing_law": "Governing law & jurisdiction",
    "insurance": "Insurance",
    "entity": "Contracting entity & invoicing",
    "companion": "Companion documents",
}

NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
             "ten": 10, "twelve": 12, "fifteen": 15, "eighteen": 18, "twenty": 20, "thirty": 30, "forty-five": 45,
             "sixty": 60, "ninety": 90, "twenty-four": 24, "thirty-six": 36}


def fid(doc_id: str, rule: str, clause: Clause | None, extra: str = "") -> str:
    key = f"{doc_id}|{rule}|{clause.idx if clause else ''}|{extra}"
    return "F-" + hashlib.sha1(key.encode()).hexdigest()[:10]


def days_values(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\(?(\d{1,3})\)?\s*(?:calendar\s+|business\s+|working\s+)?days?\b", text)]


def percents(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)]


def money_values(text: str) -> list[float]:
    out = []
    for m in re.finditer(r"(?:USD|US\$|\$)\s?([\d,]+(?:\.\d+)?)\s*(million|m\b)?", text, re.I):
        v = float(m.group(1).replace(",", ""))
        if m.group(2):
            v *= 1_000_000
        out.append(v)
    return out


class Ctx:
    """Helpers bound to one document."""

    def __init__(self, doc: Document, checklist: dict, precedents: list[dict]):
        self.doc = doc
        self.checklist = checklist
        self.precedents = precedents
        self.sections: dict[str, list[Clause]] = {}
        for c in doc.clauses:
            self.sections.setdefault(section_of(c), []).append(c)
        self.findings: list[dict] = []
        self.atliq = (doc.atliq_term or "AtliQ")
        self.cp = (doc.counterparty_term or "the counterparty")

    def section_text(self, c: Clause) -> str:
        return plain(" ".join(x.text for x in self.sections.get(section_of(c), [c])))

    def add(self, rule: str, category: str, severity: str, title: str, clause: Clause | None,
            interpretation: str, recommendation: str, extracted: dict | None = None, confidence: str = "High",
            perspective: str | None = None, extra_key: str = "", related: list[Clause] | None = None,
            precedent_keys: list[str] | None = None):
        fact = None
        if clause is not None:
            fact = {"clause_idx": clause.idx, "ref": clause.ref, "excerpt": clause.text, "page": clause.page,
                    "line": clause.line, "heading": clause.heading}
        rel = [{"clause_idx": r.idx, "ref": r.ref, "excerpt": r.text} for r in (related or []) if r is not clause]
        self.findings.append({
            "id": fid(self.doc.doc_id, rule, clause, extra_key),
            "doc_id": self.doc.doc_id, "rule": rule, "category": category,
            "category_label": CATEGORY_LABELS.get(category, category), "severity": severity, "title": title,
            "fact": fact, "related_facts": rel, "extracted": extracted or {},
            "interpretation": interpretation, "recommendation": recommendation,
            "checklist": self.checklist.get(category), "precedents": match_precedents(self.precedents, category,
                                                                                    precedent_keys, self.doc),
            "confidence": confidence,
            "perspective": perspective or perspective_label(self.doc),
            "source": "rules", "evidence_label": self.doc.evidence_label,
        })


def perspective_label(doc: Document) -> str:
    return {"supplier": "AtliQ as supplier", "buyer": "AtliQ as buyer (fairness to the other side)",
            "partner": "AtliQ as partner", "nda": "NDA party", "intercompany": "Intercompany",
            "letter": "Letter / consent"}.get(doc.atliq_role, doc.atliq_role)


# ---------------------------------------------------------------- checklist & precedents

CHECKLIST_KEYS = {
    "liquidated_damages": ["lds"], "liability": ["liability"], "indemnity": ["indemnity"], "payment": ["payment"],
    "governing_law": ["gov law"], "ip": ["ip →", "ip ->"], "termination": ["termination"],
    "confidentiality": ["confidentiality", "ndas"],
}


def parse_checklist(doc: Document | None) -> dict:
    out = {}
    if not doc:
        return out
    lines = [l.strip()[1:].strip() for l in doc.text.splitlines() if l.strip().startswith("- ")]
    for cat, keys in CHECKLIST_KEYS.items():
        hits = [l for l in lines if any(l.lower().startswith(k) for k in keys)]
        if hits:
            out[cat] = {"items": hits, "source": doc.filename,
                        "evidence_label": "Company preference — personal checklist last edited March 2024, not formally approved"}
    return out


PRECEDENT_TERMS = {
    "liquidated_damages": r"\bLD\b|delay|liquidated",
    "liability": r"liabilit",
    "indemnity": r"indemn",
    "payment": r"payment|pay-when-paid|\b\d+ ?days?\b|60-day|90 days",
    "termination": r"terminat",
    "ip": r"\bIP\b|licen[cs]e|PipeKit|reuse|Work Product",
    "confidentiality": r"\bNDA\b|one-way|mutual",
    "exclusivity": r"non-compete|exclusiv|no less favorable|Competing Platform|discount",
    "data_security": r"BAA|de-identified|offshore",
    "governing_law": r"\blaw\b|arbitration|courts|LCIA|DIFC|SIAC",
    "insurance": r"insurance|cyber",
}


def match_precedents(entries: list[dict], category: str, keys: list[str] | None, doc: Document) -> list[dict]:
    pat = PRECEDENT_TERMS.get(category)
    if not pat or not entries:
        return []
    out = []
    for e in entries:
        lines = [l for l in e["lines"] if re.search(pat, l, re.I)]
        if keys:
            lines = [l for l in lines if any(re.search(k, l, re.I) for k in keys)] or []
        if not lines:
            continue
        out.append({
            "title": e["title"], "excerpt": " / ".join(lines[:3]), "is_exception": e["is_exception"],
            "outcome": e["outcome"], "source": "negotiation_notes.md",
            "evidence_label": "Negotiation note (Jay's unreviewed reconstruction)" +
                              (" — DEAL-SPECIFIC EXCEPTION, not policy" if e["is_exception"] else ""),
        })
    return out[:4]


# ---------------------------------------------------------------- analyzers

def _heading_is(c: Clause, pat: str) -> bool:
    return bool(re.search(pat, c.heading, re.I))


def analyze_ld(x: Ctx):
    doc = x.doc
    seen_sections = set()
    for c in doc.clauses:
        t = plain(c.text)
        if not re.search(r"liquidated damages|penalt(y|ies) for delay|delay penalt|per (calendar )?(day|week) of delay|"
                         r"for each (complete |calendar )?(day|week)", t, re.I):
            continue
        if not re.search(r"\d+(\.\d+)?\s*%|percent", t, re.I):
            continue
        sec = section_of(c)
        if sec in seen_sections:
            continue
        seen_sections.add(sec)
        stext = x.section_text(c)
        pct = percents(t)
        rate = pct[0] if pct else None
        rm = re.search(r"\d+(?:\.\d+)?\s*%", t)
        rate_seg = t[rm.start(): rm.start() + 160] if rm else t
        per_day = bool(re.search(r"\b(each|per|every)\s+(calendar\s+|business\s+)?day\b|each day|per day", rate_seg, re.I))
        base_total = bool(re.search(r"(total\s+)?contract value|total fees|total contract|fees payable under this agreement|"
                                    r"aggregate fees|total value", rate_seg, re.I)) and not re.search(r"affected milestone|for the affected", rate_seg, re.I)
        base_ms = bool(re.search(r"milestone|affected (deliverable|milestone)|fees? (payable )?for the affected", rate_seg, re.I)) and not base_total
        cap_m = re.search(r"(?:shall not exceed|not exceed|maximum of|up to a maximum of|capped at|cap of|in aggregate exceed)"
                          r"[^.%]{0,80}?(\d+(?:\.\d+)?)\s*%", stext, re.I)
        cap = float(cap_m.group(1)) if cap_m else None
        cap_on_total = bool(cap_m and re.search(r"%\)?\s*(of\s+)?(the\s+)?(total|contract value|total fees|fees payable under this agreement)",
                                                stext[cap_m.start(): cap_m.end() + 80], re.I))
        client_excl = bool(re.search(r"(not|no)[^.]{0,60}(apply|payable|liable)[^.]{0,60}(delay|delays)[^.]{0,40}caused by|"
                                     r"attributable to (the )?(supplier|vendor|service provider|contractor|atliq|developer)|"
                                     r"for reasons attributable to|caused by (the )?(client|company|customer|lakeshore|blueorchid)|"
                                     r"delay caused by the client|to the extent (such )?delay is caused by|other than as a result of any act or omission of (the )?(client|company|customer)", stext, re.I))
        cumulative = bool(re.search(r"in addition to and not in lieu|without prejudice to .{0,40}(other|actual) (rights|damages)", stext, re.I))
        extracted = {"rate_percent": rate, "period": "day" if per_day else "week", "base": "total contract value" if base_total
                     else "milestone fee" if base_ms else "unclear", "cap_percent": cap,
                     "cap_base": "total" if cap_on_total else ("milestone" if cap is not None else None),
                     "client_delay_exclusion": client_excl, "cumulative_with_actual_damages": cumulative}
        problems, sev = [], "Low"
        if cap is None:
            problems.append("no cap on liquidated damages was found in this clause or its sibling sub-clauses")
            sev = "Critical"
        if per_day:
            problems.append(f"the rate accrues per day ({rate}% per day)")
            sev = "Critical" if cap is None or (rate or 0) >= 1 else max_sev(sev, "High")
        if base_total:
            problems.append("it is calculated on the total contract value rather than the affected milestone")
            sev = max_sev(sev, "High")
        if cap is not None and (cap > 5 or cap_on_total):
            problems.append(f"the cap is {cap}% of the {'total contract value' if cap_on_total else 'base'}")
            sev = max_sev(sev, "High" if cap >= 10 or cap_on_total else "Medium")
        if not client_excl:
            problems.append("no exclusion for delay caused by the client was found (the Brightwater dispute turned on this)")
            sev = max_sev(sev, "High")
        if cumulative:
            problems.append("LDs are cumulative with actual damages, so they are not a genuine cap on delay exposure")
            sev = max_sev(sev, "High")
        if doc.atliq_role == "buyer":
            # AtliQ imposes the LD on its vendor: a fairness issue rather than exposure for AtliQ.
            sev = {"Critical": "High", "High": "Medium"}.get(sev, sev)
        if not problems:
            x.add("ld_within_preference", "liquidated_damages", "Low", "Liquidated damages appear capped and scoped",
                  c, f"Rate {rate}% per {extracted['period']} on the {extracted['base']}, cap {cap}%, client-caused delay excluded. "
                     "This resembles the position AtliQ negotiated with Acme, Northwind and Trustline (per negotiation notes).",
                  "No change suggested by the rules; confirm milestone dates are achievable.", extracted, related=x.sections.get(sec),
                  precedent_keys=[r"0\.5%"])
            continue
        x.add("ld_risk", "liquidated_damages", sev, "Liquidated damages: " + problems[0].split(" (")[0], c,
              "Rule reading: " + "; ".join(problems) + ".",
              "Ask for a cap (AtliQ's usual counter in past deals: 0.5% of the affected milestone fee per week, capped at 5% "
              "of that milestone, no LDs for client-caused delay — per negotiation notes, unverified) and an explicit "
              "client-delay exclusion." if doc.atliq_role != "buyer" else
              "AtliQ is the buyer here. Karandeep's note says AtliQ's own paper should not carry terms he would reject from a "
              "client; consider the PixelCraft precedent (penalty deleted).",
              extracted, related=x.sections.get(sec))


def max_sev(a: str, b: str) -> str:
    return a if SEV_ORDER[a] <= SEV_ORDER[b] else b


def analyze_liability(x: Ctx):
    doc = x.doc
    secs = [c for c in doc.clauses if _heading_is(c, r"liabilit") or re.search(r"aggregate liability|limit(s|ation)? (of|or exclude)? ?.{0,20}liability", plain(c.text), re.I)]
    found_cap = False
    for c in secs:
        t = plain(c.text)
        mutual_statutory = re.search(r"(the parties|each party|either party) shall be liable without limitation for damage caused intentionally or by gross negligence", t, re.I)
        if mutual_statutory:
            x.add("liability_statutory_unlimited", "liability", "Medium", "Unlimited liability for intent / gross negligence (both parties)", c,
                  "Both parties are liable without limit for intentional or grossly negligent damage and personal injury. This mirrors "
                  "mandatory rules in some jurisdictions (here, German law) and is narrower than general unlimited liability.",
                  "Ask counsel whether this is mandatory under the governing law; confirm the cap in the following sub-clauses applies otherwise.",
                  {"uncapped_heads": "intent, gross negligence, personal injury, product liability"})
            found_cap = True
            continue
        if re.search(r"nothing in this agreement shall limit( or exclude)?|shall not limit or exclude|without limitation for all|"
                     r"unlimited liability|liable without limit|shall be unlimited|liability .{0,40}shall not be limited", t, re.I):
            who_atliq = re.search(rf"\b({re.escape(x.atliq)}|supplier|contractor|vendor|service provider|developer|partner)('s)?\b", t, re.I)
            sev = "Critical" if who_atliq and doc.atliq_role != "buyer" else "High"
            x.add("liability_unlimited", "liability", sev, "Liability appears uncapped for AtliQ" if doc.atliq_role != "buyer"
                  else "Vendor/contractor liability appears uncapped (AtliQ's own paper)", c,
                  "The clause states that liability is not limited. Kessler Mobility was walked away from over unlimited "
                  "liability (negotiation notes).",
                  "Seek a mutual cap (checklist: 1x fees) with narrow carve-outs." if doc.atliq_role != "buyer" else
                  "Consider capping liability at fees for both sides, as was done for PixelCraft (negotiation notes).",
                  {"uncapped": True}, precedent_keys=[r"unlimited|without limitation|1x|capped"])
            found_cap = True
            continue
        m = re.search(r"(?:aggregate|total)\s+liability[^.]{0,200}?(?:shall not exceed|not exceed|limited to|capped at)([^.]{0,160})", t, re.I)
        if m:
            found_cap = True
            limit_txt = m.group(1)
            one_sided = bool(re.search(rf"\b({re.escape(x.cp)}|client|company|customer)'?s (total )?aggregate liability", t, re.I)) and not re.search(r"each party|either party|neither party", t, re.I)
            mult = re.search(r"(two|three|\d+(?:\.\d+)?)\s*(?:\(\d+\)\s*)?(?:times|x)\b", limit_txt, re.I)
            if one_sided:
                x.add("liability_one_sided_cap", "liability", "High", "Liability cap protects only the counterparty", c,
                      "The cap wording applies to the counterparty's liability; no equivalent cap for AtliQ was found in this clause.",
                      "Ask for a mutual cap.", {"cap_text": limit_txt.strip()})
            elif mult:
                x.add("liability_multiple", "liability", "High", "Liability cap exceeds 1x fees", c,
                      f"Cap expressed as a multiple of fees ('{mult.group(0)}'); checklist preference is 1x fees.",
                      "Negotiate to 1x fees.", {"cap_text": limit_txt.strip()})
            carve = re.search(r"(?:save|except|other than|excluding)\s+(?:in respect of\s+|for\s+)?(?:liability arising from\s+)?([^.]{10,220})", t, re.I)
            if carve and re.search(r"confidential|data|indemn|security|privacy|gross negligence", carve.group(1), re.I) and \
                    re.search(r"data|indemn", carve.group(1), re.I):
                x.add("liability_carveouts", "liability", "Medium", "Uncapped carve-outs from the liability cap", c,
                      f"Carve-outs listed: '{carve.group(1).strip()[:160]}'. Exposure for these heads is not limited by the cap.",
                      "Check whether data-protection or indemnity carve-outs could be sub-capped (e.g. a super-cap).",
                      {"carve_out_text": carve.group(1).strip()})
    subordinate = re.search(r"statement of work|business associate|exhibit", doc.title, re.I)
    if not found_cap and doc.atliq_role in ("supplier", "partner") and not subordinate:
        illegible = any(q["code"] in ("illegible", "little_text") for q in doc.quality)
        x.add("liability_no_cap_found", "liability", "Medium" if not illegible else "Low",
              "No limitation-of-liability cap identified" + (" (extraction incomplete)" if illegible else ""), None,
              "The rules did not find a liability cap in the extracted text. " +
              ("Extraction quality warnings exist for this document, so this is NOT a confirmed absence." if illegible else
               "This may mean liability is uncapped or that the cap sits in a schedule not included in this file."),
              "Read the agreement (and any referenced MSA/schedules) to confirm.", confidence="Low")


def analyze_indemnity(x: Ctx):
    doc = x.doc
    for c in doc.clauses:
        t = plain(c.text)
        if not re.search(r"indemnif", t, re.I):
            continue
        if re.search(r"regardless of whether[^.]{0,80}negligence|including (those|losses|claims) arising from the negligence of|"
                     r"even if caused[^.]{0,40}negligence", t, re.I):
            x.add("indemnity_others_negligence", "indemnity", "Critical" if doc.atliq_role != "buyer" else "High",
                  "Indemnity covers the other party's own negligence", c,
                  "AtliQ would indemnify losses even where caused by the indemnified party's negligence. The checklist says "
                  "'we don't cover their mistakes'; PayTrack's equivalent clause was negotiated to mutual (negotiation notes).",
                  "Limit to losses caused by AtliQ's breach/negligence; make it mutual.", precedent_keys=[r"mutual|negligence"])
            continue
        broad = re.search(r"any and all (losses|claims|liabilities)[^.]{0,120}arising out of or (relating|related) to\s*\(?a?\)?\s*(the services|this agreement|the deliverables)", t, re.I)
        by_atliq = re.search(rf"^\s*(?:\*\*)?[\d.]+(?:\*\*)?\s*(?:\*\*[^*]+\*\*\s*)?({re.escape(x.atliq)}|contractor|supplier|vendor|service provider|partner|business associate)\s+shall\s+(defend,\s*)?indemnif", plain(c.text), re.I)
        if broad and by_atliq:
            x.add("indemnity_broad", "indemnity", "High", "Broad one-way indemnity from AtliQ", c,
                  "AtliQ indemnifies against any losses arising out of the services/agreement, not only third-party IP or its own breach.",
                  "Narrow to third-party claims caused by AtliQ's breach, negligence or IP infringement, and seek a mutual indemnity.")


def analyze_payment(x: Ctx):
    doc = x.doc
    best = None
    for c in doc.clauses:
        t = plain(c.text)
        if re.search(r"pay-when-paid|pay when paid|(after|following|upon|within [^.]{0,30} of) (AtliQ'?s? )?receipt of (corresponding )?payment from (the )?(end )?client|"
                     r"paid by the end client", t, re.I):
            x.add("payment_pay_when_paid", "payment", "High", "Pay-when-paid: payment depends on the end client paying", c,
                  "Payment to the other side is conditional on AtliQ being paid by its client" if doc.atliq_role == "buyer"
                  else "AtliQ's payment depends on a third party paying.",
                  "Kriti has pushed back ('we're 12 people' — tracker note). PixelCraft precedent: 30-day payment for a small agency."
                  if doc.atliq_role == "buyer" else "Seek a fixed payment term independent of third parties.",
                  {"days": max(days_values(t) or [0]) or None}, perspective=perspective_label(doc))
        if re.search(r"set[- ]?off[^.]{0,160}(any other agreement|other agreements)", t, re.I):
            x.add("payment_setoff", "payment", "Medium", "Cross-agreement set-off", c,
                  "The counterparty may set off amounts owed under other agreements against AtliQ's invoices.",
                  "Limit set-off to undisputed amounts under this agreement.")
        if re.search(r"exchange rate determined by the company|at (its|the company's) (sole )?discretion", t, re.I) and \
                re.search(r"pa(id|y)|rate|timesheet", t, re.I) and doc.atliq_role == "buyer":
            x.add("payment_discretion", "payment", "Medium", "Payment amount or approval at AtliQ's sole discretion", c,
                  "A one-sided discretion over approval or currency conversion shifts risk to the contractor.",
                  "Use objective criteria (fixed currency, published reference rate, approval within N days).")
        if re.search(r"deemed waived|shall be waived", t, re.I) and re.search(r"invoice", t, re.I):
            x.add("payment_invoice_waiver", "payment", "Medium", "Late invoices are forfeited", c,
                  "Invoices not submitted within the stated window are deemed waived — an operational deadline for finance.",
                  "Track invoice submission deadlines; seek removal or a longer window.", {"days": max(days_values(t) or [0]) or None})
        for m in re.finditer(r"(?:pay|paid|payable|payment)[^.]{0,140}?(?:within|not later than)\s+(?:[a-z\-]+\s+){0,4}\(?(\d{1,3})\)?\s*(?:calendar\s+)?days|net\s*(\d{2,3})\b", t, re.I):
            seg = m.group(0)
            # skip dispute/notice windows, but not "undisputed invoice within N days" (that IS the payment term)
            if re.search(r"(?<!un)disput(e|es|ing)\b|notify|notice|object|reject|return|delete|correct", seg, re.I):
                continue
            n = int(m.group(1) or m.group(2))
            if best is None or n > best[0]:
                best = (n, c)
    if best:
        n, c = best
        if n > 45 or (n > 30 and doc.atliq_role == "buyer"):
            sev = "High" if n > 45 else "Medium"
            x.add("payment_term_long", "payment", sev, f"Payment term of {n} days", c,
                  f"Checklist preference: 30 days, 45 max. This clause sets {n} days."
                  + (" AtliQ is the payer here; long terms push cash-flow strain onto a smaller vendor." if doc.atliq_role == "buyer" else ""),
                  "Negotiate to 30 days (45 max). Trustline moved from 90 to 45 days (negotiation notes)." if doc.atliq_role != "buyer"
                  else "Consider 30 days, consistent with the PixelCraft precedent.",
                  {"days": n}, precedent_keys=[r"\d+ ?d|days|payment"])
        elif n > 30:
            x.add("payment_term_medium", "payment", "Low", f"Payment term of {n} days (within 45-day maximum)", c,
                  f"{n} days is above the 30-day target but within the 45-day maximum on the checklist.",
                  "Acceptable under the checklist; note for cash-flow planning.", {"days": n})


def analyze_termination(x: Ctx):
    doc = x.doc
    for c in doc.clauses:
        t = plain(c.text)
        if not re.search(r"for convenience|for any reason or no reason|without cause", t, re.I):
            continue
        if not re.search(r"terminat", t, re.I):
            continue
        days = days_values(t)
        notice = min(days) if days else None
        cp_only = not re.search(r"either party|each party|both parties|mutual", t, re.I)
        no_wip = re.search(r"no obligation to pay for work in progress|sole obligation shall be to pay[^.]{0,60}accepted|"
                           r"only for (deliverables|services) (accepted|completed and accepted)", t, re.I)
        accepted_only = re.search(r"performed and accepted|accepted (by [^.]{0,20})?prior to", t, re.I)
        if no_wip:
            x.add("termination_no_wip", "termination", "High", "Termination for convenience without payment for work in progress", c,
                  "On convenience termination only accepted deliverables are paid; work in progress is not. Checklist: 'they pay for work done'.",
                  "Ask for payment for all work performed to the termination date plus non-cancellable costs.",
                  {"notice_days": notice, "counterparty_only": cp_only})
        elif accepted_only and doc.atliq_role != "buyer":
            x.add("termination_accepted_only", "termination", "Medium", "Convenience termination pays only for accepted work", c,
                  "Payment on termination is limited to services 'performed and accepted' — unaccepted work in progress may go unpaid.",
                  "Clarify that work performed to the termination date is paid.", {"notice_days": notice})
        if notice is not None and notice < 30 and cp_only and doc.atliq_role in ("supplier", "partner"):
            x.add("termination_short_notice", "termination", "Medium", f"Counterparty may terminate for convenience on {notice} days' notice", c,
                  "Short one-sided convenience termination limits revenue certainty and staffing planning.",
                  "Seek at least 30 days' notice, mutual rights, or a termination fee.", {"notice_days": notice})


def analyze_ip(x: Ctx):
    doc = x.doc
    for c in doc.clauses:
        t = plain(c.text)
        if re.search(r"(pre-existing|background|supplier materials|tools)[^.]{0,200}(assign|shall vest in the client|vest in the client|property of client)", t, re.I) and \
                not re.search(r"(retains?|shall retain|remain the property of the supplier)", t, re.I):
            x.add("ip_preexisting_assigned", "ip", "High", "AtliQ's pre-existing materials would be assigned to the client", c,
                  "The clause assigns (or vests) rights in pre-existing tools/materials incorporated into deliverables. Checklist: "
                  "'client owns what we build for them, we keep our own stuff'. Reusing those tools for other clients could then be restricted.",
                  "Carve out pre-existing/background IP and grant a licence instead.", precedent_keys=[r"IP|PipeKit|reuse|skimmed"])
        elif re.search(r"works? made for hire", t, re.I) and doc.atliq_role != "buyer":
            x.add("ip_work_for_hire", "ip", "Medium", "Work-made-for-hire ownership from creation", c,
                  "Deliverables belong to the client from creation (not on payment).", "Seek ownership transfer on payment.")
        if doc.atliq_role == "buyer" and re.search(r"(contractor|vendor)\s+(shall\s+)?retains?[^.]{0,80}(work product|deliverables|ownership)", t, re.I):
            x.add("ip_contractor_retains", "ip", "Medium", "Contractor retains IP in work product", c,
                  "If the contractor keeps ownership, AtliQ may be unable to assign that work to its own client (most client MSAs "
                  "give the client ownership of deliverables).", "Check flow-down against the client agreement this work supports.")
        if re.search(r"warrants? that it is the sole owner", t, re.I):
            x.add("ip_sole_owner_warranty", "ip", "Medium", "AtliQ warrants sole ownership of a tool/IP", c,
                  "A sole-ownership warranty is only safe if no prior agreement assigned rights in that tool. See the conflicts tab "
                  "for any prior assignment found in executed contracts.",
                  "Verify chain of title before signing.")
        if re.search(r"irrevocable[^.]{0,60}worldwide[^.]{0,80}(modify|reproduce)", t, re.I) and re.search(r"pipekit|background|pre-existing|supplier tools", t, re.I):
            x.add("ip_broad_background_licence", "ip", "Medium", "Broad licence to AtliQ's background tools", c,
                  "The client gets an irrevocable, worldwide right to modify/reproduce AtliQ background tools beyond the deliverable.",
                  "Limit the licence to use as part of the deliverables for internal purposes.")


def analyze_confidentiality(x: Ctx):
    doc = x.doc
    t_all = plain(doc.text)
    if doc.atliq_role == "nda" or re.search(r"non-?disclosure", doc.title, re.I):
        if re.search(r"\bresiduals?\b", t_all, re.I):
            c = next((c for c in doc.clauses if re.search(r"\bresiduals?\b", c.text, re.I) and re.search(r"use|free", c.text, re.I)), None)
            x.add("nda_residuals", "confidentiality", "High", "Residuals clause", c,
                  "A residuals clause lets information retained in memory be used freely, weakening protection for AtliQ's "
                  "architecture, methods and know-how.", "Delete the residuals clause or limit it narrowly.")
        mutual_title = "mutual" in doc.title.lower()
        ci_def = next((c for c in doc.clauses if re.search(r'confidential information["”]?\*?\*?\s*["”]?\s*means', plain(c.text), re.I)), None)
        one_way = False
        if ci_def is not None:
            d = plain(ci_def.text)
            one_way = bool(re.search(r"disclosed[^.]{0,80}by or on behalf of the (company|discloser|client|disclosing party)\b(?! or)", d, re.I)) \
                      and not re.search(r"either party|a party|each party|disclosing party", d, re.I)
        if one_way or (not mutual_title and x.atliq.lower() in ("recipient", "receiving party")):
            x.add("nda_one_way", "confidentiality", "High" if mutual_title else "Medium",
                  "NDA is titled mutual but protects only one side" if mutual_title else "One-way NDA", ci_def,
                  "Confidential Information is defined as information disclosed by the counterparty only; AtliQ's own information "
                  "(architecture, approach) would not be protected. Checklist: 'NDAs → just sign if mutual'. GlobalMart's one-way "
                  "NDA was converted to mutual (negotiation notes).",
                  "Make the definition and obligations mutual.", precedent_keys=[r"mutual|one-way"])
    for c in doc.clauses:
        t = plain(c.text)
        if re.search(r"confidential", t, re.I) and re.search(r"in perpetuity|perpetual|indefinitely", t, re.I) and \
                not re.search(r"trade secret", t, re.I) and not re.search(r"licen[cs]e", t, re.I):
            x.add("confidentiality_perpetual", "confidentiality", "Low", "Perpetual confidentiality obligation", c,
                  "Obligations never expire.", "Consider a fixed term (e.g. 3-5 years) except for trade secrets.")


EXCL_EXCLUDE = re.compile(r"non-exclusive|exclusive jurisdiction|exclusive of|exclusive remedy|sole and exclusive|"
                          r"exclusive property|exclusive, perpetual|exclusively in the state|exclusively for covered entity|"
                          r"developed exclusively|non-exclusivity", re.I)
RESTRICT_RE = re.compile(
    r"non-?compet|restricted period|exclusivity|exclusively to the company|shall not\b[^.]{0,90}(act as|provide|develop|license|engage|be engaged|"
    r"solicit, market to, or provide|partner with)|no less favou?rable than|most[- ]favou?red", re.I)


def restrictive_clauses(doc: Document) -> list[Clause]:
    out = []
    for c in doc.clauses:
        t = plain(c.text)
        if not RESTRICT_RE.search(t):
            continue
        if EXCL_EXCLUDE.search(t) and not re.search(r"non-?compet|restricted period|no less favou?rable|exclusively to the company", t, re.I):
            continue
        if re.search(r"shall not[^.]{0,40}(solicit|hire)[^.]{0,40}(employ|personnel|staff)", t, re.I) and not re.search(r"account|customer|client", t, re.I):
            continue  # ordinary employee non-solicit
        if re.search(r"subcontractor", t, re.I) and not re.search(r"non-?compet|exclusiv|account", t, re.I):
            continue  # subcontracting controls are handled by the data/companion checks
        if re.search(r"shall not (use|disclose|assign|subcontract|incorporate)", t, re.I) and not RESTRICT_RE.search(t.replace("shall not use", "")):
            continue
        if re.search(r"^(\*\*)?[\d.]+(\*\*)?\s*\"\*?\*?[A-Z][^\"]+\"?\*?\*?\s*(means|has the meaning)", c.text) and not re.search(r"restricted period", t, re.I):
            continue  # pure definition (except the Restricted Period definition itself)
        out.append(c)
    return out


def analyze_exclusivity(x: Ctx):
    doc = x.doc
    for c in restrictive_clauses(doc):
        t = plain(c.text)
        if re.search(r"restricted period[\"”*\s]*means", t, re.I):
            continue
        affiliates = bool(re.search(r"affiliates?", t, re.I))
        bound_atliq = bool(re.search(rf"\b({re.escape(x.atliq)}|supplier|service provider|partner|vendor|contractor|developer|neither party|"
                                     r"neither it nor any of its affiliates|business associate)\b", t, re.I))
        mfn = bool(re.search(r"no less favou?rable|most[- ]favou?red", t, re.I))
        post_term = re.search(r"(\d{1,2})\)?\s*months?\s*(after|following|thereafter)|restricted period|term \+", t, re.I)
        if doc.atliq_role == "buyer":
            sev = "Medium"
            title = "Exclusivity / non-compete imposed on the contractor"
            interp = ("AtliQ's draft restricts the individual/vendor from working for others. Karandeep's note: a freelancer "
                      "should not get AtliQ's paper and feel the way he felt reading Brightwater's.")
            rec = "Limit to conflicts of interest / client non-solicit; check enforceability for the contractor's location with counsel."
        elif mfn:
            sev, title = "High", "Most-favoured pricing commitment (MFN)"
            interp = ("AtliQ promises this counterparty prices no worse than any other customer. Any lower rate offered "
                      "elsewhere (including by Affiliates, if mentioned) may breach it.")
            rec = "Avoid MFN; if accepted, record it in the commitment register and check every new rate card against it."
        else:
            sev = "Critical" if affiliates and post_term else "High"
            title = "Restrictive covenant binding AtliQ" + (" and its Affiliates" if affiliates else "")
            interp = ("This restricts where/for whom AtliQ can work" + (", extends to Affiliates (AtliQ Inc and AtliQ "
                      "Technologies Pvt Ltd are affiliates)" if affiliates else "") + (", and continues after the agreement ends." if post_term else "."))
            rec = ("Narrow by geography, service category and duration (Al Noor precedent: worldwide/3 years narrowed to GCC "
                   "+18 months; CloudSpan: Europe removed). Check it against existing commitments.")
        if not bound_atliq and doc.atliq_role != "buyer":
            sev, title = "Low", "Restrictive clause (party bound unclear)"
            interp = "A restrictive clause was detected but the rules could not determine which party is bound."
            rec = "Read the clause to confirm who is restricted."
        x.add("restrictive_covenant", "exclusivity", sev, title, c, interp, rec,
              {"binds_affiliates": affiliates, "mfn": mfn, "post_term": bool(post_term)},
              precedent_keys=[r"non-compete|exclusiv|no less|GCC|Europe|discount"])


def analyze_data(x: Ctx):
    doc = x.doc
    for c in doc.clauses:
        t = plain(c.text)
        m = re.search(r"within\s+(?:[a-z\-]+\s+)?\(?(\d{1,3})\)?\s*hours", t, re.I)
        if m and re.search(r"breach|incident|security|unauthori[sz]ed", t, re.I) and re.search(r"notif", t, re.I):
            h = int(m.group(1))
            if h <= 24:
                x.add("data_breach_window", "data_security", "Medium", f"{h}-hour security-incident notification", c,
                      "A short notification window requires an incident process that can meet it (including for suspected incidents).",
                      "Confirm AtliQ can meet it; consider 'confirmed' incidents and 48-72 hours.", {"hours": h})
        if re.search(r"bear all costs|at (its|contractor's|supplier's) (own )?(sole )?(cost|expense)[^.]{0,80}(notification|credit monitoring|remediation)", t, re.I):
            x.add("data_breach_costs", "data_security", "High", "AtliQ bears all costs of a security incident", c,
                  "Investigation, notification, credit monitoring and remediation costs fall on AtliQ without a stated limit.",
                  "Tie cost recovery to AtliQ's fault and sub-cap it; check cyber insurance limits.")
        if re.search(r"outside (the united states|the kingdom|the uae|india|the eea)|offshore|hosted within|not (be )?transfer[^.]{0,40}outside", t, re.I) \
                and re.search(r"phi|personal data|guest data|data", t, re.I):
            us_health = re.search(r"\bPHI\b|protected health", doc.text)
            sev = "High" if us_health else "Medium"
            x.add("data_localisation", "data_security", sev, "Data location / offshore-access restriction", c,
                  "AtliQ's delivery teams for both entities sit in Pune (atliq_entities.md). Offshore access to this data is "
                  "restricted, so staffing and environments must comply." + (" For PHI, offshore personnel may only touch "
                  "de-identified data where the clause allows it." if us_health else ""),
                  "Confirm the delivery model (who accesses what, from where) before signing; check companion BAA/DPA terms.")
        if re.search(r"subcontractor", t, re.I) and re.search(r"located in the united states|organi[sz]ed under the laws of a state", t, re.I):
            x.add("data_subcontractor_location", "data_security", "High", "Subcontractors must be US-organised with US-located personnel", c,
                  "Any subcontractor (including AtliQ Technologies Pvt Ltd under an intercompany arrangement, or a freelancer) "
                  "must be US-organised and staffed in the US. AtliQ's delivery teams sit in Pune (atliq_entities.md).",
                  "Confirm the staffing plan and every subcontractor before signing; obtain prior written approval as required.")
        if re.search(r"train|tune|evaluate[^.]{0,30}(machine learning|artificial intelligence|model)", t, re.I) and re.search(r"shall not", t, re.I):
            x.add("data_ai_training", "data_security", "Low", "Restriction on using data to train AI models", c,
                  "Data (or derived data) may not be used to train models beyond this client's work.",
                  "Communicate to the delivery team; check reuse of models/accelerators.")


def analyze_insurance(x: Ctx, known_coverage: dict):
    doc = x.doc
    for c in doc.clauses:
        t = plain(c.text)
        if not re.search(r"insurance|liability of \$|errors and omissions", t, re.I):
            continue
        m = re.search(r"cyber[^.;]{0,60}?(\$\s?[\d,]+(?:\.\d+)?\s*(?:million|m\b)?)", t, re.I)
        if m:
            req = money_values(m.group(1))
            req_v = req[0] if req else None
            have = known_coverage.get("cyber")
            if req_v and have and req_v > have["amount"]:
                x.add("insurance_cyber_gap", "insurance", "High", f"Cyber insurance required: ${req_v:,.0f} (AtliQ reportedly has ${have['amount']:,.0f})", c,
                      f"Required cyber cover exceeds the amount Karandeep mentioned ('{have['quote']}' — {have['source']}, "
                      "a meeting note, unverified against the policy).",
                      "Confirm the actual policy limit with the broker; negotiate the requirement or budget for higher cover.",
                      {"required": req_v, "reported_current": have["amount"]})
            elif req_v and req_v >= 2_000_000:
                x.add("insurance_cyber_req", "insurance", "Medium", f"Cyber insurance requirement ${req_v:,.0f}", c,
                      "AtliQ's actual cover is not recorded in the dataset.", "Confirm cover with the broker.", {"required": req_v})


def known_coverage_from_notes(notes: list[Document]) -> dict:
    """Pull insurance figures stated in meeting notes (evidence: meeting note, unverified)."""
    out = {}
    for d in notes:
        for line in d.text.splitlines():
            m = re.search(r"cyber (?:policy|insurance|cover)[^$]{0,20}\$\s?(\d+(?:\.\d+)?)\s*(m|million|k)?", line, re.I)
            if m:
                v = float(m.group(1)) * (1_000_000 if (m.group(2) or "").lower() in ("m", "million") else 1_000 if (m.group(2) or "").lower() == "k" else 1)
                out["cyber"] = {"amount": v, "quote": line.strip().lstrip("- ").strip()[:140], "source": d.filename}
    return out


def run_rules(doc: Document, checklist: dict, precedents: list[dict], known_coverage: dict) -> list[dict]:
    if not doc.is_contract:
        return []
    x = Ctx(doc, checklist, precedents)
    analyze_ld(x)
    analyze_liability(x)
    analyze_indemnity(x)
    analyze_payment(x)
    analyze_termination(x)
    analyze_ip(x)
    analyze_confidentiality(x)
    analyze_exclusivity(x)
    analyze_data(x)
    analyze_insurance(x, known_coverage)
    # de-duplicate identical ids (same rule, same clause)
    seen, out = set(), []
    for f in x.findings:
        if f["id"] in seen:
            continue
        seen.add(f["id"])
        out.append(f)
    out.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["fact"]["clause_idx"] if f["fact"] else 9999))
    return out
