"""Locust load test: the registration peak (original ``tests/load/registration.js``, k6).

    uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \\
        --host http://127.0.0.1:8000 --csv storage/loadtest/run

Run the server behind one trusted proxy hop (``TRUSTED_PROXY_COUNT=1``): every simulated
student then sends its own ``X-Forwarded-For`` address, the way Nginx reports campus clients,
and allauth's per-address sign-in limit (``LOGIN_RATE_LIMIT_PER_IP``) applies per student
instead of to the load generator's single address.

Environment:

- ``ACCOUNTS``: CSV with ``email,password`` written by ``setup_demo --student-accounts`` into
  private storage (default ``$PRIVATE_MEDIA_ROOT/load-accounts.csv``, else
  ``storage/private/load-accounts.csv``).
- ``SEARCH``: catalog search text (default ``GEN``, the demo's general-education course codes).
- ``ADDRESSES``: how many client addresses the students share. ``0`` (default): one address per
  student account. ``1``: every student behind one NAT address (shows the per-address sign-in
  limit); ``N``: students spread over N addresses.
- ``FIRST_ACCOUNT``: index of the first account (default: random), so consecutive runs use other
  students than the iterations a previous run cut off at its end (those can still hold a seat).

Every iteration signs in as the next student (fresh cookies), opens the registration page,
searches the catalog the way the browser does (HTMX ``?partial=results``), registers for the
first section with open seats and drops it again so the data returns to its starting state. A
refusal (full section, rule, closed window) is a handled outcome, not an error; only HTTP
failures and slow pages fail the thresholds, which are checked when the run ends:

- ``registration_page`` p95 < 800 ms, ``enroll`` p95 < 1500 ms, failures < 1 %.

The registration buttons post like HTMX does (``HX-Request``): the view runs the action and
answers 302 to the registration page, which the client follows; the ``enroll`` and ``drop``
timings include that page, as the browser waits for it before it swaps ``#registration``.
After the run, ``loadtest/seat_check.sql`` confirms no section holds more students than seats.
"""

from __future__ import annotations

import csv
import ipaddress
import itertools
import os
import random
import re
import threading
from pathlib import Path
from typing import Any

from locust import HttpUser, between, events, task

ROOT = Path(__file__).resolve().parents[1]
_PRIVATE = Path(os.environ.get("PRIVATE_MEDIA_ROOT", ROOT / "storage" / "private"))
ACCOUNTS_FILE = Path(os.environ.get("ACCOUNTS", _PRIVATE / "load-accounts.csv"))
SEARCH = os.environ.get("SEARCH", "GEN")
ADDRESSES = int(os.environ.get("ADDRESSES", "0"))
THRESHOLDS_MS = {"registration_page": 800, "enroll": 1500}
MAX_FAILURE_RATIO = 0.01
#: First simulated client address (a private range, one address per account index).
FIRST_ADDRESS = int(ipaddress.ip_address("10.0.0.1"))

CSRF_INPUT = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
TERM_INPUT = re.compile(r'name="term" value="(\d+)"')
# One search result row (``data-*`` attributes, independent of the interface language).
RESULT = re.compile(r'data-section="(\d+)" data-open-seats="(\d+)"')
DROP = re.compile(r'name="action" value="drop">[\s\S]*?name="enrollment_id" value="(\d+)"')
TONE = re.compile(r'role="status" data-tone="(\w+)"')


def _load_accounts() -> list[dict[str, str]]:
    if not ACCOUNTS_FILE.exists():
        raise SystemExit(f"No account list at {ACCOUNTS_FILE}: run `manage.py setup_demo --student-accounts` first.")
    with ACCOUNTS_FILE.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("email")]


_accounts = _load_accounts()
_first = int(os.environ.get("FIRST_ACCOUNT") or random.randrange(len(_accounts)))  # noqa: S311 (not a secret)
_next_account = itertools.islice(itertools.cycle(range(len(_accounts))), _first, None)
_lock = threading.Lock()


def _account() -> tuple[int, dict[str, str]]:
    with _lock:
        index = next(_next_account)
    return index, _accounts[index]


def _address(index: int) -> str:
    """The student's client address as the trusted proxy reports it."""
    slot = index % ADDRESSES if ADDRESSES > 0 else index
    return str(ipaddress.ip_address(FIRST_ADDRESS + slot))


_outcomes: dict[str, int] = {
    "enrolled": 0,
    "dropped": 0,
    "refused": 0,
    "no_term": 0,
    "no_results": 0,
    "sign_in_refused": 0,
}


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
        index, account = _account()
        self.client.headers["X-Forwarded-For"] = _address(index)

        login = self.client.get("/accounts/login/", name="login_page")
        token = _csrf(login.text)
        with self.client.post(
            "/accounts/login/",
            data={"csrfmiddlewaretoken": token or "", "login": account["email"], "password": account["password"]},
            allow_redirects=False,
            name="login",
            catch_response=True,
        ) as signed_in:
            if signed_in.status_code != 302:
                # 429: allauth's per-address limit; 200: the form came back with an error.
                signed_in.failure(f"sign in returned {signed_in.status_code}")
                _count("sign_in_refused")
                return

        page = self.client.get("/portal/registration/", name="registration_page")
        if page.status_code != 200:
            return
        term = TERM_INPUT.search(page.text)
        token = _csrf(page.text)
        if term is None or token is None:
            _count("no_term")  # no term open for this student: nothing to register
            return

        search = self.client.get(
            "/portal/registration/",
            params={"term": term[1], "q": SEARCH, "partial": "results"},
            headers={"HX-Request": "true"},
            name="search",
        )
        results = [(section, int(seats)) for section, seats in RESULT.findall(search.text)]
        if not results:
            _count("no_results")
            return
        # Prefer a section with open seats; the first result's refusal is still a realistic outcome.
        section = next((section for section, seats in results if seats > 0), results[0][0])
        before = set(DROP.findall(page.text))

        enrolled = self._post(
            token, {"action": "enroll", "term": term[1], "q": SEARCH, "section_id": section}, "enroll"
        )
        added = [enrollment for enrollment in DROP.findall(enrolled) if enrollment not in before]
        if not added:
            _count("refused")
            return
        _count("enrolled")
        dropped = self._post(token, {"action": "drop", "term": term[1], "q": SEARCH, "enrollment_id": added[0]}, "drop")
        tone = TONE.search(dropped)
        if tone is not None and tone[1] == "success" and added[0] not in DROP.findall(dropped):
            _count("dropped")

    def _post(self, token: str, data: dict[str, str], name: str) -> str:
        """Posts a registration button like HTMX does and returns the page it redirects to."""
        response = self.client.post(
            "/portal/registration/",
            data={"csrfmiddlewaretoken": token, **data},
            headers={"HX-Request": "true"},
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
