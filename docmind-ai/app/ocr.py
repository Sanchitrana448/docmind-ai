"""
Text extraction layer: native PDF text extraction when available (fast, 100%
accurate), OCR fallback via Tesseract for scanned/image documents.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List


@dataclass
class Word:
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int


@dataclass
class OCRResult:
    text: str
    words: List[Word]
    method: str  # "native_pdf" | "tesseract_ocr" | "plain_text"
    mean_confidence: float


def extract_from_pdf(content: bytes) -> OCRResult:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    native_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    if native_text.strip() and len(native_text.strip()) > 20:
        # Native text layer present — no OCR needed, 100% confidence.
        return OCRResult(text=native_text, words=[], method="native_pdf", mean_confidence=1.0)

    # No usable text layer -> rasterize pages and OCR them.
    try:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(content, dpi=200)
    except Exception as e:
        raise RuntimeError(f"Could not rasterize PDF for OCR: {e}")

    return _ocr_images(images)


def extract_from_image(content: bytes) -> OCRResult:
    from PIL import Image

    img = Image.open(io.BytesIO(content))
    return _ocr_images([img])


def _ocr_images(images) -> OCRResult:
    import pytesseract

    all_text = []
    all_words: List[Word] = []
    confidences = []
    for img in images:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        page_text_parts = []
        for i in range(len(data["text"])):
            word = data["text"][i].strip()
            conf = float(data["conf"][i]) if str(data["conf"][i]).lstrip("-").isdigit() else -1.0
            if word:
                page_text_parts.append(word)
                if conf >= 0:
                    confidences.append(conf)
                    all_words.append(
                        Word(
                            text=word,
                            confidence=conf / 100.0,
                            left=data["left"][i],
                            top=data["top"][i],
                            width=data["width"][i],
                            height=data["height"][i],
                        )
                    )
        all_text.append(" ".join(page_text_parts))

    mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return OCRResult(text="\n".join(all_text), words=all_words, method="tesseract_ocr", mean_confidence=round(mean_conf, 3))


def extract_text(filename: str, content: bytes) -> OCRResult:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_from_pdf(content)
    if lower.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        return extract_from_image(content)
    # Plain text / markdown
    return OCRResult(text=content.decode("utf-8", errors="ignore"), words=[], method="plain_text", mean_confidence=1.0)
