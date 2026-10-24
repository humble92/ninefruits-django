"""HTML to PDF (original ``PdfRenderer`` and ``GotenbergPdfRenderer``). Chromium based so that mixed
Korean, Chinese, Lao and Latin text uses the same fonts as the browser (ADR 0004)."""

from __future__ import annotations

from typing import Any, Protocol

import httpx
from django.conf import settings
from django.template.loader import render_to_string

from ninefruits.pdf.options import PdfOptions

CONVERT_HTML_ROUTE = "/forms/chromium/convert/html"


class PdfRenderingError(RuntimeError):
    """Gotenberg did not return a PDF (unreachable, timed out or an error status)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PdfRenderer(Protocol):
    def render(self, html: str, options: PdfOptions | None = None) -> bytes: ...

    def render_template(
        self, template_name: str, context: dict[str, Any] | None = None, options: PdfOptions | None = None
    ) -> bytes: ...


class GotenbergPdfRenderer:
    """Sends the HTML as ``index.html`` to Gotenberg's Chromium route and returns the PDF bytes."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None, client: httpx.Client | None = None):
        self.base_url = (base_url or settings.GOTENBERG_URL).rstrip("/")
        self.timeout = float(timeout if timeout is not None else getattr(settings, "GOTENBERG_TIMEOUT", 60))
        self.client = client

    def render(self, html: str, options: PdfOptions | None = None) -> bytes:
        options = options or PdfOptions()
        files = {"files": ("index.html", html.encode("utf-8"), "text/html; charset=utf-8")}
        try:
            if self.client is not None:
                response = self.client.post(
                    self.base_url + CONVERT_HTML_ROUTE,
                    data=options.to_gotenberg_fields(),
                    files=files,
                    timeout=self.timeout,
                )
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.base_url + CONVERT_HTML_ROUTE, data=options.to_gotenberg_fields(), files=files
                    )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise PdfRenderingError(
                f"Gotenberg returned HTTP {error.response.status_code}.", error.response.status_code
            ) from error
        except httpx.HTTPError as error:
            raise PdfRenderingError(f"Gotenberg request failed: {type(error).__name__}.") from error
        return response.content

    def render_template(
        self, template_name: str, context: dict[str, Any] | None = None, options: PdfOptions | None = None
    ) -> bytes:
        return self.render(render_to_string(template_name, context or {}), options)


def get_renderer() -> PdfRenderer:
    """The configured renderer (``PDF_RENDERER`` dotted path, default Gotenberg)."""
    path = getattr(settings, "PDF_RENDERER", None)
    if path:
        from django.utils.module_loading import import_string

        renderer: PdfRenderer = import_string(path)()
        return renderer
    return GotenbergPdfRenderer()
