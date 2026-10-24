"""``pdf_sample``: renders a mixed Korean, Chinese, Lao and English sample to check PDF fonts
(original ``pdf:sample``)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import CommandParser
from django.utils import timezone

from ninefruits.core.commands import StatusCommand
from ninefruits.pdf import PdfRenderingError, get_renderer


class Command(StatusCommand):
    help = "Render a mixed Korean, Chinese, Lao and English sample to check PDF fonts"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "path",
            nargs="?",
            default="pdf-sample.pdf",
            help="Path in the private file storage (default pdf-sample.pdf)",
        )

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]
        path: str = options["path"]
        try:
            pdf = get_renderer().render_template("pdf/sample.html", {"issued_on": timezone.localdate()})
        except PdfRenderingError as error:
            self.error(str(error))
            return self.FAILURE
        try:
            if default_storage.exists(path):
                default_storage.delete(path)
            name = default_storage.save(path, ContentFile(pdf))
        except SuspiciousFileOperation:
            self.error(f"[{path}] is outside the private file storage.")
            return self.FAILURE
        self.info(f"Written to {default_storage.path(name)}")
        return self.SUCCESS
