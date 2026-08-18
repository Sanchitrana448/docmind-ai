from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .pipeline import ProcessedDocument, process_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docmind")

app = FastAPI(
    title="DocMind AI",
    description="Multimodal document intelligence — OCR, classification, structured extraction with confidence scoring and human review.",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DOCS: dict[str, ProcessedDocument] = {}
STATIC_DIR = Path(__file__).parent.parent / "frontend"


class ReviewRequest(BaseModel):
    field_name: str
    corrected_value: str


@app.get("/health")
def health():
    return {"status": "ok", "processed_documents": len(DOCS)}


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    try:
        result = process_document(file.filename, content)
    except Exception as e:
        logger.exception("processing failed")
        raise HTTPException(500, f"Processing failed: {e}")
    DOCS[result.id] = result
    return asdict(result)


@app.get("/documents")
def list_documents():
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "doc_type": d.doc_type,
            "needs_review": d.needs_review,
            "created_at": d.created_at,
        }
        for d in DOCS.values()
    ]


@app.get("/documents/{doc_id}")
def get_document(doc_id: str):
    doc = DOCS.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return asdict(doc)


@app.post("/documents/{doc_id}/review")
def submit_review(doc_id: str, review: ReviewRequest):
    doc = DOCS.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    doc.corrections[review.field_name] = review.corrected_value
    for f in doc.fields:
        if f["name"] == review.field_name:
            f["value"] = review.corrected_value
            f["confidence"] = 1.0  # human-verified
    doc.needs_review = any(f["confidence"] < 0.55 for f in doc.fields) or bool(doc.validation_warnings)
    return asdict(doc)


@app.get("/", response_class=HTMLResponse)
def index_page():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>DocMind AI</h1><p>Frontend not built. See /docs for API.</p>"
