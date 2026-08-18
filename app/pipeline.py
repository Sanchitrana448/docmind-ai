from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional

from . import classify, extractors, ocr

LOW_CONFIDENCE_THRESHOLD = 0.55


@dataclass
class ProcessedDocument:
    id: str
    filename: str
    doc_type: str
    doc_type_confidence: float
    ocr_method: str
    ocr_confidence: float
    fields: List[dict]
    validation_warnings: List[str]
    needs_review: bool
    corrections: dict = field(default_factory=dict)
    raw_text_preview: str = ""
    created_at: float = field(default_factory=time.time)


def _validate(fields: List[extractors.Field]) -> List[str]:
    warnings = []
    for f in fields:
        if f.value is None:
            continue
        if "date" in f.name and f.value:
            # very light sanity check — not a full date parser
            if not any(ch.isdigit() for ch in f.value):
                warnings.append(f"Field '{f.name}' does not look like a valid date: '{f.value}'")
        if "amount" in f.name and f.value:
            digits = "".join(ch for ch in f.value if ch.isdigit() or ch == ".")
            if not digits:
                warnings.append(f"Field '{f.name}' does not contain a numeric amount: '{f.value}'")
    return warnings


def process_document(filename: str, content: bytes) -> ProcessedDocument:
    ocr_result = ocr.extract_text(filename, content)
    doc_type, type_conf = classify.classify(ocr_result.text)
    fields = extractors.extract_fields(doc_type, ocr_result.text)
    warnings = _validate(fields)

    low_conf_fields = [f for f in fields if f.confidence < LOW_CONFIDENCE_THRESHOLD]
    needs_review = bool(low_conf_fields) or bool(warnings) or ocr_result.mean_confidence < 0.6 and ocr_result.method == "tesseract_ocr"

    return ProcessedDocument(
        id=str(uuid.uuid4())[:10],
        filename=filename,
        doc_type=doc_type,
        doc_type_confidence=type_conf,
        ocr_method=ocr_result.method,
        ocr_confidence=ocr_result.mean_confidence,
        fields=[asdict(f) for f in fields],
        validation_warnings=warnings,
        needs_review=needs_review,
        raw_text_preview=ocr_result.text[:600],
    )
