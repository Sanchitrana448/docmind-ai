import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.classify import classify
from app.extractors import extract_invoice, extract_cv
from app.pipeline import process_document

INVOICE_TEXT = """
INVOICE
Invoice Number: INV-2024-0091
From: Acme Supplies Ltd
Invoice Date: 12/03/2024
Due Date: 26/03/2024
Bill To: Beta Corp
Subtotal: $1,200.00
Total: $1,320.00
"""

CV_TEXT = """
Jane Doe
jane.doe@example.com
+44 7911 123456

Education:
MSc Artificial Intelligence, University of Example, 2023-2024

Skills:
Python, Machine Learning, Deep Learning, NLP, SQL
"""


def test_classify_invoice():
    label, conf = classify(INVOICE_TEXT)
    assert label == "invoice"
    assert conf > 0


def test_classify_cv():
    label, conf = classify(CV_TEXT)
    assert label == "cv_resume"


def test_classify_unknown_for_gibberish():
    label, conf = classify("asdkjh aslkdj alskdj")
    assert label == "unknown"
    assert conf == 0.0


def test_extract_invoice_fields():
    fields = {f.name: f.value for f in extract_invoice(INVOICE_TEXT)}
    assert fields["invoice_number"] == "INV-2024-0091"
    assert fields["total_amount"] == "$1,320.00"
    assert fields["invoice_date"] is not None


def test_extract_cv_fields():
    fields = {f.name: f.value for f in extract_cv(CV_TEXT)}
    assert fields["email"] == "jane.doe@example.com"
    assert fields["candidate_name"] == "Jane Doe"


def test_process_document_plain_text_invoice():
    doc = process_document("invoice.txt", INVOICE_TEXT.encode("utf-8"))
    assert doc.doc_type == "invoice"
    assert doc.ocr_method == "plain_text"
    field_map = {f["name"]: f["value"] for f in doc.fields}
    assert field_map["invoice_number"] == "INV-2024-0091"


def test_process_document_flags_low_confidence_for_review():
    sparse_text = "This document contains almost nothing useful.".encode("utf-8")
    doc = process_document("mystery.txt", sparse_text)
    assert doc.doc_type == "unknown"
    assert doc.needs_review is True


def test_invoice_total_uses_total_line_not_subtotal():
    text = "INVOICE\nInvoice Number: INV-1\nSubtotal: $100.00\nTotal: $110.00\nDue Date: 01/12/2026\n"
    fields = {f.name: f for f in extract_invoice(text)}
    assert fields["total_amount"].value == "$110.00"
    assert fields["due_date"].value == "01/12/2026"


def test_missing_total_is_not_replaced_by_subtotal_and_goes_to_review():
    text = "INVOICE\nInvoice Number: INV-1\nInvoice Date: 03/11/2026\nSubtotal: $100.00\nTotal: TBC\n"
    result = process_document("inv.txt", text.encode())
    fields = {f["name"]: f for f in result.fields}
    assert fields["total_amount"]["value"] is None
    assert result.needs_review


def test_dropped_decimal_total_is_flagged_for_review():
    text = "INVOICE\nInvoice Number: INV-1\nInvoice Date: 03/11/2026\nTotal: $2450\n"
    result = process_document("inv.txt", text.encode())
    assert result.needs_review


def test_cv_name_field_is_not_validated_as_a_date():
    result = process_document("cv.txt", CV_TEXT.encode())
    assert not any("candidate_name" in w for w in result.validation_warnings)


def test_sample_endpoints_and_review_roundtrip():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    doc = client.post("/samples/invoice-bad-amount").json()
    assert doc["needs_review"]
    fixed = client.post(f"/documents/{doc['id']}/review", json={"field_name": "total_amount", "corrected_value": "$1,320.00"}).json()
    amount = next(f for f in fixed["fields"] if f["name"] == "total_amount")
    assert amount["confidence"] == 1.0 and amount["value"] == "$1,320.00"
    assert client.post("/samples/nope").status_code == 404
