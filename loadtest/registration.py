"""Locust load test: the registration peak (original ``tests/load/registration.js``, k6).

    uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \\
        --host http://127.0.0.1:8000 --csv storage/loadtest/run

Environment:

- ``ACCOUNTS``: CSV with ``email,password`` written by ``setup_demo --student-accounts``
  (default ``storage/private/load-accounts.csv``).
- ``SEARCH``: catalog search text (default ``GEN``, the demo's general-education course codes).

Every iteration signs in as the next student (fresh cookies), opens the registration page,
searches the catalog the way the browser does (HTMX ``?partial=results``), registers for the
first section with open seats and drops it again so the data returns to its starting state. A
refusal (full section, rule, closed window) is a handled outcome, not an error; only HTTP
failures and slow pages fail the thresholds, which are checked when the run ends:

- ``registration_page`` p95 < 800 ms, ``enroll`` p95 < 1500 ms, failures < 1 %.
"""

from __future__ import annotations

import csv
import itertools
import os
import re
import threading
from pathlib import Path
from typing import Any

from locust import HttpUser, between, events, task

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS_FILE = Path(os.environ.get("ACCOUNTS", ROOT / "storage" / "private" / "load-accounts.csv"))
SEARCH = os.environ.get("SEARCH", "GEN")
THRESHOLDS_MS = {"registration_page": 800, "enroll": 1500}
MAX_FAILURE_RATIO = 0.01

CSRF_INPUT = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
TERM_INPUT = re.compile(r'name="term" value="(\d+)"')
# One search result row (``data-*`` attributes, independent of the interface language).
RESULT = re.compile(r'data-section="(\d+)" data-open-seats="(\d+)"')
DROP = re.compile(r'name="action" value="drop">[\s\S]*?name="enrollment_id" value="(\d+)"')


def _load_accounts() -> list[dict[str, str]]:
    if not ACCOUNTS_FILE.exists():
        raise SystemExit(f"No account list at {ACCOUNTS_FILE}: run `manage.py setup_demo --student-accounts` first.")
    with ACCOUNTS_FILE.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("email")]


_accounts = _load_accounts()
_next_account = itertools.cycle(range(len(_accounts)))
_lock = threading.Lock()


def _account() -> dict[str, str]:
    with _lock:
        return _accounts[next(_next_account)]


_outcomes: dict[str, int] = {"enrolled": 0, "dropped": 0, "refused": 0}


def _count(outcome: str) -> None:
    """Registration outcomes (k6 ``Counter``), printed when the run ends."""
    with _lock:
        _outcomes[outcome] += 1


def _csrf(body: str) -> str | None:
    match = CSRF_INPUT.search(body)
    return match[1] if match else None


class Student(HttpUser):
    wait_time = between(1, 1)

    @task
    def register_and_drop(self) -> None:
        self.client.cookies.clear()
        account = _account()

        login = self.client.get("/accounts/login/", name="login_page")
        token = _csrf(login.text)
        with self.client.post(
            "/accounts/login/",
            data={"csrfmiddlewaretoken": token or "", "login": account["email"], "password": account["password"]},
            headers={"Referer": f"{self.host}/accounts/login/"},
            allow_redirects=False,
            name="login",
            catch_response=True,
        ) as signed_in:
            if signed_in.status_code != 302:
                signed_in.failure(f"sign in returned {signed_in.status_code}")
                return

        page = self.client.get("/portal/registration/", name="registration_page")
        if page.status_code != 200:
            return
        term = TERM_INPUT.search(page.text)
        token = _csrf(page.text)
        if term is None or token is None:
            return  # no term open for this student: nothing to register

        search = self.client.get(
            "/portal/registration/",
            params={"term": term[1], "q": SEARCH, "partial": "results"},
            headers={"HX-Request": "true"},
            name="search",
        )
        results = [(section, int(seats)) for section, seats in RESULT.findall(search.text)]
        if not results:
            return
        # Prefer a section with open seats; the first result's refusal is still a realistic outcome.
        section = next((section for section, seats in results if seats > 0), results[0][0])
        before = set(DROP.findall(page.text))

        enrolled = self._post(
            token, {"action": "enroll", "term": term[1], "q": SEARCH, "section_id": section}, "enroll"
        )
        added = [enrollment for enrollment in DROP.findall(enrolled) if enrollment not in before]
        if added:
            _count("enrolled")
            self._post(token, {"action": "drop", "term": term[1], "q": SEARCH, "enrollment_id": added[0]}, "drop")
            _count("dropped")
        else:
            _count("refused")

    def _post(self, token: str, data: dict[str, str], name: str) -> str:
        """Posts a registration button like HTMX does and returns the page it redirects to."""
        response = self.client.post(
            "/portal/registration/",
            data={"csrfmiddlewaretoken": token, **data},
            headers={"HX-Request": "true", "Referer": f"{self.host}/portal/registration/"},
            name=name,
        )
        return response.text


@events.quitting.add_listener
def _check_thresholds(environment: Any, **_kwargs: Any) -> None:
    stats = environment.stats
    problems = []
    for name, limit in THRESHOLDS_MS.items():
        entry = stats.entries.get((name, "GET")) or stats.entries.get((name, "POST"))
        if entry and entry.num_requests and entry.get_response_time_percentile(0.95) > limit:
            problems.append(f"{name} p95 {entry.get_response_time_percentile(0.95):.0f} ms > {limit} ms")
    total = stats.total
    if total.num_requests and total.num_failures / total.num_requests > MAX_FAILURE_RATIO:
        problems.append(f"failures {total.num_failures / total.num_requests:.2%} > {MAX_FAILURE_RATIO:.0%}")
    print("registration outcomes: " + ", ".join(f"{key} {value}" for key, value in sorted(_outcomes.items())))
    for problem in problems:
        print(f"threshold failed: {problem}")
    if problems:
        environment.process_exit_code = 1
