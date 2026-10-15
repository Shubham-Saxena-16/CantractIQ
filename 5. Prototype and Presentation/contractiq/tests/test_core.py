"""Core regression tests against the real dataset. Run:  .venv\\Scripts\\python -m unittest discover -s tests -v

Uses a temporary data directory, so the app's own database is not touched. No network calls are made.
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["CONTRACTIQ_DATA_DIR"] = tempfile.mkdtemp(prefix="ciq_test_")
os.environ.pop("GROQ_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)

from backend import llm  # noqa: E402
from backend.checks import companion_checks, entity_checks, tracker_quality  # noqa: E402
from backend.commitments import build_register, detect_conflicts  # noqa: E402
from backend.corpus import link_documents, load_corpus, load_tracker, parse_negotiation_entries  # noqa: E402
from backend.extraction import ExtractionError, extract  # noqa: E402
from backend.rules import known_coverage_from_notes, parse_checklist, run_rules  # noqa: E402

AS_OF = date(2026, 9, 28)
DOCS = load_corpus()
TRACKER = load_tracker()
link_documents(DOCS, TRACKER)
BY = {d.doc_id: d for d in DOCS}
CHECK = parse_checklist(next(d for d in DOCS if d.kind == "checklist"))
PREC = parse_negotiation_entries(next(d for d in DOCS if d.kind == "negotiation_note"))
COV = known_coverage_from_notes([d for d in DOCS if d.kind == "meeting_note"])
REG = build_register(DOCS, TRACKER, AS_OF)
ENT = next(d for d in DOCS if d.kind == "company_reference")
TB = {r["contract_id"]: r for r in TRACKER}


def doc(prefix):
    return next(d for d in DOCS if d.doc_id.startswith(prefix))


def rules_of(prefix):
    return {f["rule"]: f for f in run_rules(doc(prefix), CHECK, PREC, COV)}


def conflicts_of(prefix):
    return detect_conflicts(doc(prefix), REG, TRACKER, AS_OF, BY)["conflicts"]


class CorpusTests(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(TRACKER), 48)
        self.assertEqual(sum(d.kind == "executed" for d in DOCS), 17)
        self.assertEqual(sum(d.kind == "draft" for d in DOCS), 15)

    def test_tracker_links(self):
        expected = {"2026-09-10_harrington_health_msa": "C-023", "2026-09-16_harrington_health_baa": "C-046",
                    "2026-09-19_lakeshore": "C-026", "2025-03-15_al_noor_hospitality": "C-007",
                    "2025-01-22_al_noor_mutual_nda": "C-013", "2025-10-06_atliq_intercompany": "C-044"}
        for p, cid in expected.items():
            self.assertEqual(doc(p).tracker_ids, [cid], p)

    def test_party_detection(self):
        self.assertEqual(doc("2026-09-23_rheinwerk").atliq_term, "Supplier")
        self.assertEqual(doc("2026-09-15_travelhub").atliq_entity, "AtliQ Inc")
        self.assertEqual(doc("2022-07-01_orbit").atliq_entity, "AtliQ Technologies Pvt Ltd")  # OCR "TECHN0LOGIES"

    def test_ocr_quality_warnings(self):
        codes = {q["code"] for q in doc("2022-07-01_orbit").quality}
        self.assertTrue({"ocr_source", "illegible"} <= codes)


class RuleTests(unittest.TestCase):
    def test_harrington(self):
        r = rules_of("2026-09-10_harrington_health_msa")
        self.assertEqual(r["liability_unlimited"]["severity"], "Critical")
        self.assertEqual(r["ld_risk"]["severity"], "Critical")
        self.assertIsNone(r["ld_risk"]["extracted"]["cap_percent"])
        self.assertEqual(r["payment_term_long"]["extracted"]["days"], 90)
        self.assertIn("indemnity_others_negligence", r)
        self.assertIn("insurance_cyber_gap", r)
        # every finding with a fact quotes text that really exists in the document
        d = doc("2026-09-10_harrington_health_msa")
        for f in r.values():
            if f["fact"]:
                self.assertIn(f["fact"]["excerpt"], d.text)

    def test_negotiated_ld_is_low(self):
        for p in ("2025-03-10_acme", "2026-08-15_trustline", "2025-06-20_northwind"):
            r = rules_of(p)
            self.assertIn("ld_within_preference", r, p)
            self.assertNotIn("ld_risk", r, p)

    def test_brightwater_uncapped_ld(self):
        self.assertEqual(rules_of("2025-11-28_brightwater")["ld_risk"]["severity"], "Critical")

    def test_finserve_nda(self):
        r = rules_of("2026-09-25_finserve")
        self.assertIn("nda_one_way", r)
        self.assertIn("nda_residuals", r)

    def test_buyer_side_fairness(self):
        r = rules_of("2026-09-26_kriti")
        self.assertIn("payment_pay_when_paid", r)
        self.assertEqual(r["payment_term_long"]["extracted"]["days"], 120)
        self.assertIn("buyer", r["payment_pay_when_paid"]["perspective"])

    def test_al_noor_exception_precedent_labelled(self):
        f = rules_of("2026-09-18_gulf_crown")["ld_risk"]
        self.assertTrue(any(p["is_exception"] for p in f["precedents"]))


class ConflictTests(unittest.TestCase):
    def test_register(self):
        types = {(c["type"], c["status"]) for c in REG}
        self.assertIn(("non_compete", "expired"), types)       # Orbit, ended 2025-06-30
        al = next(c for c in REG if "AL NOOR" in (c["counterparty"] or "").upper())
        self.assertEqual(al["end"], "2029-09-14")
        self.assertTrue(al["binds_affiliates"])
        self.assertTrue(al["waivers"])

    def test_expected_conflicts(self):
        self.assertTrue(any("AL NOOR" in c["prior_counterparty"].upper() for c in conflicts_of("2026-09-18_gulf_crown")))
        self.assertTrue(any("AL NOOR" in c["prior_counterparty"].upper() for c in conflicts_of("2026-09-21_blueorchid")))
        self.assertTrue(any(c["type"] == "mfn_pricing" for c in conflicts_of("2026-09-19_lakeshore")))
        self.assertTrue(any("CLOUDSPAN" in c["prior_counterparty"].upper() for c in conflicts_of("2026-09-24_datavane")))
        self.assertTrue(any(c["type"] == "ip_assignment" for c in conflicts_of("2026-09-23_rheinwerk")))

    def test_no_false_conflicts(self):
        for p in ("2026-09-27_loopmart", "2026-09-24_sunrise_foods_sow2", "2026-02-10_al_noor_waiver", "2025-01-22_al_noor_mutual_nda"):
            self.assertEqual(conflicts_of(p), [], p)

    def test_waiver_does_not_cover_gulf_crown(self):
        c = next(c for c in conflicts_of("2026-09-18_gulf_crown") if c["type"] == "non_compete")
        self.assertFalse(any(w["covers_this_deal"] for w in c["waiver_assessment"]))


class CheckTests(unittest.TestCase):
    def test_travelhub_entity(self):
        d = doc("2026-09-15_travelhub")
        res = {e["check"]: e for e in entity_checks(d, TB["C-024"], ENT)}
        self.assertEqual(res["Contracting entity"]["status"], "mismatch")
        self.assertEqual(res["Invoicing entity"]["status"], "mismatch")

    def test_harrington_companions(self):
        comps = companion_checks(doc("2026-09-10_harrington_health_msa"), DOCS, TRACKER)
        names = {c["document"]: c["status"] for c in comps}
        self.assertEqual(names["HIPAA Business Associate Agreement"], "draft")
        self.assertTrue(any("Daniel Ortiz" in k and v == "missing" for k, v in names.items()))
        self.assertFalse(any("Kriti" in k for k in names))  # Kriti's note only mentions the Harrington *template*

    def test_tracker_quality(self):
        dq = tracker_quality(TRACKER, DOCS, REG, AS_OF)
        dups = {i["contract_id"] for i in dq if i["code"] == "duplicate"}
        self.assertEqual(dups, {"C-010", "C-011"})
        understated = {i["contract_id"] for i in dq if i["code"] == "restrictions_understated"}
        self.assertTrue({"C-007", "C-002", "C-032"} <= understated)


class ExtractionAndAiTests(unittest.TestCase):
    def test_extraction_errors(self):
        with self.assertRaises(ExtractionError):
            extract("x.pdf", b"%PDF-1.4 broken")
        with self.assertRaises(ExtractionError):
            extract("x.doc", b"\xd0\xcf old")
        with self.assertRaises(ExtractionError):
            extract("x.txt", b"")

    def test_markdown_passthrough(self):
        md, warnings, info = extract("a.md", "# T\n\n1.1 Clause".encode())
        self.assertEqual(info["format"], "markdown")

    def test_quote_verification(self):
        src = "12.1 **The Supplier** shall not provide revenue-management services to any Hospitality Business in the GCC."
        self.assertTrue(llm.verify_quote("shall not provide revenue-management services", src))
        self.assertTrue(llm.verify_quote("The Supplier shall not … any Hospitality Business in the GCC", src))
        self.assertFalse(llm.verify_quote("shall not provide any services worldwide", src))
        self.assertFalse(llm.verify_quote("GCC", src))

    def test_demo_mode_without_key(self):
        self.assertEqual(llm.status()["mode"], "demo")


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend.app import app
        cls.c = TestClient(app)

    def test_review_append_only(self):
        a = self.c.get("/api/documents/2026-09-18_gulf_crown_hotels_msa_draft/analysis").json()
        fid = a["findings"][0]["id"]
        r1 = self.c.post(f"/api/findings/{fid}/review", json={"disposition": "needs_info", "reviewer": "Test"})
        r2 = self.c.post(f"/api/findings/{fid}/review", json={"disposition": "escalate_counsel", "note": "n", "reviewer": "Test"})
        self.assertEqual(r2.json()["review"]["disposition"], "escalate_counsel")
        self.assertEqual(len(self.c.get(f"/api/findings/{fid}/history").json()), 2)
        from backend.config import DB_PATH
        con = sqlite3.connect(DB_PATH)
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                con.execute("UPDATE review_events SET disposition='resolved'")
        finally:
            con.close()
        self.assertEqual(self.c.post(f"/api/findings/{fid}/review", json={"disposition": "approve", "reviewer": "T"}).status_code, 422)

    def test_ask_insufficient(self):
        r = self.c.post("/api/ask", json={"question": "kangaroo quantum blockchain"}).json()
        self.assertTrue(r["insufficient_evidence"])
        r = self.c.post("/api/ask", json={"question": "payment term", "use_ai": True, "consent": True}).json()
        self.assertEqual(r["mode"], "demo")  # no key -> never pretends to be AI
        self.assertIn("ai_error", r)

    def test_ai_review_refused_without_key(self):
        self.assertEqual(self.c.post("/api/documents/2026-09-18_gulf_crown_hotels_msa_draft/ai-review", json={"consent": True}).status_code, 400)

    def test_exports(self):
        t = self.c.get("/api/documents/2026-09-10_harrington_health_msa_draft/export/summary.md").text
        self.assertIn("not legal advice", t)
        self.assertIn("Search coverage", t)


if __name__ == "__main__":
    unittest.main()
