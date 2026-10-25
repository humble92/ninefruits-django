"""First-screen screenshots for the README, taken from the demo data.

    uv run python tools/screenshots.py [locale ...] [--base-url=URL] [--out=DIR] [--chromium=PATH]

Signs in as the demo system administrator, instructor and student (password ``demo-password``,
created by ``setup_demo``), switches the account language to each locale (``POST /i18n/locale/``)
and captures ``/admin/`` and ``/portal/`` at 1366x900 with Playwright (Chromium). Without
locales it captures every language of the manuals (en, ko, zh_Hans, lo). Files are written to
``docs/screenshots/<locale>/{admin,instructor,student}.png``.

Expects a development server on the demo database, for example ``uv run manage.py runserver
8765`` after ``setup_install`` and ``setup_demo --size=small --seed=42``. Playwright is in the
dev dependency group; run ``uv run playwright install chromium`` once, or pass an existing
Chromium with ``--chromium`` (or ``PLAYWRIGHT_CHROMIUM``). See
docs/development/adding-a-language.md, step 4.

Original: tools/screenshots.py of ninefruits-laravel (Gotenberg screenshots of /admin and
/portal for the same three accounts).
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Browser, Page, ViewportSize, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
#: Locale directory names of the manuals (Django locale names) -> language codes of the app.
LOCALES: dict[str, str] = {"en": "en", "ko": "ko", "zh_Hans": "zh-hans", "lo": "lo"}
VIEWPORT: ViewportSize = {"width": 1366, "height": 900}
DEFAULT_PASSWORD = "demo-password"  # noqa: S105 - fictional demo accounts (ninefruits/setup/conf.py)


@dataclass(frozen=True)
class Shot:
    email: str
    path: str
    file: str


SHOTS: tuple[Shot, ...] = (
    Shot("system-administrator@demo.test", "/admin/", "admin.png"),
    Shot("instructor@demo.test", "/portal/", "instructor.png"),
    Shot("student@demo.test", "/portal/", "student.png"),
)


def locale_pair(value: str) -> tuple[str, str]:
    """``zh_Hans``, ``zh-hans`` or ``zh-Hans`` -> (``zh_Hans``, ``zh-hans``)."""
    for directory, code in LOCALES.items():
        if value.lower() in (directory.lower(), code):
            return directory, code
    # A language added later: directory name as given, language code as Django spells it.
    code = value.replace("_", "-").lower()
    return value, code


def sign_in(page: Page, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/accounts/login/")
    page.fill("input[name=login]", email)
    page.fill("input[name=password]", password)
    with page.expect_navigation():
        page.locator("form:has(input[name=login]) [type=submit]").first.click()
    if "/accounts/login/" in page.url:
        raise SystemExit(f"Sign-in failed for {email}; is the demo data loaded (setup_demo)?")


def switch_language(page: Page, base_url: str, code: str) -> None:
    token = next((c["value"] for c in page.context.cookies() if c["name"] == "csrftoken"), "")
    response = page.request.post(
        f"{base_url}/i18n/locale/",
        form={"locale": code, "next": "/portal/"},
        headers={"X-CSRFToken": token, "Referer": f"{base_url}/portal/"},
    )
    if not response.ok:
        raise SystemExit(f"Language switch to {code} failed: HTTP {response.status}")


def capture(browser: Browser, base_url: str, password: str, directory: str, code: str, out: Path) -> None:
    target = out / directory
    target.mkdir(parents=True, exist_ok=True)
    for shot in SHOTS:
        context = browser.new_context(viewport=VIEWPORT, locale=code, device_scale_factor=1)
        page = context.new_page()
        try:
            sign_in(page, base_url, shot.email, password)
            switch_language(page, base_url, code)
            page.goto(f"{base_url}{shot.path}", wait_until="networkidle")
            if page.locator("html").get_attribute("lang") not in (code, None):
                print(f"  warning: {shot.path} is not in {code}; is it a supported language?", file=sys.stderr)
            file = target / shot.file
            page.screenshot(path=str(file))
            print(f"{directory}: {shot.email} {shot.path} -> {file}")
        finally:
            context.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("locales", nargs="*", help="Locales to capture (default: en ko zh_Hans lo)")
    parser.add_argument("--base-url", default=os.environ.get("APP_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "screenshots")
    parser.add_argument("--chromium", default=os.environ.get("PLAYWRIGHT_CHROMIUM"), help="Chromium executable")
    parser.add_argument("--password", default=os.environ.get("DEMO_PASSWORD", DEFAULT_PASSWORD))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    pairs = [locale_pair(value) for value in (args.locales or list(LOCALES))]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({"executable_path": args.chromium} if args.chromium else {}))
        try:
            for directory, code in pairs:
                capture(browser, base_url, args.password, directory, code, args.out)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
