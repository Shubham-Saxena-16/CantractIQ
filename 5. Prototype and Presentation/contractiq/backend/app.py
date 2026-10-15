"""FastAPI application: JSON API under /api and the built React frontend at /."""
from __future__ import annotations

import hashlib
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from . import db, engine as engine_mod, llm
from .config import APP_DIR, AS_OF, CHECKLIST_VERSION, DATASET_DIR, MAX_UPLOAD_BYTES, UPLOAD_DIR, EXTRACTED_DIR
from .engine import DISPOSITIONS
from .extraction import ExtractionError, extract

def E():
    return engine_mod.get()


@asynccontextmanager
async def lifespan(_app):
    E()  # analyse the repository once at startup
    yield


app = FastAPI(title="AtliQ ContractIQ", version="0.1.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def _unhandled(request, exc):  # pragma: no cover - last-resort error reporting
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {type(exc).__name__}: {exc}"})


# ---------------------------------------------------------------- meta & dashboard

@app.get("/api/meta")
def meta():
    e = E()
    return {"app": "AtliQ ContractIQ", "as_of": AS_OF.isoformat(), "dataset_dir": str(DATASET_DIR),
            "checklist_version": CHECKLIST_VERSION, "ai": llm.status(), "dispositions": DISPOSITIONS,
            "counts": {"documents": sum(d.is_contract for d in e.docs), "tracker_rows": len(e.tracker)},
            "guardrail": "ContractIQ is decision support only. It never signs, approves, rejects, redlines or sends contracts."}


@app.get("/api/dashboard")
def dashboard():
    return E().dashboard()


@app.get("/api/contracts")
def contracts():
    return E().contracts()


@app.get("/api/data-quality")
def data_quality():
    e = E()
    return {"issues": e.dq, "counts": e._dq_counts()}


# ---------------------------------------------------------------- documents

@app.get("/api/documents")
def documents():
    e = E()
    return [e.doc_overview(d) | {"risk_level": e.risk_level(d.doc_id)} for d in e.docs if d.is_contract]


@app.get("/api/sources")
def sources():
    e = E()
    return [{"doc_id": d.doc_id, "filename": d.filename, "kind": d.kind, "evidence_label": d.evidence_label, "title": d.title}
            for d in e.docs]


@app.get("/api/documents/{doc_id}")
def document(doc_id: str):
    d = E().document_detail(doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    return d


@app.get("/api/documents/{doc_id}/analysis")
def analysis(doc_id: str):
    a = E().analysis_for(doc_id)
    if not a:
        raise HTTPException(404, "Document not found")
    return a


def _md_response(text: str | None, name: str):
    if text is None:
        raise HTTPException(404, "Document not found")
    return PlainTextResponse(text, media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/documents/{doc_id}/export/summary.md")
def export_summary(doc_id: str):
    return _md_response(E().export_summary(doc_id), f"{doc_id}_review_summary.md")


@app.get("/api/documents/{doc_id}/export/escalation.md")
def export_escalation(doc_id: str):
    return _md_response(E().export_summary(doc_id, escalation_only=True), f"{doc_id}_counsel_escalation.md")


@app.get("/api/documents/{doc_id}/export/extracted.md")
def export_extracted(doc_id: str):
    return _md_response(E().export_extracted(doc_id), f"{doc_id}_extracted.md")


class Correction(BaseModel):
    field: str = Field(..., pattern=r"^(counterparty|atliq_entity|client_country|governing_law|currency|invoice_entity|doc_type|deadline)$")
    value: str = Field("", max_length=300)
    reviewer: str = Field(..., min_length=1, max_length=80)


@app.post("/api/documents/{doc_id}/corrections")
def add_correction(doc_id: str, body: Correction):
    if doc_id not in E().by_id:
        raise HTTPException(404, "Document not found")
    db.execute("INSERT INTO context_corrections(doc_id, field, value, reviewer, created_at) VALUES(?,?,?,?,?)",
               (doc_id, body.field, body.value, body.reviewer, db.now()))
    return {"ok": True, "corrections": db.corrections(doc_id),
            "note": "Stored as a reviewer correction. The original extracted value is kept and still shown."}


class Consent(BaseModel):
    consent: bool = False


@app.post("/api/documents/{doc_id}/ai-review")
def ai_review(doc_id: str, body: Consent):
    res = E().ai_review(doc_id, body.consent)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


# ---------------------------------------------------------------- review

class ReviewIn(BaseModel):
    disposition: str | None = None
    note: str | None = Field(None, max_length=4000)
    follow_up: bool = False
    reviewer: str = Field(..., min_length=1, max_length=80)


@app.post("/api/findings/{fid}/review")
def review_finding(fid: str, body: ReviewIn):
    f = E().finding(fid)
    if not f:
        raise HTTPException(404, "Finding not found")
    if body.disposition and body.disposition not in DISPOSITIONS:
        raise HTTPException(422, f"disposition must be one of {DISPOSITIONS}")
    if not body.disposition and not body.note and not body.follow_up:
        raise HTTPException(422, "Provide a disposition, a note or a follow-up flag.")
    ev = db.add_review("finding", fid, f["doc_id"], body.disposition, body.note, body.follow_up, body.reviewer)
    return {"ok": True, "event": ev, "review": db.latest_reviews().get(fid)}


@app.get("/api/findings/{fid}/history")
def finding_history(fid: str):
    return db.review_history(fid)


@app.get("/api/review-queue")
def review_queue():
    return E().review_queue()


# ---------------------------------------------------------------- commitments & obligations

@app.get("/api/commitments")
def commitments():
    e = E()
    conflicts = []
    for doc_id, a in e.analysis.items():
        d = e.by_id[doc_id]
        for c in a["conflicts"]:
            conflicts.append({**c, "new_title": d.title, "new_filename": d.filename, "new_kind": d.kind,
                              "new_counterparty": d.counterparty_name})
    searched = [d.filename for d in e.docs if d.kind == "executed"]
    gaps = [i for i in e.dq if i["code"] == "executed_copy_missing"]
    return {"register": e.register, "conflicts": conflicts, "historical": e.history_issues,
            "precedents": e.precedents,
            "coverage": {"executed_searched": searched,
                         "not_in_repository": [f"{i['contract_id']}: {e.tracker_by_id[i['contract_id']]['counterparty']} "
                                               f"{e.tracker_by_id[i['contract_id']]['doc_type']}" for i in gaps],
                         "statement": f"The register was built from {len(searched)} executed contracts. {len(gaps)} contracts the tracker "
                                      "marks as signed are not in the repository, so their commitments are unknown."}}


@app.get("/api/obligations")
def obligations():
    e = E()
    ov = db.obligation_overrides()
    out = []
    for o in e.obligations:
        d = e.by_id.get(o["doc_id"]) if o["doc_id"] else None
        row = e.tracker_by_id.get(o["tracker_id"]) if o["tracker_id"] else None
        out.append({**o, **ov.get(o["id"], {}), "doc_title": d.title if d else None,
                    "counterparty": (d.counterparty_name if d else None) or (row["counterparty"] if row else None),
                    "doc_kind": d.kind if d else "tracker only"})
    out.sort(key=lambda o: (o["due_date"] is None, o["due_date"] or ""))
    return out


class ObligationIn(BaseModel):
    owner: str | None = Field(None, max_length=80)
    status: str | None = Field(None, pattern=r"^(Open|In progress|Done|Not applicable|Expired|Needs verification)$")
    note: str | None = Field(None, max_length=2000)
    reviewer: str = Field(..., min_length=1, max_length=80)


@app.post("/api/obligations/{oid}")
def update_obligation(oid: str, body: ObligationIn):
    if not any(o["id"] == oid for o in E().obligations):
        raise HTTPException(404, "Obligation not found")
    db.execute("INSERT INTO obligation_updates(obligation_id, owner, status, note, reviewer, created_at) VALUES(?,?,?,?,?,?)",
               (oid, body.owner, body.status, body.note, body.reviewer, db.now()))
    return {"ok": True, "current": db.obligation_overrides().get(oid)}


# ---------------------------------------------------------------- Q&A

class AskIn(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    doc_id: str | None = None
    use_ai: bool = False
    consent: bool = False


@app.post("/api/ask")
def ask(body: AskIn):
    res = E().ask(body.question, body.doc_id or None, body.use_ai, body.consent)
    if "error" in res:
        raise HTTPException(422, res["error"])
    return res


# ---------------------------------------------------------------- upload

@app.post("/api/upload")
async def upload(file: UploadFile = File(...), counterparty: str = Form(""), doc_type: str = Form(""),
                 atliq_entity: str = Form(""), country: str = Form(""), deadline: str = Form(""),
                 tracker_id: str = Form(""), atliq_role: str = Form(""), notes: str = Form(""), requested_by: str = Form(""),
                 value_usd: str = Form("")):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB).")
    fname = Path(file.filename or "upload").name
    try:
        md, warnings, info = extract(fname, data)
    except ExtractionError as e:
        raise HTTPException(422, f"Extraction failed: {e}")
    e = E()
    if tracker_id and tracker_id not in e.tracker_by_id:
        raise HTTPException(422, f"Unknown tracker id {tracker_id}")
    doc_id = "upload_" + hashlib.sha1(data).hexdigest()[:10] + "_" + re.sub(r"[^a-z0-9]+", "_", Path(fname).stem.lower())[:40]
    stored = UPLOAD_DIR / f"{doc_id}{Path(fname).suffix.lower()}"
    stored.write_bytes(data)
    (EXTRACTED_DIR / f"{doc_id}.md").write_text(md, encoding="utf-8")
    ctx = {k: v.strip() for k, v in {"counterparty": counterparty, "doc_type": doc_type, "atliq_entity": atliq_entity,
                                    "country": country, "deadline": deadline, "tracker_id": tracker_id, "atliq_role": atliq_role,
                                    "notes": notes, "requested_by": requested_by, "value_usd": value_usd}.items() if v and v.strip()}
    ctx["not_provided"] = [k for k in ("counterparty", "doc_type", "atliq_entity", "country", "deadline") if k not in ctx]
    db.save_upload(doc_id, fname, str(stored), md, ctx, warnings, info)
    e.build()
    d = e.by_id[doc_id]
    return {"doc_id": doc_id, "info": info, "warnings": d.quality, "clause_count": len(d.clauses),
            "findings": len(e.analysis.get(doc_id, {}).get("findings", []))}


@app.post("/api/reload")
def reload():
    E().build()
    return {"ok": True}


# ---------------------------------------------------------------- frontend

DIST = (APP_DIR / "frontend" / "dist").resolve()
# index.html must always be revalidated: it names the current hashed bundle, and a cached copy pointing at a
# bundle deleted by a rebuild renders a blank page. Hashed files under assets/ never change, so cache them hard.
NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404)
    index = DIST / "index.html"
    if not index.exists():
        return PlainTextResponse("Frontend not built. Run `npm install` and `npm run build` in contractiq/frontend, "
                                 "then reload. (For development use `npm run dev` on port 5173.)", 503, headers=NO_CACHE)
    if path:
        f = (DIST / path).resolve()
        if DIST in f.parents and f.is_file():
            return FileResponse(f, headers=IMMUTABLE if path.startswith("assets/") else NO_CACHE)
        if path.startswith("assets/"):
            raise HTTPException(404, "Asset not found — the page may be from an older build; hard-refresh (Ctrl+F5).")
    return FileResponse(index, headers=NO_CACHE)
