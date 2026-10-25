"""Writes the standard reports as CSV, for comparing with the original (porting-plan Phase 13).

Both systems share the schema, so the comparison loads the original's demo data into a Django
database (``pg_dump --data-only`` of the original, restored with triggers disabled) and runs the
same reports with the same parameters on both sides:

    DB_DATABASE=nf_reportcmp uv run python tools/report_csv_dump.py /tmp/reports-django
    diff -r /tmp/reports-original /tmp/reports-django

The original side runs ``ReportCatalog::csv`` with the same ``RUNS`` (see
``porting/phase-13-report.md``). Reports run in English as the system actor.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: file name -> (report key, parameters); term ids refer to the restored original data.
RUNS: dict[str, tuple[str, dict[str, object]]] = {
    "students": ("students", {}),
    "headcount": ("headcount", {}),
    "graduation_candidates": ("graduation_candidates", {}),
    "status_changes": ("status_changes", {}),
    "section_enrollments": ("section_enrollments", {}),
    "term_records": ("term_records", {}),
    "section_enrollments_t2": ("section_enrollments", {"term": 2}),
    "term_records_t1": ("term_records", {"term": 1}),
    "not_registered_t2": ("not_registered", {"term": 2}),
    "not_registered_t3": ("not_registered", {"term": 3}),
    "students_enrolled": ("students", {"status": "enrolled"}),
}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    import django

    django.setup()
    from django.utils import translation

    from ninefruits.core.db import session_context
    from ninefruits.reporting.services.catalog import ReportCatalog

    target = Path(argv[0])
    target.mkdir(parents=True, exist_ok=True)
    catalog = ReportCatalog()
    with translation.override("en"), session_context().system("report-compare"):
        for name, (key, params) in RUNS.items():
            (target / f"{name}.csv").write_text(catalog.csv(key, dict(params)), encoding="utf-8")
            print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
