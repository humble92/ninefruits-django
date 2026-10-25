"""Page setup (original ``App\\Support\\Pdf\\PdfOptions``). Sizes in inches (A4 by default), as
Chromium expects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfOptions:
    paper_width: float = 8.27
    paper_height: float = 11.69
    margin: float = 0.6
    landscape: bool = False

    def to_gotenberg_fields(self) -> dict[str, str]:
        margin = _number(self.margin)
        return {
            "paperWidth": _number(self.paper_width),
            "paperHeight": _number(self.paper_height),
            "marginTop": margin,
            "marginBottom": margin,
            "marginLeft": margin,
            "marginRight": margin,
            "landscape": "true" if self.landscape else "false",
            "printBackground": "true",
        }


def _number(value: float) -> str:
    """PHP ``(string) 8.27`` -> ``"8.27"``, ``(string) 1.0`` -> ``"1"``."""
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text
