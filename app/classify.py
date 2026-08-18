"""Rule-based document classifier.

Deterministic keyword/pattern scoring per document type. Swappable for a
trained text classifier later (interface: classify(text) -> (label, confidence)).
"""
from __future__ import annotations

import re

DOCUMENT_TYPES = ["invoice", "cv_resume", "contract", "receipt", "report", "form", "unknown"]

_SIGNALS = {
    "invoice": [r"\binvoice\b", r"\binvoice\s*(no|#|number)\b", r"\bbill\s*to\b", r"\bdue\s*date\b", r"\bsubtotal\b"],
    "cv_resume": [r"\bcurriculum\s*vitae\b", r"\bresume\b", r"\bwork\s*experience\b", r"\beducation\b", r"\bskills\b", r"\breferences\b"],
    "contract": [r"\bagreement\b", r"\bparties\b", r"\bwhereas\b", r"\bterms\s*and\s*conditions\b", r"\bhereby\b", r"\beffective\s*date\b"],
    "receipt": [r"\breceipt\b", r"\bthank\s*you\s*for\s*your\s*purchase\b", r"\bchange\s*due\b", r"\bcashier\b", r"\btotal\b"],
    "report": [r"\bexecutive\s*summary\b", r"\bfindings\b", r"\bmethodology\b", r"\bconclusion\b"],
    "form": [r"\bplease\s*(complete|fill)\b", r"\bsignature\b", r"\bapplicant\b", r"\bdate\s*of\s*birth\b"],
}


def classify(text: str) -> tuple[str, float]:
    t = text.lower()
    scores = {}
    for doc_type, patterns in _SIGNALS.items():
        hits = sum(1 for p in patterns if re.search(p, t))
        scores[doc_type] = hits / len(patterns)

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    if best_score == 0:
        return "unknown", 0.0
    return best_type, round(min(1.0, best_score + 0.15), 3)
