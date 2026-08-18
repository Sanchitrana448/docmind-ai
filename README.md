# DocMind AI

**Multimodal document intelligence platform.** Upload an invoice, CV, contract, or receipt (PDF, scanned image, or plain text) and get back structured, field-level data with per-field confidence scores, validation warnings, and a human-review loop for anything the system isn't sure about.

Uses **real OCR** (Tesseract + Poppler) for scanned documents, and native PDF text extraction (instant, 100% accurate) whenever a text layer is already present — no unnecessary OCR calls.

## Why this project exists

Document AI is one of the highest-value, most commonly interviewed-for AI engineering domains (invoice processing, KYC, resume parsing, contract review). This project demonstrates the full production pattern: extraction → confidence scoring → validation → human-in-the-loop correction, not just "run OCR and hope."

## Pipeline

```
Upload
  │
  ▼
Text extraction   → native PDF text layer, OR Tesseract OCR for scans/images
  │
  ▼
Classification    → rule-based document-type classifier (invoice/CV/contract/receipt/...)
  │
  ▼
Field extraction   → type-specific regex/heuristic extractors
  │
  ▼
Validation           → sanity-checks dates, amounts
  │
  ▼
Confidence scoring     → per-field + OCR-level confidence
  │
  ▼
Human review flag        → low-confidence documents routed for correction
  │
  ▼
Correction feedback loop   → POST /documents/{id}/review persists human corrections
```

## Run it

```bash
# System deps (already present in the Docker image):
#   sudo apt-get install tesseract-ocr poppler-utils
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000
```

Docker (includes OCR system deps):

```bash
docker build -t docmind .
docker run -p 8000:8000 docmind
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/documents` | Upload & process a document (pdf/png/jpg/txt) |
| `GET` | `/documents/{id}` | Fetch full extraction result |
| `POST` | `/documents/{id}/review` | Submit a human correction for a field |
| `GET` | `/health` | Liveness check |

## Verified behavior

Tested end-to-end against a real generated receipt image: Tesseract OCR correctly read the merchant name and date, but misread `$24.50` as `$2450` (a genuine OCR artifact — dropped decimal point). The pipeline's own validator caught the malformed amount, set `needs_review: true`, and the `/review` endpoint successfully accepted and applied the human correction, boosting the field's confidence to 100%. This is exactly the "trust but verify" behavior expected of production document AI — it doesn't quietly ship a wrong number.

## Tests

```bash
pytest tests/ -v
```

7/7 tests covering classification (invoice/CV/unknown), field extraction (invoice numbers, CV emails/names), and end-to-end pipeline behavior including the low-confidence review flag.

## Tech stack

Python · FastAPI · Tesseract OCR · pdf2image/Poppler · pypdf · Pillow · Docker · pytest.

## Case study (recruiter summary)

**Problem:** Manual document data entry is slow and OCR-only pipelines silently ship errors.
**Approach:** Built a classify → extract → validate → confidence-score → human-review pipeline with per-field provenance, tested against real scanned-image OCR (not just clean text).
**Result (measured, this repo):** 7/7 automated tests passing; live OCR smoke test correctly flagged a real digit-drop OCR error for human review instead of silently accepting it.
**What I'd do next:** replace regex extractors with a fine-tuned layout-aware model (LayoutLM/Donut), add bounding-box visualization in the frontend, and support batch processing with a task queue (Redis/Celery) for production throughput.
