from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.db.models import Count, F, Q, QuerySet, Window
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.grading.models import TermRecord
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord, YearLevelChange, YearLevelRule, YearLevelRun
from ninefruits.security.enums import Permission
from ninefruits.security.services.authorization import authorization
from ninefruits.term.models import Term

if TYPE_CHECKING:
    from ninefruits.security.models import User


class ManageYearLevels:
    @staticmethod
    def can_manage(user: User) -> bool:
        return authorization().scope_for(user, Permission.STUDENT_RECORDS_MANAGE).is_global

    @staticmethod
    def can_configure(user: User) -> bool:
        return authorization().scope_for(user, Permission.INSTITUTION_SETTINGS_MANAGE).is_global

    @transaction.atomic
    def save_rule(self, rule: YearLevelRule, data: dict[str, Any], staff: User) -> YearLevelRule:
        if not self.can_configure(staff):
            raise PermissionDenied
        basis = data["basis"]
        try:
            minimums = [Decimal(row["minimum"]) for row in data["thresholds"]] if basis != "manual" else []
            valid = basis in {"credits", "terms", "manual"} and (
                basis == "manual"
                or (
                    1 <= len(minimums) <= 9
                    and all(
                        0 < value <= 99999
                        and value > previous
                        and value % (1 if basis == "terms" else Decimal("0.1")) == 0
                        for previous, value in zip([Decimal(0), *minimums], minimums, strict=False)
                    )
                )
            )
        except InvalidOperation, ValueError:
            valid = False
        if not valid:
            raise ValidationError(
                _(
                    "Use increasing positive thresholds. Terms must be whole numbers "
                    "and credits can have one decimal place."
                )
            )
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [2190101])
        if data["is_default"]:
            YearLevelRule.objects.filter(is_default=True).exclude(pk=rule.pk).update(is_default=False)
        rule.name = data["name"]
        rule.basis = basis
        rule.thresholds = [{"minimum": str(value)} for value in minimums]
        rule.is_default = data["is_default"]
        rule.save()
        audit("year_level.rule_saved", rule, reason="Configure year-level rules", causer=staff)
        return rule

    @transaction.atomic
    def preview(self, term_id: int, cutoff: date, staff: User, program_id: int | None = None) -> YearLevelRun:
        if not self.can_manage(staff):
            raise PermissionDenied
        term = Term.objects.select_for_update().get(pk=term_id)
        if cutoff >= term.start_date or cutoff > timezone.localdate():
            raise ValidationError(_("The results cutoff must be today or earlier and before the target term starts."))
        if YearLevelRun.objects.filter(term=term, status__in=["draft", "scheduled"]).exists():
            raise ValidationError(_("This term already has a draft or scheduled progression run."))
        rules = YearLevelRule.objects.in_bulk()
        default = next((rule for rule in rules.values() if rule.is_default), None)
        if default is None:
            raise ValidationError(_("Set an institution default rule before creating a preview."))
        run = YearLevelRun.objects.create(term=term, cutoff_date=cutoff, program_id=program_id)
        records = StudentRecord.objects.filter(status=StudentStatus.ENROLLED, admission_date__lte=cutoff)
        if program_id is not None:
            records = records.filter(program_id=program_id)
        after = 0
        while chunk := list(records.filter(pk__gt=after).select_related("program").order_by("pk")[:500]):
            after = chunk[-1].pk
            # The latest closed cumulative result already accounts for retakes.
            totals = {
                row["student_record_id"]: row
                for row in TermRecord.objects.filter(
                    student_record_id__in=[record.pk for record in chunk],
                    closed_at__isnull=False,
                    term__end_date__lte=cutoff,
                )
                .annotate(
                    credits=F("cumulative_earned_credits"),
                    terms=Window(
                        expression=Count("pk", filter=Q(earned_credits__gt=0)),
                        partition_by=[F("student_record_id")],
                    ),
                )
                .order_by("student_record_id", "-term__start_date", "-term_id")
                .distinct("student_record_id")
                .values("student_record_id", "credits", "terms")
            }
            changes = []
            for record in chunk:
                rule = rules.get(record.program.year_level_rule_id, default)
                total = totals.get(record.pk)
                if rule.basis == "manual" or total is None:
                    continue
                value = total[rule.basis]
                target = 1 + sum(value >= Decimal(row["minimum"]) for row in rule.thresholds)
                if target > record.year_level:
                    changes.append(
                        YearLevelChange(
                            year_level_run=run,
                            student_record=record,
                            program_id=record.program_id,
                            from_level=record.year_level,
                            to_level=target,
                            rule_name=str(rule.name),
                            basis=rule.basis,
                            measured_value=value,
                        )
                    )
            YearLevelChange.objects.bulk_create(changes)
        audit("year_level.previewed", run, reason="Calculate proposed year levels", causer=staff)
        return run

    @transaction.atomic
    def schedule(self, run_id: int, when: datetime, staff: User) -> None:
        run = self._lock_run(run_id, staff)
        if run.status != "draft" or when <= timezone.now() or not run.changes.filter(outcome__isnull=True).exists():
            raise ValidationError(_("Only a draft with included changes can be scheduled for a future time."))
        run.status, run.scheduled_at, run.approved_by = "scheduled", when, staff
        run.save(update_fields=["status", "scheduled_at", "approved_by", "updated_at"])
        audit("year_level.scheduled", run, reason="Approve the reviewed year-level changes", causer=staff)

    @transaction.atomic
    def exclude(self, run_id: int, change_id: int, staff: User) -> None:
        run = self._lock_run(run_id, staff)
        if run.status != "draft":
            raise ValidationError(_("You can only review changes in a draft."))
        change = run.changes.get(pk=change_id)
        change.outcome = "excluded" if change.outcome is None else None
        change.save(update_fields=["outcome"])
        audit(
            "year_level.reviewed",
            run,
            reason="Review a proposed year-level change",
            properties={"change_id": change_id, "outcome": change.outcome},
            causer=staff,
        )

    @transaction.atomic
    def cancel(self, run_id: int, staff: User) -> None:
        run = self._lock_run(run_id, staff)
        if run.status not in {"draft", "scheduled"}:
            raise ValidationError(_("Only draft or scheduled runs can be canceled."))
        run.status = "canceled"
        run.save(update_fields=["status", "updated_at"])
        audit("year_level.canceled", run, reason="Cancel the proposed or scheduled changes", causer=staff)

    def _lock_run(self, run_id: int, staff: User) -> YearLevelRun:
        if not self.can_manage(staff):
            raise PermissionDenied
        return YearLevelRun.objects.select_for_update().get(pk=run_id)

    def due(self) -> QuerySet[YearLevelRun]:
        return YearLevelRun.objects.filter(status="scheduled", scheduled_at__lte=timezone.now())

    def apply_due(self) -> int:
        return sum(self._apply(pk) for pk in self.due().order_by("pk").values_list("pk", flat=True))

    @transaction.atomic
    def _apply(self, run_id: int) -> bool:
        run = self.due().select_for_update().filter(pk=run_id).first()
        if run is None:
            return False
        counts = {"applied": 0, "stale": 0}
        for change in run.changes.filter(outcome__isnull=True).order_by("student_record_id").iterator():
            updated = StudentRecord.objects.filter(
                pk=change.student_record_id,
                status=StudentStatus.ENROLLED,
                program_id=change.program_id,
                year_level=change.from_level,
            ).update(year_level=change.to_level, updated_at=timezone.now())
            change.outcome = "applied" if updated == 1 else "stale"
            counts[change.outcome] += 1
            change.save(update_fields=["outcome"])
        run.status, run.applied_at = "applied", timezone.now()
        run.save(update_fields=["status", "applied_at", "updated_at"])
        audit("year_level.applied", run, reason="Apply the approved year-level changes", properties=counts)
        return True
