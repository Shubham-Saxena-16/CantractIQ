"""Split a Markdown contract into citable clauses, keeping section headings, clause numbers and pages.

Page numbers are only known when the source carries page markers: either "Page N of M" footers
(as in the OCR'd scan) or the `<!-- page N -->` markers our PDF extractor writes. Otherwise the
page is left as None and only the section reference is cited.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

HEADING_RE = re.compile(r"^(#{1,4})\s+(.*\S)\s*$")
PAGE_MARK_RE = re.compile(r"<!--\s*page\s+(\d+)\s*-->", re.I)
PAGE_FOOTER_RE = re.compile(r"^\s*Page\s+(\d+)\s+of\s+\d+\s*$", re.I)
RULE_RE = re.compile(r"^\s*-{5,}\s*$")
# "12.1 text", "**12.1** text", "§ 6.2 text", "S1.2 text", "1. SERVICES" (OCR'd caps headings)
CLAUSE_NO_RE = re.compile(
    r"^\s*(?:\*\*)?(?P<no>(?:§\s*)?(?:S)?\d{1,2}(?:\.\d{1,2}){0,3})(?:\*\*)?[.)]?\s+(?P<rest>.+)$"
)
OCR_HEADING_RE = re.compile(r"^\s*\d{1,2}\.\s+[A-Z0-9][A-Z0-9 &,\-]{3,}$")
TABLE_RE = re.compile(r"^\s*\|")


@dataclass
class Clause:
    idx: int
    number: str | None      # e.g. "12.1" or None for unnumbered paragraphs
    heading: str            # nearest section heading, e.g. "12. RESTRICTIVE COVENANTS"
    text: str
    page: int | None
    line: int               # 1-based line in the Markdown source
    kind: str = "clause"    # clause | table | paragraph

    @property
    def ref(self) -> str:
        parts = []
        if self.number:
            n = self.number.replace("§", "").strip()
            parts.append(f"§{n}")
        elif self.heading:
            parts.append(self.heading)
        if self.number and self.heading:
            parts.append(f"({self.heading})")
        if self.page:
            parts.append(f"p.{self.page}")
        return " ".join(parts) if parts else f"line {self.line}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ref"] = self.ref
        return d


def _strip_md(s: str) -> str:
    return s.replace("**", "").strip()


def split_clauses(markdown: str) -> list[Clause]:
    lines = markdown.splitlines()
    clauses: list[Clause] = []
    heading = ""
    page = None
    has_footers = any(PAGE_FOOTER_RE.match(l) for l in lines)
    if has_footers:
        page = 1
    buf: list[str] = []
    buf_meta: dict = {}

    def flush():
        nonlocal buf, buf_meta
        text = "\n".join(buf).strip()
        if text:
            clauses.append(Clause(idx=len(clauses), number=buf_meta.get("number"), heading=heading,
                                  text=text, page=buf_meta.get("page"), line=buf_meta.get("line", 0),
                                  kind=buf_meta.get("kind", "paragraph")))
        buf, buf_meta = [], {}

    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        m = PAGE_MARK_RE.search(line)
        if m:
            flush()
            page = int(m.group(1))
            continue
        if PAGE_FOOTER_RE.match(line):
            flush()
            page = int(PAGE_FOOTER_RE.match(line).group(1)) + 1
            continue
        if RULE_RE.match(line):
            flush()
            continue
        hm = HEADING_RE.match(line)
        if hm:
            flush()
            heading = _strip_md(hm.group(2))
            continue
        if OCR_HEADING_RE.match(line):
            # OCR'd plain-text heading such as "6. RESTRICTIVE C0VENANT"
            flush()
            heading = _strip_md(line)
            continue
        if not line.strip():
            flush()
            continue
        if TABLE_RE.match(line):
            if buf_meta.get("kind") != "table":
                flush()
                buf_meta = {"kind": "table", "line": i, "page": page}
            buf.append(line)
            continue
        cm = CLAUSE_NO_RE.match(line)
        if cm and buf_meta.get("kind") != "table":
            flush()
            buf_meta = {"kind": "clause", "number": cm.group("no").replace("**", ""), "line": i, "page": page}
            buf.append(line)
            continue
        if buf_meta.get("kind") == "table":
            flush()
        if not buf:
            buf_meta = {"kind": "paragraph", "line": i, "page": page}
        buf.append(line)
    flush()
    return clauses


def section_of(clause: Clause) -> str:
    """Top-level clause number ("12" for "12.3") or the heading, used to group sibling clauses."""
    if clause.number:
        n = clause.number.replace("§", "").replace("S", "").strip()
        return n.split(".")[0]
    return clause.heading


def plain(text: str) -> str:
    """Markdown-light text for matching: no bold markers, collapsed whitespace."""
    t = text.replace("**", "").replace("\\", "")
    return re.sub(r"\s+", " ", t).strip()
