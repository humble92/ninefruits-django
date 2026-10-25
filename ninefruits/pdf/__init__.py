"""PDF rendering through Gotenberg (Chromium), original ``App\\Support\\Pdf`` and ADR 0004.

    from ninefruits.pdf import PdfOptions, get_renderer

    pdf: bytes = get_renderer().render_template("pdf/sample.html", {...}, PdfOptions(landscape=True))

Templates extend ``pdf/layout.html`` (fonts: Noto Sans CJK KR/SC, Noto Sans Lao, Noto Sans, all
installed in the Gotenberg image).
"""

from ninefruits.pdf.options import PdfOptions
from ninefruits.pdf.renderer import GotenbergPdfRenderer, PdfRenderer, PdfRenderingError, get_renderer

__all__ = ["GotenbergPdfRenderer", "PdfOptions", "PdfRenderer", "PdfRenderingError", "get_renderer"]
