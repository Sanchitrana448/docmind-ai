"""Field-level extraction, dispatched on document type.

Fields carry {value, confidence, source_snippet} rather than a bare value. The
snippet is what makes a low score actionable: a reviewer can see the text the
guess came from and correct it in one pass, instead of re-reading the document
to work out where the number came from.

Confidence is per field on purpose. A regex-matched email and a merchant name
guessed from the first line of a receipt are not equally trustworthy, and one
document-level score would hide that.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Field:
    name: str
    value: Optional[str]
    confidence: float
    source_snippet: str = ""


DATE_RE = r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})"
MONEY_RE = r"[£$€]\s?[\d,]+\.\d{2}|\b[\d,]+\.\d{2}\s?(?:GBP|USD|EUR)\b"
EMAIL_RE = r"[\w\.\-+]+@[\w\-]+\.[\w\.\-]+"
PHONE_RE = r"(\+?\d[\d\s\-\(\)]{7,}\d)"


def _find(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[re.Match]:
    return re.search(pattern, text, flags)


def _field_from_match(name: str, match: Optional[re.Match], base_conf: float = 0.85) -> Field:
    if not match:
        return Field(name=name, value=None, confidence=0.0)
    return Field(name=name, value=match.group(0).strip(), confidence=base_conf, source_snippet=match.group(0))


def extract_invoice(text: str) -> list[Field]:
    fields = []
    inv_num = _find(r"invoice\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{2,19})", text)
    fields.append(Field("invoice_number", inv_num.group(1) if inv_num else None, 0.8 if inv_num else 0.0))
    fields.append(_field_from_match("invoice_date", _find(DATE_RE, text)))
    vendor = _find(r"(?:from|vendor|company)\s*[:\-]?\s*([A-Z][A-Za-z0-9&,\. ]{2,40})", text)
    fields.append(Field("vendor", vendor.group(1).strip() if vendor else None, 0.55 if vendor else 0.0))
    totals = re.findall(MONEY_RE, text)
    fields.append(Field("total_amount", totals[-1] if totals else None, 0.75 if totals else 0.0))
    due = _find(r"due\s*date\s*[:\-]?\s*" + DATE_RE, text)
    fields.append(_field_from_match("due_date", due, 0.7))
    return fields


def extract_cv(text: str) -> list[Field]:
    fields = []
    fields.append(_field_from_match("email", _find(EMAIL_RE, text), 0.95))
    fields.append(_field_from_match("phone", _find(PHONE_RE, text), 0.6))
    name_match = re.match(r"\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})", text.strip())
    fields.append(Field("candidate_name", name_match.group(1) if name_match else None, 0.5 if name_match else 0.0))
    skills_block = _find(r"skills\s*[:\-]?\s*(.{0,300})", text, re.IGNORECASE | re.DOTALL)
    fields.append(Field("skills_snippet", skills_block.group(1).strip()[:200] if skills_block else None, 0.5 if skills_block else 0.0))
    edu_block = _find(r"education\s*[:\-]?\s*(.{0,200})", text, re.IGNORECASE | re.DOTALL)
    fields.append(Field("education_snippet", edu_block.group(1).strip()[:200] if edu_block else None, 0.5 if edu_block else 0.0))
    return fields


def extract_contract(text: str) -> list[Field]:
    fields = []
    fields.append(_field_from_match("effective_date", _find(r"effective\s*date\s*[:\-]?\s*" + DATE_RE, text), 0.75))
    parties = re.findall(r"between\s+([A-Z][A-Za-z0-9&,\. ]{2,40})\s+and\s+([A-Z][A-Za-z0-9&,\. ]{2,40})", text)
    if parties:
        fields.append(Field("party_a", parties[0][0].strip(), 0.6))
        fields.append(Field("party_b", parties[0][1].strip(), 0.6))
    else:
        fields.append(Field("party_a", None, 0.0))
        fields.append(Field("party_b", None, 0.0))
    term = _find(r"term\s*of\s*(\d+\s*(?:day|month|year)s?)", text, re.IGNORECASE)
    fields.append(_field_from_match("term_length", term, 0.6))
    return fields


def extract_receipt(text: str) -> list[Field]:
    fields = []
    fields.append(_field_from_match("date", _find(DATE_RE, text)))
    totals = re.findall(MONEY_RE, text)
    fields.append(Field("total_amount", totals[-1] if totals else None, 0.8 if totals else 0.0))
    merchant_match = re.match(r"\s*([A-Z][A-Za-z0-9&,\. ]{2,40})", text.strip())
    fields.append(Field("merchant", merchant_match.group(1).strip() if merchant_match else None, 0.4 if merchant_match else 0.0))
    return fields


def extract_generic(text: str) -> list[Field]:
    fields = []
    fields.append(_field_from_match("first_date_found", _find(DATE_RE, text), 0.6))
    fields.append(_field_from_match("first_email_found", _find(EMAIL_RE, text), 0.7))
    fields.append(_field_from_match("first_amount_found", _find(MONEY_RE, text), 0.6))
    return fields


EXTRACTORS = {
    "invoice": extract_invoice,
    "cv_resume": extract_cv,
    "contract": extract_contract,
    "receipt": extract_receipt,
}


def extract_fields(doc_type: str, text: str) -> list[Field]:
    fn = EXTRACTORS.get(doc_type, extract_generic)
    return fn(text)
