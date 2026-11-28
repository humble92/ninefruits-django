from typing import Any

from ninefruits.core.commands import AuditedCommand
from ninefruits.person.actions.year_levels import ManageYearLevels


class Command(AuditedCommand):
    help = "Apply due approved student year-level changes"

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]
        count = ManageYearLevels().apply_due()
        self.record_result({"runs_applied": count})
        self.info(f"Applied {count} year-level run(s).")
        return self.SUCCESS
