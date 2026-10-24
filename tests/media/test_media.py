"""Private media storage (original spatie/laravel-medialibrary usage), permission checked
downloads and ``media_prune_orphans`` (original OperationsCommandsTest media case)."""

from __future__ import annotations

import hashlib
import io
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.http import HttpRequest
from django.test import Client
from django.urls import include, path
from PIL import Image

from ninefruits.audit.models import ActivityLog
from ninefruits.media import services
from ninefruits.media.models import Media
from ninefruits.media.services import (
    IMAGES,
    PDF_AND_IMAGES,
    FileNameNotAllowed,
    FileTooBig,
    FileUnacceptableForCollection,
    MediaCollection,
    add_media,
    add_media_from_bytes,
    clear_collection,
    delete_media,
    header_safe_file_name,
    sanitize_file_name,
)
from ninefruits.media.views import PrivateMediaDownloadView
from ninefruits.security.models.user import User
from tests.audit.support import make_user

pytestmark = pytest.mark.django_db

PDF_BYTES = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def private_storage(settings: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "private"
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": str(root)}},
    }
    monkeypatch.setattr(
        User,
        "media_collections",
        {
            "photo": MediaCollection("photo", single_file=True, accepts=IMAGES),
            "documents": MediaCollection("documents", accepts=PDF_AND_IMAGES, max_size=1024),
        },
        raising=False,
    )
    return root


def test_stores_a_file_privately_with_its_checksum_and_sniffed_type(private_storage: Path) -> None:
    owner = make_user()
    upload = SimpleUploadedFile("Scan 2026#1.pdf", PDF_BYTES, content_type="image/png")

    media = add_media(owner, upload, "documents", custom_properties={"document_type_id": 3})

    media.refresh_from_db()
    assert (media.model_type, media.model_id, media.collection_name) == ("security.user", owner.pk, "documents")
    assert media.file_name == "Scan-2026-1.pdf"
    assert media.name == "Scan 2026#1"
    assert media.mime_type == "application/pdf"  # from the content, not the client
    assert media.size == len(PDF_BYTES)
    assert media.disk == "default"
    assert media.custom_property("document_type_id") == 3
    assert media.sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
    assert media.uuid is not None and media.order_column >= 1
    assert media.created_at is not None and media.created_at.tzinfo is not None
    assert (private_storage / str(media.pk) / "Scan-2026-1.pdf").read_bytes() == PDF_BYTES
    assert media.belongs_to(owner) and media.owner == owner
    assert "Scan" not in repr(media)


def test_keeps_only_the_latest_file_of_a_single_file_collection(private_storage: Path) -> None:
    owner = make_user()
    first = add_media_from_bytes(owner, png_bytes(), "a.png", "photo")
    second = add_media_from_bytes(owner, png_bytes(), "b.png", "photo")

    assert list(Media.objects.for_owner(owner, "photo")) == [second]
    assert not (private_storage / str(first.pk)).exists()
    assert second.order_column > first.order_column


def test_refuses_files_the_collection_does_not_accept() -> None:
    owner = make_user()

    with pytest.raises(FileUnacceptableForCollection):
        add_media_from_bytes(owner, PDF_BYTES, "photo.png", "photo")
    with pytest.raises(FileTooBig):
        add_media_from_bytes(owner, PDF_BYTES * 100, "big.pdf", "documents")
    with pytest.raises(FileNameNotAllowed):
        add_media_from_bytes(owner, png_bytes(), "shell.php.png", "photo")
    assert not Media.objects.exists()


def test_sanitizes_file_names_like_the_original() -> None:
    assert sanitize_file_name("my file\u0007.pdf") == "my-file.pdf"
    assert sanitize_file_name("../../etc/passwd") == "..-..-etc-passwd"
    assert header_safe_file_name('a"b\r\nc.pdf') == "abc.pdf"


def test_deletes_files_with_their_rows(private_storage: Path) -> None:
    owner = make_user()
    media = add_media_from_bytes(owner, PDF_BYTES, "a.pdf", "documents")
    other = add_media_from_bytes(owner, PDF_BYTES, "b.pdf", "documents")

    delete_media(media)
    assert not Media.objects.filter(pk=media.pk).exists()
    assert not (private_storage / str(media.pk)).exists()

    assert clear_collection(owner, "documents") == 1
    assert not (private_storage / str(other.pk)).exists()


class DocumentDownloadView(PrivateMediaDownloadView):
    def get_media(self, request: HttpRequest, **kwargs: Any) -> Media | None:
        media = Media.objects.filter(pk=kwargs["pk"]).first()
        if media is None:
            return None
        if media.model_id != request.user.pk and not request.user.has_perm("media_test.view"):
            raise PermissionDenied
        return media


class PhotoView(DocumentDownloadView):
    disposition = "inline"
    cache_control = "private, max-age=300"


urlpatterns = [
    path("accounts/", include("allauth.urls")),
    path("_test/media/<int:pk>", DocumentDownloadView.as_view()),
    path("_test/photo/<int:pk>", PhotoView.as_view()),
]


@pytest.mark.urls(__name__)
def test_downloads_go_through_the_permission_check(client: Client, grant: Any) -> None:
    owner = make_user()
    media = add_media_from_bytes(owner, PDF_BYTES, 'report"x.pdf', "documents")

    assert client.get(f"/_test/media/{media.pk}").status_code == 302  # sign in first

    client.force_login(make_user())
    assert client.get(f"/_test/media/{media.pk}").status_code == 403

    client.force_login(owner)
    response = client.get(f"/_test/media/{media.pk}")
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == PDF_BYTES
    assert response["Content-Type"] == "application/pdf"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Cache-Control"] == "private, no-store"
    assert response["Content-Disposition"] == 'attachment; filename="reportx.pdf"'

    assert client.get("/_test/media/999999").status_code == 404


@pytest.mark.urls(__name__)
def test_inline_downloads(client: Client) -> None:
    owner = make_user()
    media = add_media_from_bytes(owner, png_bytes(), "me.png", "photo")
    client.force_login(owner)

    response = client.get(f"/_test/photo/{media.pk}")
    assert response["Content-Disposition"] == 'inline; filename="me.png"'
    assert response["Cache-Control"] == "private, max-age=300"


def test_removes_orphan_media_rows_and_directories(private_storage: Path) -> None:
    owner = make_user()
    media = add_media_from_bytes(owner, png_bytes(), "me.png", "photo")
    (private_storage / "999999").mkdir()
    (private_storage / "999999" / "ghost.png").write_bytes(b"y")
    Media.objects.filter(pk=media.pk).update(model_id=999999999)

    out = StringIO()
    assert call_command("media_prune_orphans", dry_run=True, stdout=out) == 0
    assert "Dry run: 1 orphan row(s), 1 orphan director(ies)." in out.getvalue()
    assert Media.objects.count() == 1

    out = StringIO()
    assert call_command("media_prune_orphans", stdout=out) == 0
    assert "1 orphan row(s), 1 orphan director(ies)." in out.getvalue()
    assert Media.objects.count() == 0
    assert not (private_storage / "999999").exists()
    assert not (private_storage / str(media.pk)).exists()

    run = ActivityLog.objects.filter(properties__command="media_prune_orphans").latest("id")
    assert run.properties["result"] == {"rows": 1, "directories": 1}


def test_treats_unknown_owner_types_as_orphans() -> None:
    owner = make_user()
    media = add_media_from_bytes(owner, png_bytes(), "me.png", "photo")
    Media.objects.filter(pk=media.pk).update(model_type="App\\Models\\Person\\Person")

    assert services.prune_orphans(dry_run=True).rows == 1
