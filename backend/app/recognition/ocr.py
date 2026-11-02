"""OCR signal (RapidOCR, ONNX, CPU): how much readable text a photo contains, plus a snippet for search."""
from __future__ import annotations




TEXT_KEYWORDS = ("text", "caption", "document", "receipt", "invoice", "note", "slide", "chart", "meme", "screenshot",
                 "ticket", "quote", "whiteboard")


def text_category(categories: list[dict]) -> list[dict]:
    """Categories in a set that are about text (documents, captions, screenshots…)."""
    return [c for c in categories if c["id"] == "ids" or any(k in f"{c['id']} {c['name']}".lower() for k in TEXT_KEYWORDS)]
