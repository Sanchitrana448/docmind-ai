# DocMind AI

[![tests](https://github.com/Sanchitrana448/docmind-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Sanchitrana448/docmind-ai/actions/workflows/ci.yml)

Live: https://docmind-ai-8uct.onrender.com  
*(free tier, so it may take ~50s to wake outside weekday daytime)*

Upload an invoice, CV, contract or receipt (PDF, scan, or plain text) and get structured fields back, each with its own confidence score and the snippet it came from.

## Why the confidence scores matter

While testing this against a generated receipt image, Tesseract read `$24.50` as `$2450`. A dropped decimal point, which is one of the most common and most expensive OCR failures, because the output is still a perfectly valid-looking number.

The pipeline caught it. The amount validator saw a malformed value, set `needs_review: true`, and routed the document to the correction endpoint instead of returning it as clean data. Posting the corrected value to `/documents/{id}/review` overwrote the field and bumped its confidence to 1.0 as human-verified.

That behaviour is the whole point of the project. Extraction accuracy is a solved-ish problem; knowing when you got it wrong is not. A pipeline that silently returns `$2450` is worse than one that refuses to answer.

## How it works

Text extraction picks a strategy per file:

- PDF with a text layer, use it directly. No OCR, instant, exact.
- PDF without one, rasterize at 200 DPI via Poppler, then OCR.
- Image, straight to Tesseract.
- Anything else, decode as UTF-8.

Then classification (keyword scoring across invoice / CV / contract / receipt / report / form), type-specific field extraction, validation, confidence scoring, and a review flag if anything looks off.

Confidence is per field, not per document. `email` extracted by regex scores 0.95; `merchant` guessed from the first line of a receipt scores 0.4, because that heuristic is genuinely weak and the score should say so.

## Running it

Needs Tesseract and Poppler on the system:

```bash
sudo apt-get install tesseract-ocr poppler-utils
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Docker already includes both:

```bash
docker build -t docmind .
docker run -p 8000:8000 docmind
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/documents` | Upload and process |
| `GET` | `/documents` | List processed documents |
| `GET` | `/documents/{id}` | Full extraction result |
| `POST` | `/documents/{id}/review` | Submit a human correction |
| `GET` | `/health` | Liveness |

## Review flag logic

A document gets `needs_review: true` if any of these hold:

- any field scored below 0.55
- a validator produced a warning (non-numeric amount, date with no digits)
- mean OCR confidence came in under 0.6 and the text came from Tesseract rather than a native text layer

That last condition only applies to OCR'd documents. A native PDF text layer is exact, so scoring it against an OCR confidence threshold would flag clean documents for no reason.

## Tests

```bash
pytest tests/ -v
```

Seven tests covering classification (invoice, CV, and a gibberish input that should come back `unknown` with 0.0 confidence), field extraction for invoices and CVs, the end-to-end path on plain text, and the low-confidence review flag firing when it should.

## Limitations

- Extractors are regex and heuristics, so they're brittle on unusual layouts. A layout-aware model (LayoutLM, Donut) is the real answer and is what I'd build next.
- No bounding-box output in the UI. The OCR layer already collects per-word boxes in `ocr.py`, they just aren't drawn.
- Everything is in memory, so processed documents don't survive a restart.
- Single-document, synchronous. Batch throughput would need a task queue.
- The date validator only checks that a date contains a digit. It is not a real date parser.

## Stack

Python, FastAPI, Tesseract via pytesseract, pdf2image/Poppler, pypdf, Pillow, Docker, pytest.
