"""Local BM25 search over clauses, notes and tracker rows. Runs entirely on this machine."""
from __future__ import annotations

import math
import re
from collections import Counter

STOP = set("""a an and are as at be by for from has have if in into is it its of on or that the their this to was were will with
shall may any all such other which what does do did we our us you your there about than then these those not no can""".split())


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", text.lower())
    return [t for t in toks if t not in STOP and len(t) > 1]


class Index:
    def __init__(self):
        self.items: list[dict] = []
        self.tfs: list[Counter] = []
        self.df: Counter = Counter()
        self.avgdl = 1.0

    def build(self, items: list[dict]):
        self.items = items
        self.tfs = [Counter(tokenize(it["text"] + " " + it.get("context", ""))) for it in items]
        self.df = Counter()
        for tf in self.tfs:
            self.df.update(tf.keys())
        self.avgdl = sum(sum(tf.values()) for tf in self.tfs) / max(1, len(self.tfs))

    def search(self, query: str, k: int = 8, doc_ids: set[str] | None = None, kinds: set[str] | None = None,
               k1: float = 1.4, b: float = 0.7) -> list[dict]:
        q = tokenize(query)
        if not q:
            return []
        N = len(self.items)
        scored = []
        for i, (it, tf) in enumerate(zip(self.items, self.tfs)):
            if doc_ids and it.get("doc_id") not in doc_ids:
                continue
            if kinds and it.get("kind") not in kinds:
                continue
            dl = sum(tf.values()) or 1
            s, matched = 0.0, []
            for t in set(q):
                f = tf.get(t)
                if not f:
                    continue
                idf = math.log(1 + (N - self.df[t] + 0.5) / (self.df[t] + 0.5))
                s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self.avgdl))
                matched.append(t)
            if s > 0:
                scored.append((s, i, matched))
        scored.sort(reverse=True)
        out = []
        for s, i, matched in scored[:k]:
            out.append({**self.items[i], "score": round(s, 3), "matched_terms": matched,
                        "coverage": round(len(set(matched)) / len(set(q)), 2)})
        return out
