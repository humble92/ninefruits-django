"""Port of tests/Feature/Pdf/PdfRenderingTest.php (Gotenberg, ADR 0004)."""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pytest
import respx
from django.conf import settings
from django.core.management import call_command

from ninefruits.pdf import GotenbergPdfRenderer, PdfOptions, PdfRenderingError, get_renderer

CONVERT = f"{settings.GOTENBERG_URL.rstrip('/')}/forms/chromium/convert/html"


def _fields(request: httpx.Request) -> dict[str, str]:
    """Multipart form fields of the request (text parts and the HTML file)."""
    body = request.content
    boundary = request.headers["Content-Type"].split("boundary=")[1].encode()
    fields = {}
    for part in body.split(b"--" + boundary):
        if b"\r\n\r\n" not in part:
            continue
        head, _sep, value = part.partition(b"\r\n\r\n")
        name = head.split(b'name="')[1].split(b'"')[0].decode()
        fields[name] = value.rstrip(b"\r\n").decode("utf-8")
    return fields


@respx.mock
def test_sends_html_and_page_setup_to_gotenberg() -> None:
    route = respx.post(CONVERT).mock(return_value=httpx.Response(200, content=b"%PDF-1.7 fake"))

    pdf = get_renderer().render("<p>자료구조</p>", PdfOptions(landscape=True))

    assert pdf == b"%PDF-1.7 fake"
    fields = _fields(route.calls.last.request)
    assert fields["files"] == "<p>자료구조</p>"
    assert fields["landscape"] == "true"
    assert fields["paperWidth"] == "8.27"
    assert fields["paperHeight"] == "11.69"
    assert fields["marginTop"] == fields["marginLeft"] == "0.6"
    assert fields["printBackground"] == "true"
    assert b'filename="index.html"' in route.calls.last.request.content


def test_page_options() -> None:
    assert PdfOptions(margin=1).to_gotenberg_fields()["marginBottom"] == "1"
    assert PdfOptions().to_gotenberg_fields()["landscape"] == "false"


@respx.mock
def test_fails_loudly_when_rendering_fails() -> None:
    respx.post(CONVERT).mock(return_value=httpx.Response(500, content=b"error"))

    with pytest.raises(PdfRenderingError) as error:
        get_renderer().render("<p>x</p>")
    assert error.value.status_code == 500


@respx.mock
def test_fails_loudly_when_gotenberg_is_unreachable() -> None:
    respx.post(CONVERT).mock(side_effect=httpx.ConnectTimeout("timed out"))

    with pytest.raises(PdfRenderingError, match="ConnectTimeout"):
        GotenbergPdfRenderer(timeout=1).render("<p>x</p>")


@respx.mock
def test_renders_templates_with_the_pdf_layout() -> None:
    route = respx.post(CONVERT).mock(return_value=httpx.Response(200, content=b"%PDF"))

    get_renderer().render_template("pdf/sample.html", {"issued_on": None})

    html = _fields(route.calls.last.request)["files"]
    assert html.startswith("<!DOCTYPE html>")
    assert "Noto Sans CJK KR" in html and "Noto Sans Lao" in html
    assert '<td lang="zh-Hans">数据结构</td>' in html
    assert '<td lang="lo">ໂຄງສ້າງຂໍ້ມູນ</td>' in html


@respx.mock
def test_pdf_sample_command_writes_the_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from django.core.files.storage import FileSystemStorage

    storage = FileSystemStorage(location=tmp_path)
    monkeypatch.setattr("ninefruits.pdf.management.commands.pdf_sample.default_storage", storage)
    respx.post(CONVERT).mock(return_value=httpx.Response(200, content=b"%PDF-sample"))
    out = io.StringIO()

    code = call_command("pdf_sample", "checks/sample.pdf", stdout=out)

    assert code == 0
    assert (tmp_path / "checks" / "sample.pdf").read_bytes() == b"%PDF-sample"
    assert "Written to" in out.getvalue()


@respx.mock
def test_pdf_sample_command_reports_failures() -> None:
    respx.post(CONVERT).mock(return_value=httpx.Response(503))
    err = io.StringIO()
    assert call_command("pdf_sample", stdout=io.StringIO(), stderr=err) == 1
    assert "HTTP 503" in err.getvalue()


@pytest.mark.gotenberg
def test_renders_mixed_korean_chinese_lao_and_english_with_embedded_fonts() -> None:
    try:
        httpx.get(f"{settings.GOTENBERG_URL.rstrip('/')}/health", timeout=2).raise_for_status()
    except httpx.HTTPError:
        pytest.skip("Gotenberg is not reachable.")

    pdf = get_renderer().render_template("pdf/sample.html", {"issued_on": None})

    assert pdf.startswith(b"%PDF")
    assert b"NotoSansCJKkr" in pdf
    assert b"NotoSansCJKsc" in pdf
    assert b"NotoSansLao" in pdf
