"""Built-in sample documents so the demo works with one click.

All content is invented. The receipt is rendered to a PNG at request time so
it goes through the real Tesseract OCR path, not the plain-text shortcut.
"""
from __future__ import annotations

import io

SAMPLE_TEXT = {
    "invoice": (
        "invoice.txt",
        "INVOICE\nInvoice Number: INV-2026-0417\nFrom: Northwind Supplies Ltd\n"
        "Invoice Date: 03/11/2026\nDue Date: 17/11/2026\nBill To: Beta Corp\n"
        "Subtotal: $1,200.00\nTotal: $1,320.00\n",
    ),
    "invoice-bad-amount": (
        "invoice-bad-amount.txt",
        "INVOICE\nInvoice Number: INV-2026-0418\nFrom: Northwind Supplies Ltd\n"
        "Invoice Date: 03/11/2026\nDue Date: 17/11/2026\nBill To: Beta Corp\n"
        "Subtotal: $1,200.00\nTotal: TBC\n",
    ),
    "cv": (
        "cv.txt",
        "Jane Doe\njane.doe@example.com\n+44 7911 123456\n\nEducation:\n"
        "MSc Artificial Intelligence, University of Example, 2023-2024\n\n"
        "Skills:\nPython, Machine Learning, Deep Learning, NLP, SQL\n",
    ),
}

RECEIPT_LINES = [
    "CORNER CAFE",
    "Receipt No: R-20931",
    "Date: 14/11/2026",
    "Latte x2        $9.00",
    "Muffin          $15.50",
    "Total: $24.50",
    "Thank you",
]


def render_png(lines: list[str], size: int = 28, scale: float = 1.0, blur: float = 0.0) -> bytes:
    """Render lines of text to a PNG. scale<1 and blur>0 degrade it to stress the OCR."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    font = ImageFont.load_default(size=size)
    img = Image.new("RGB", (900, 60 + len(lines) * (size + 14)), "white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((30, 30 + i * (size + 14)), line, fill="black", font=font)
    if scale != 1.0:
        w, h = img.size
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


SAMPLE_NAMES = [*SAMPLE_TEXT.keys(), "receipt-image"]


def get_sample(name: str) -> tuple[str, bytes]:
    if name in SAMPLE_TEXT:
        filename, text = SAMPLE_TEXT[name]
        return filename, text.encode()
    if name == "receipt-image":
        return "receipt.png", render_png(RECEIPT_LINES)
    raise KeyError(name)
