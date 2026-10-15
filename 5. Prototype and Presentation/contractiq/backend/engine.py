"""Builds and holds the analysed state of the repository; the API layer only reads from here."""
from __future__ import annotations

import hashlib
import os
import re
import threading
from datetime import timedelta

from . import db, llm
from .checks import companion_checks, entity_checks, tracker_quality
from .clauses import plain, split_clauses
from .commitments import build_register, detect_conflicts, historical_chain_issues
from .config import AS_OF, CHECKLIST_VERSION, DATASET_DIR, EXPIRY_WINDOW_DAYS
from .corpus import (Document, link_documents, load_corpus, load_tracker, parse_date, parse_negotiation_entries,
                     quality_warnings, detect_parties)
from .obligations import extract_obligations, restriction_obligations
from .rules import CATEGORY_LABELS, SEV_ORDER, known_coverage_from_notes, parse_checklist, run_rules
from .search import Index

DISPOSITIONS = ["relevant", "not_relevant", "resolved", "needs_info", "escalate_counsel"]
SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]


class Engine:
    def __init__(self):
        self.lock = threading.RLock()
        self.build()

    # ------------------------------------------------------------ build
    def build(self):
        with self.lock:
            self.tracker = load_tracker()
            db.import_tracker(self.tracker)
            self.tracker_by_id = {r["contract_id"]: r for r in self.tracker}
            docs = load_corpus()
            for up in db.list_uploads():
                docs.append(self._upload_doc(up))
            link_documents(docs, self.tracker)
            self.docs = docs
            self.by_id = {d.doc_id: d for d in docs}
            checklist_doc = next((d for d in docs if d.kind == "checklist"), None)
            self.checklist = parse_checklist(checklist_doc)
            neg = next((d for d in docs if d.kind == "negotiation_note"), None)
            self.precedents = parse_negotiation_entries(neg) if neg else []
            self.coverage = known_coverage_from_notes([d for d in docs if d.kind == "meeting_note"])
            self.entities_doc = next((d for d in docs if d.kind == "company_reference"), None)
            self.register = build_register(docs, self.tracker, AS_OF)
            self.history_issues = historical_chain_issues(self.register, self.tracker, self.by_id)
            self.analysis: dict[str, dict] = {}
            all_findings = []
            for d in docs:
                if d.is_contract:
                    a = self._analyse(d)
                    self.analysis[d.doc_id] = a
                    all_findings.extend(a["findings"])
            db.upsert_findings(all_findings)
            self.dq = tracker_quality(self.tracker, docs, self.register, AS_OF)
            self.obligations = self._obligations()
            self._build_index()

    def _upload_doc(self, up: dict) -> Document:
        ctx = up["context"]
        d = Document(doc_id=up["doc_id"], path=up["stored_path"], filename=up["filename"], kind="uploaded",
                     title=ctx.get("title") or up["filename"], text=up["markdown"],
                     provenance=f"Uploaded {up['created_at'][:10]} — execution status unverified", doc_date=up["created_at"][:10])
        m = re.search(r"^#\s+(.+)$", up["markdown"], re.M)
        if m and not ctx.get("title"):
            d.title = plain(m.group(1))
        d.upload_context = ctx
        d.clauses = split_clauses(up["markdown"])
        detect_parties(d)
        if ctx.get("counterparty"):
            d.counterparty_name = ctx["counterparty"]
        if ctx.get("atliq_entity") and not d.atliq_entity:
            d.atliq_entity = ctx["atliq_entity"]
        if ctx.get("atliq_role"):
            d.atliq_role = ctx["atliq_role"]
        d.quality = up["warnings"] + quality_warnings(d)
        return d

    def _analyse(self, d: Document) -> dict:
        row = self.tracker_by_id.get(d.tracker_ids[0]) if d.tracker_ids else None
        if d.kind == "uploaded" and not row:
            ctx = d.upload_context
            row = {"contract_id": None, "client_country": ctx.get("country", ""), "notes": ctx.get("notes", ""),
                   "status": "In review", "expiry_date": "", "received_date": d.doc_date, "requested_by": ctx.get("requested_by", ""),
                   "counterparty": ctx.get("counterparty", ""), "doc_type": ctx.get("doc_type", "")}
        findings = run_rules(d, self.checklist, self.precedents, self.coverage)
        conf = detect_conflicts(d, self.register, self.tracker, AS_OF, self.by_id)
        ents = entity_checks(d, row, self.entities_doc)
        comps = companion_checks(d, self.docs, self.tracker)
        # Turn conflicts, entity mismatches and missing companions into reviewable findings
        for c in conf["conflicts"]:
            findings.append({
                "id": "F-" + c["id"], "doc_id": d.doc_id, "rule": "conflict_" + c["type"], "category": "conflict",
                "category_label": "Conflict with prior commitment", "severity": c["severity"], "title": c["title"],
                "fact": c["new_evidence"][0] if c["new_evidence"] else None, "related_facts": c["new_evidence"][1:],
                "extracted": {}, "interpretation": c["rationale"], "recommendation": "Confirm the missing facts below; consider counsel review.",
                "checklist": None, "precedents": [], "confidence": c["confidence"], "perspective": "Cross-agreement check",
                "source": "conflict", "evidence_label": d.evidence_label, "conflict": c,
            })
        for e in ents:
            if e["status"] in ("mismatch", "deviation", "review") and e["severity"] in ("High", "Medium"):
                findings.append({
                    "id": "F-E" + hashlib.sha1(f"{d.doc_id}{e['check']}{e['value']}".encode()).hexdigest()[:9], "doc_id": d.doc_id,
                    "rule": "entity_" + e["check"].lower().replace(" ", "_"), "category": "governing_law" if "law" in e["check"].lower() or "forum" in e["check"].lower() or "language" in e["check"].lower() else "entity",
                    "category_label": CATEGORY_LABELS["governing_law" if "law" in e["check"].lower() or "forum" in e["check"].lower() or "language" in e["check"].lower() else "entity"],
                    "severity": e["severity"], "title": f"{e['check']}: {e['value']}" + (f" (expected {e['expected']})" if e["expected"] else ""),
                    "fact": e["fact"], "related_facts": [], "extracted": {"value": e["value"], "expected": e["expected"]},
                    "interpretation": e["note"], "recommendation": "Confirm with finance / correct the deal context if the extraction is wrong.",
                    "checklist": self.checklist.get("governing_law") if "law" in e["check"].lower() else None, "precedents": [],
                    "confidence": "High" if e["fact"] else "Medium", "perspective": "Entity & jurisdiction check",
                    "source": "entity", "evidence_label": d.evidence_label,
                })
        for c in comps:
            if c["status"] in ("missing", "unverified", "draft"):
                sev = "High" if re.search(r"BAA|business associate|flow-down|DPA", c["document"]) else "Low"
                if c["status"] == "draft" and sev == "High":
                    sev = "Medium"
                findings.append({
                    "id": "F-C" + hashlib.sha1(f"{d.doc_id}{c['document']}".encode()).hexdigest()[:9], "doc_id": d.doc_id,
                    "rule": "companion_" + c["status"], "category": "companion", "category_label": CATEGORY_LABELS["companion"],
                    "severity": sev, "title": f"{c['document']}: {c['label'].split(' — ')[0]}",
                    "fact": {"ref": c["basis"]["ref"], "excerpt": c["basis"]["excerpt"]} if c["basis"] else None,
                    "related_facts": [], "extracted": {}, "interpretation": f"{c['why']} Status: {c['label']}." +
                    (f" Evidence: {c['evidence']} ({c['evidence_label']})." if c.get("evidence") else ""),
                    "recommendation": "Locate or execute the document before signature / data transfer.",
                    "checklist": None, "precedents": [], "confidence": "Medium", "perspective": "Document completeness",
                    "source": "companion", "evidence_label": d.evidence_label,
                })
        findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), {"High": 0, "Medium": 1, "Low": 2}.get(f["confidence"], 3)))
        return {"findings": findings, "conflicts": conf["conflicts"], "considered": conf["considered"], "entity": ents,
                "companions": comps}

    def _obligations(self) -> list[dict]:
        obs = []
        seen_tracker = set()
        for d in self.docs:
            if not d.is_contract:
                continue
            row = self.tracker_by_id.get(d.tracker_ids[0]) if d.tracker_ids else None
            if row:
                seen_tracker.add(row["contract_id"])
            obs.extend(extract_obligations(d, row, AS_OF))
        for r in self.tracker:
            if r["contract_id"] not in seen_tracker:
                obs.extend(extract_obligations(None, r, AS_OF))
        obs.extend(restriction_obligations(self.register))
        uniq = {}
        for o in obs:
            uniq.setdefault(o["id"], o)
        return list(uniq.values())

    def _build_index(self):
        items = []
        for d in self.docs:
            if d.kind == "negotiation_note":
                for e in self.precedents:
                    items.append({"doc_id": d.doc_id, "source": d.filename, "ref": e["title"], "text": e["text"],
                                  "context": e["title"], "kind": d.kind, "evidence_label": d.evidence_label + (" — deal-specific exception" if e["is_exception"] else "")})
                continue
            for c in d.clauses:
                if len(c.text) < 15:
                    continue
                items.append({"doc_id": d.doc_id, "source": d.filename, "ref": c.ref, "text": c.text, "clause_idx": c.idx,
                              "context": f"{d.title} {d.counterparty_name or ''} {c.heading}", "kind": d.kind,
                              "evidence_label": d.evidence_label})
        for r in self.tracker:
            txt = "; ".join(f"{k}: {v}" for k, v in r.items() if v and k not in ("value_usd_num",))
            items.append({"doc_id": None, "source": "contract_tracker.csv", "ref": r["contract_id"], "text": txt, "kind": "tracker",
                          "context": r["counterparty"], "evidence_label": "Tracker row (metadata only — not proof of execution)"})
        self.index = Index()
        self.index.build(items)

    # ------------------------------------------------------------ views
    def doc_overview(self, d: Document) -> dict:
        a = self.analysis.get(d.doc_id, {"findings": [], "conflicts": []})
        counts = {s: 0 for s in SEVERITIES}
        for f in a["findings"]:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        reviews = db.latest_reviews()
        open_material = sum(1 for f in a["findings"] if f["severity"] in ("Critical", "High") and f["id"] not in reviews)
        return {**d.summary(), "severity_counts": counts, "conflict_count": len(a.get("conflicts", [])),
                "open_material": open_material, "tracker": [self.tracker_by_id[t] for t in d.tracker_ids if t in self.tracker_by_id]}

    def risk_level(self, doc_id: str) -> str | None:
        a = self.analysis.get(doc_id)
        if not a or not a["findings"]:
            return None
        return min((f["severity"] for f in a["findings"]), key=lambda s: SEV_ORDER.get(s, 9))

    def contracts(self) -> list[dict]:
        docs_by_t: dict[str, list[Document]] = {}
        for d in self.docs:
            for t in d.tracker_ids:
                docs_by_t.setdefault(t, []).append(d)
        dq_by_t: dict[str, list[dict]] = {}
        for i in self.dq:
            if i.get("contract_id"):
                dq_by_t.setdefault(i["contract_id"], []).append(i)
        out = []
        for r in self.tracker:
            ds = docs_by_t.get(r["contract_id"], [])
            levels = [self.risk_level(d.doc_id) for d in ds]
            levels = [l for l in levels if l]
            out.append({**r, "documents": [{"doc_id": d.doc_id, "filename": d.filename, "kind": d.kind,
                                            "evidence_label": d.evidence_label} for d in ds],
                        "risk_level": min(levels, key=lambda s: SEV_ORDER[s]) if levels else None,
                        "data_quality": dq_by_t.get(r["contract_id"], [])})
        # uploaded documents not linked to the tracker appear as their own rows
        for d in self.docs:
            if d.kind == "uploaded" and not d.tracker_ids:
                ctx = d.upload_context
                out.append({"contract_id": d.doc_id, "counterparty": ctx.get("counterparty") or d.counterparty_name or "",
                            "doc_type": ctx.get("doc_type", ""), "atliq_entity": ctx.get("atliq_entity", ""),
                            "client_country": ctx.get("country", ""), "requested_by": ctx.get("requested_by", ""),
                            "received_date": d.doc_date, "status": "Uploaded (not in tracker)", "signed_date": "", "expiry_date": "",
                            "value_usd": ctx.get("value_usd", ""), "value_usd_num": None, "file_location": "ContractIQ upload",
                            "restrictive_clauses": "", "notes": ctx.get("notes", ""),
                            "documents": [{"doc_id": d.doc_id, "filename": d.filename, "kind": d.kind, "evidence_label": d.evidence_label}],
                            "risk_level": self.risk_level(d.doc_id), "data_quality": [], "uploaded": True})
        return out

    def dashboard(self) -> dict:
        rows = self.tracker
        statuses: dict[str, int] = {}
        for r in rows:
            statuses[r["status"] or "(blank)"] = statuses.get(r["status"] or "(blank)", 0) + 1
        under_review = [r for r in rows if r["status"].lower() == "in review"]
        blank_with_draft = [r for r in rows if not r["status"] and any(d.kind == "draft" and r["contract_id"] in d.tracker_ids for d in self.docs)]
        horizon = AS_OF + timedelta(days=EXPIRY_WINDOW_DAYS)
        upcoming, recently_expired = [], []
        for r in rows:
            e = parse_date(r["expiry_date"])
            if not e:
                continue
            if AS_OF <= e <= horizon:
                upcoming.append({**r, "days_left": (e - AS_OF).days})
            elif AS_OF - timedelta(days=90) <= e < AS_OF:
                recently_expired.append({**r, "days_ago": (AS_OF - e).days})
        upcoming.sort(key=lambda r: r["expiry_date"])
        high_risk = []
        for d in self.docs:
            if not d.is_contract:
                continue
            lvl = self.risk_level(d.doc_id)
            if lvl in ("Critical", "High"):
                a = self.analysis[d.doc_id]
                high_risk.append({"doc_id": d.doc_id, "title": d.title, "counterparty": d.counterparty_name, "kind": d.kind,
                                  "evidence_label": d.evidence_label, "risk_level": lvl, "tracker_ids": d.tracker_ids,
                                  "critical": sum(f["severity"] == "Critical" for f in a["findings"]),
                                  "high": sum(f["severity"] == "High" for f in a["findings"]),
                                  "conflicts": len(a["conflicts"])})
        high_risk.sort(key=lambda x: (x["kind"] != "draft" and x["kind"] != "uploaded", SEV_ORDER[x["risk_level"]], -x["critical"], -x["high"]))
        dups = sorted({i["contract_id"] for i in self.dq if i["code"] == "duplicate"})
        deadlines = sorted([o for o in self.obligations if o["kind"] == "review_deadline" and o["due_date"]], key=lambda o: o["due_date"])
        reviews = db.latest_reviews()
        escalated = sum(1 for v in reviews.values() if v.get("disposition") == "escalate_counsel")
        follow = sum(1 for v in reviews.values() if v.get("follow_up"))
        return {
            "as_of": AS_OF.isoformat(),
            "kpis": {
                "total_contracts": len(rows), "suspected_duplicates": dups,
                "under_review": len(under_review), "under_review_blank_status": len(blank_with_draft),
                "high_risk_drafts": sum(1 for h in high_risk if h["kind"] in ("draft", "uploaded")),
                "high_risk_executed": sum(1 for h in high_risk if h["kind"] == "executed"),
                "upcoming_expirations": len(upcoming), "expiry_window_days": EXPIRY_WINDOW_DAYS,
                "conflicts": sum(len(a["conflicts"]) for a in self.analysis.values()),
                "escalated": escalated, "follow_up": follow,
            },
            "status_breakdown": statuses, "high_risk": high_risk, "upcoming_expirations": upcoming,
            "recently_expired": recently_expired, "review_deadlines": deadlines,
            "data_quality_counts": self._dq_counts(),
        }

    def _dq_counts(self) -> dict:
        c: dict[str, int] = {}
        for i in self.dq:
            c[i["code"]] = c.get(i["code"], 0) + 1
        return c

    def document_detail(self, doc_id: str) -> dict | None:
        d = self.by_id.get(doc_id)
        if not d:
            return None
        return {**self.doc_overview(d), "text": d.text, "clauses": [c.to_dict() for c in d.clauses],
                "corrections": db.corrections(doc_id), "checklist_version": CHECKLIST_VERSION}

    def analysis_for(self, doc_id: str) -> dict | None:
        d = self.by_id.get(doc_id)
        if not d:
            return None
        a = self.analysis.get(doc_id, {"findings": [], "conflicts": [], "considered": [], "entity": [], "companions": []})
        reviews = db.latest_reviews()
        overrides = db.obligation_overrides()
        findings = [{**f, "review": reviews.get(f["id"])} for f in a["findings"]]
        obs = [{**o, **overrides.get(o["id"], {})} for o in self.obligations if o["doc_id"] == doc_id]
        searched = [x for x in self.docs if x.kind == "executed"]
        gaps = [i for i in self.dq if i["code"] == "executed_copy_missing"]
        return {"doc_id": doc_id, "findings": findings, "conflicts": a["conflicts"], "considered": a["considered"],
                "entity": a["entity"], "companions": a["companions"], "obligations": obs,
                "coverage": {"executed_searched": [x.filename for x in searched],
                             "not_in_repository": [f"{i['contract_id']}: {self.tracker_by_id[i['contract_id']]['counterparty']} "
                                                   f"{self.tracker_by_id[i['contract_id']]['doc_type']}" for i in gaps],
                             "statement": f"Conflict checks searched {len(searched)} executed contracts in the repository. "
                                          f"{len(gaps)} tracker rows marked Signed have no executed copy here and could not be "
                                          "searched. 'No conflict found' does not mean no conflict exists."},
                "quality": d.quality, "mode": llm.status()}

    def review_queue(self) -> list[dict]:
        reviews = db.latest_reviews()
        out = []
        for doc_id, a in self.analysis.items():
            d = self.by_id[doc_id]
            for f in a["findings"]:
                out.append({"id": f["id"], "doc_id": doc_id, "doc_title": d.title, "counterparty": d.counterparty_name,
                            "kind": d.kind, "severity": f["severity"], "category_label": f["category_label"], "title": f["title"],
                            "confidence": f["confidence"], "ref": f["fact"]["ref"] if f.get("fact") else None,
                            "review": reviews.get(f["id"])})
        out.sort(key=lambda x: (x["kind"] == "executed", SEV_ORDER.get(x["severity"], 9)))
        return out

    def finding(self, fid: str) -> dict | None:
        for a in self.analysis.values():
            for f in a["findings"]:
                if f["id"] == fid:
                    return f
        return None

    # ------------------------------------------------------------ Q&A
    def ask(self, question: str, doc_id: str | None, use_ai: bool, consent: bool) -> dict:
        question = question.strip()
        if not question:
            return {"error": "Please enter a question."}
        hits = []
        q = question.lower()
        if doc_id:
            in_doc = self.index.search(question, k=6, doc_ids={doc_id})
            hits = [{**h, "in_scope": True} for h in in_doc]
            hits += [{**h, "in_scope": False} for h in self.index.search(question, k=8) if h.get("doc_id") != doc_id][:3]
        else:
            hits = self.index.search(question, k=8)
        best_cov = max((h["coverage"] for h in hits), default=0)
        insufficient = not hits or best_cov < 0.34
        related = []
        if doc_id and doc_id in self.analysis:
            cat_words = {"liquidated_damages": "ld|liquidated|delay|penalt", "liability": "liabil|cap|unlimited",
                         "indemnity": "indemn", "payment": "pay|invoice|days", "termination": "terminat|notice|convenience",
                         "ip": "ip\\b|intellectual|own|reuse|licen", "confidentiality": "confiden|nda|residual",
                         "exclusivity": "exclusiv|non-compete|compet|mfn|rate|price", "data_security": "data|breach|security|phi|offshore",
                         "governing_law": "law|jurisdiction|court|arbitrat", "insurance": "insur|cyber",
                         "entity": "entity|invoice|inc|pvt", "conflict": "conflict|prior|already|promised|commit",
                         "companion": "baa|dpa|nda|document|missing"}
            cats = {c for c, p in cat_words.items() if re.search(p, q)}
            rel_f = [f for f in self.analysis[doc_id]["findings"] if f["category"] in cats][:6]
            related = [{"id": f["id"], "severity": f["severity"], "title": f["title"], "ref": f["fact"]["ref"] if f.get("fact") else None,
                        "category_label": f["category_label"]} for f in rel_f]
            # Clauses the rules engine already identified for these topics are the strongest in-scope evidence: put them first.
            d = self.by_id[doc_id]
            have = {h.get("clause_idx") for h in hits if h.get("in_scope")}
            extra = []
            for f in rel_f:
                ci = (f.get("fact") or {}).get("clause_idx")
                if ci is not None and ci not in have and f["source"] == "rules":
                    c = d.clauses[ci]
                    extra.append({"doc_id": doc_id, "source": d.filename, "ref": c.ref, "text": c.text, "clause_idx": ci, "kind": d.kind,
                                  "evidence_label": d.evidence_label, "score": None, "matched_terms": [], "coverage": 1.0, "in_scope": True})
                    have.add(ci)
            hits = extra[:4] + hits
            if extra:
                insufficient = False
            # The party clause tells the model which party is AtliQ (e.g. "Contractor").
            party = next((c for c in d.clauses if d.atliq_term and "atliq" in c.text.lower()
                          and re.search(rf"\b{re.escape(d.atliq_term)}\b", c.text)), None)
            if party and party.idx not in have:
                hits.insert(0, {"doc_id": doc_id, "source": d.filename, "ref": party.ref, "text": party.text, "clause_idx": party.idx,
                                "kind": d.kind, "evidence_label": d.evidence_label, "score": None, "matched_terms": [],
                                "coverage": 0.0, "in_scope": True,
                                "context": f"Party clause: AtliQ is referred to as '{d.atliq_term}'"})
        passages = [{"n": i + 1, **h} for i, h in enumerate(hits)]
        result ={"question": question, "doc_id": doc_id, "passages": passages, "related_findings": related,
                  "insufficient_evidence": insufficient, "mode": "demo"}
        if use_ai:
            st = llm.status()
            if not st["available"]:
                result["ai_error"] = "AI is not configured (no API key). Showing local search results only."
            elif not consent:
                result["ai_error"] = "AI answer not requested: consent to send excerpts was not given."
            elif not passages:
                result["ai_error"] = "No relevant passages were found, so nothing was sent to the AI."
            else:
                try:
                    ans = llm.grounded_answer(question, passages)
                    if not ans["answer"].strip():
                        ans["answer"] = "The AI could not answer this from the retrieved sources (insufficient evidence)."
                    result.update({"mode": "ai", "ai": ans, "insufficient_evidence": ans["insufficient_evidence"]})
                    db.log_ai("qa", doc_id, st["provider"], st["model"],
                              f"question + {len(passages)} excerpts: " + ", ".join(f"{p['source']} {p['ref']}" for p in passages)[:2000], ans)
                except llm.LLMError as e:
                    result["ai_error"] = str(e)
        if result["mode"] == "demo":
            if insufficient:
                result["answer"] = ("Insufficient evidence: no passage in the repository matches enough of this question to answer it. "
                                    "Check the contract directly, or rephrase using contract terms (e.g. 'liability cap', 'payment days').")
            else:
                result["answer"] = ("DEMO MODE — no AI-generated answer. Below are the most relevant passages found by local search, "
                                    "with their evidence type. Read the cited text to answer; related rule-based findings are linked.")
        return result

    # ------------------------------------------------------------ AI risk review
    def ai_review(self, doc_id: str, consent: bool) -> dict:
        d = self.by_id.get(doc_id)
        if not d:
            return {"error": "Document not found."}
        st = llm.status()
        if not st["available"]:
            return {"error": "AI is not configured (no API key). The rule-based findings above are the demo-mode analysis."}
        if not consent:
            return {"error": "Consent is required before sending contract text to the AI provider."}
        key = r"liab|indemn|liquidat|delay|pay|invoice|terminat|intellectual|licen|confiden|exclusiv|compet|data|security|law|jurisdiction|insur|warrant"
        # Keep the request small (provider rate limits): the most risk-relevant clauses, each capped in length.
        cands = [c for c in d.clauses if c.kind != "table" and len(c.text) > 40 and re.search(key, c.heading + " " + c.text, re.I)]
        cands.sort(key=lambda c: -len(re.findall(key, c.heading + " " + c.text, re.I)))
        budget, chosen = int(os.environ.get("CONTRACTIQ_AI_REVIEW_CHARS", "14000")), []
        for c in cands:
            t = c.text[:1200]
            if budget - len(t) < 0:
                continue
            budget -= len(t)
            chosen.append(c)
        clauses = [{"idx": c.idx, "ref": c.ref, "text": c.text[:1200]} for c in sorted(chosen, key=lambda c: c.idx)]
        try:
            res = llm.ai_risk_review(d.title, clauses)
        except llm.LLMError as e:
            return {"error": str(e)}
        db.log_ai("risk_review", doc_id, st["provider"], st["model"], f"{len(clauses)} clauses from {d.filename}", res)
        res["provider"], res["model"], res["sent_clause_count"] = st["provider"], st["model"], len(clauses)
        return res

    # ------------------------------------------------------------ exports
    def export_summary(self, doc_id: str, escalation_only: bool = False) -> str | None:
        d = self.by_id.get(doc_id)
        a = self.analysis_for(doc_id)
        if not d or not a:
            return None
        reviews = db.latest_reviews()
        fs = a["findings"]
        if escalation_only:
            fs = [f for f in fs if (reviews.get(f["id"]) or {}).get("disposition") == "escalate_counsel"]
        L = []
        title = "Counsel escalation package" if escalation_only else "Contract review summary"
        L += [f"# {title}: {d.title}", "",
              f"- **Document:** {d.filename} ({d.evidence_label})",
              f"- **Counterparty:** {d.counterparty_name or 'not identified'}",
              f"- **AtliQ entity named in contract:** {d.atliq_entity or 'not identified'}",
              f"- **Tracker row(s):** {', '.join(d.tracker_ids) or 'none'} ({d.tracker_match_basis or 'n/a'})",
              f"- **Review date basis:** {AS_OF.isoformat()} · Checklist applied: {CHECKLIST_VERSION}",
              f"- **Analysis mode:** deterministic rules{' + AI (verified quotes only)' if llm.status()['available'] else ' (demo mode — no AI used)'}",
              "", "> Decision-support output. It is not legal advice and it does not approve, sign or send anything. "
                  "Facts below are quoted from the source; interpretations are labelled.", ""]
        if d.quality:
            L += ["## Extraction quality warnings", ""] + [f"- {q['message']}" for q in d.quality] + [""]
        if escalation_only and not fs:
            L += ["_No findings are currently marked 'escalate to counsel'._", ""]
        L += ["## Findings" if not escalation_only else "## Escalated findings", ""]
        for f in fs:
            r = reviews.get(f["id"]) or {}
            L += [f"### [{f['severity']}] {f['title']}", f"*{f['category_label']} · confidence {f['confidence']} · {f['perspective']}*", ""]
            if f.get("fact"):
                L += [f"**Fact — {d.filename}, {f['fact']['ref']}:**", "", "> " + plain(f["fact"]["excerpt"])[:1500], ""]
            else:
                L += ["**Fact:** no single clause (see interpretation).", ""]
            L += [f"**Interpretation (rule-based, not legal advice):** {f['interpretation']}", "",
                  f"**Suggested next step:** {f['recommendation']}", ""]
            if f.get("conflict"):
                c = f["conflict"]
                L += [f"**Prior commitment — {c['prior_filename']}, {c['prior_ref']} ({c['prior_evidence_label']}):**", "",
                      "> " + plain(c["prior_excerpt"])[:1200], "", "**Facts still needed to confirm:**"] + [f"- {m}" for m in c["missing_facts"]] + [""]
            if f.get("checklist"):
                L += [f"**Checklist:** {'; '.join(f['checklist']['items'])} — _{f['checklist']['evidence_label']}_", ""]
            for p in f.get("precedents") or []:
                L += [f"- Precedent ({p['evidence_label']}): **{p['title']}** — {p['excerpt']}"]
            L += [f"**Reviewer decision:** {r.get('disposition', 'not yet reviewed')}" + (f" — {r['note']}" if r.get("note") else "") +
                  (f" (by {r['reviewer']}, {r['created_at']})" if r.get("reviewer") else "") + (" · flagged for follow-up" if r.get("follow_up") else ""), ""]
        if not escalation_only:
            L += ["## Companion documents", ""]
            L += [f"- **{c['document']}** — {c['label']}" + (f" (evidence: {c['evidence']})" if c.get("evidence") else "") for c in a["companions"]] or ["- None identified."]
            L += ["", "## Entity, currency and governing-law checks", ""]
            L += [f"- {e['check']}: **{e['status']}** — {e['value'] or 'not found'}" + (f" (expected {e['expected']})" if e["expected"] else "") + f". {e['note']}" for e in a["entity"]]
            L += ["", "## Obligations and deadlines", ""]
            L += [f"- {o['title']} — due {o['due_date'] or 'unverified'} ({o['due_basis']}); owner: {o.get('owner', 'Unassigned')}; status: {o.get('status', 'Open')}" for o in a["obligations"]] or ["- None extracted."]
        unresolved = [f for f in a["findings"] if f["severity"] in ("Critical", "High") and (reviews.get(f["id"]) or {}).get("disposition") not in ("resolved", "not_relevant")]
        L += ["", "## Unresolved material items", ""] + ([f"- [{f['severity']}] {f['title']}" for f in unresolved] or ["- None."])
        L += ["", "## Search coverage", "", a["coverage"]["statement"], ""]
        return "\n".join(L)

    def export_extracted(self, doc_id: str) -> str | None:
        d = self.by_id.get(doc_id)
        if not d:
            return None
        header = [f"<!-- Extracted by AtliQ ContractIQ from {d.filename}. Evidence type: {d.evidence_label}. -->"]
        for q in d.quality:
            header.append(f"<!-- {q['level'].upper()}: {q['message']} -->")
        return "\n".join(header) + "\n\n" + d.text


engine: Engine | None = None


def get() -> Engine:
    global engine
    if engine is None:
        engine = Engine()
    return engine
