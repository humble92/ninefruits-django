"""Helpers of the admission tests."""

from __future__ import annotations

from typing import Any

PDF_BYTES = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


def fake_pdf(name: str = "diploma.pdf") -> Any:
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")
