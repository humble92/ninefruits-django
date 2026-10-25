"""Results (original ``RecordAssessmentResult``). For a session: the area scores, the total and
whether it passed (the total against the pass score and every area against its minimum; decided
by hand for pass/fail kinds). Legacy summed the areas against one cut line only, and silently
overwrote scores (cet_add2go). Entering again replaces the result and is audited; published
results are locked (decided 2026-10-23) and change only through a correction request. External
results (an outside body's test) carry the evidence file."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import IO, Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import File
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.assessment.enums import AssessmentRegistrationStatus, ResultSource, ScoringMethod
from ninefruits.assessment.models import (
    AssessmentComponent,
    AssessmentComponentScore,
    AssessmentRegistration,
    AssessmentResult,
    AssessmentSession,
    AssessmentType,
    format_score,
)
from ninefruits.audit.logger import audit
from ninefruits.media.services import add_media, clear_collection
from ninefruits.security.enums import Permission

from ._support import json_number, json_value, now, one_decimal, require_reason, to_decimal


class RecordAssessmentResult:
    def for_registration(
        self,
        registration: AssessmentRegistration,
        scores: dict[str, Any],
        passed: bool | None,
        staff: Any,
        total: Any = None,
        note: str | None = None,
        applying_correction: bool = False,
    ) -> AssessmentResult:
        """``scores``: component code => score."""
        self._authorize(staff)
        # Loaded fresh: the session's publication state decides whether entry is still allowed.
        registration = AssessmentRegistration.objects.select_related("session__assessment_type", "student_record").get(
            pk=registration.pk
        )
        if registration.status == AssessmentRegistrationStatus.CANCELLED:
            raise ValidationError({"registration": _("The student is not registered for this session.")})
        session = registration.session
        # Published results are locked: changes go through a correction request.
        if session.is_published and not applying_correction:
            raise ValidationError(
                {"registration": _("The results of this session are published: request a correction instead.")}
            )

        kind = session.assessment_type
        components = kind.ordered_components()
        by_component, total_score = self._component_scores(kind, components, scores, to_decimal(total))
        is_passed = self._decide(kind, components, session.effective_pass_score(), by_component, total_score, passed)
        note = (note or "").strip() or None

        with transaction.atomic():
            result, _created = AssessmentResult.objects.update_or_create(
                registration_id=registration.pk,
                defaults={
                    "session_id": session.pk,
                    "student_record_id": registration.student_record_id,
                    "assessment_type_id": kind.pk,
                    "source": ResultSource.SESSION,
                    "taken_date": session.held_date,
                    "total_score": total_score,
                    "level": None,
                    "is_passed": is_passed,
                    "note": note,
                    "entered_by_id": staff.pk,
                    "entered_at": now(),
                },
            )
            AssessmentComponentScore.objects.filter(result_id=result.pk).delete()
            AssessmentComponentScore.objects.bulk_create(
                AssessmentComponentScore(result_id=result.pk, component_id=component_id, score=score)
                for component_id, score in by_component.items()
            )
            if registration.status == AssessmentRegistrationStatus.ABSENT:
                registration.status = AssessmentRegistrationStatus.REGISTERED
                registration.save(update_fields=["status", "updated_at"])

        audit(
            "assessment.result_corrected" if applying_correction else "assessment.result_recorded",
            result,
            reason=note,
            properties={
                "session_id": session.pk,
                "student_number": registration.student_record.student_number,
                "total": json_number(total_score),
                "passed": is_passed,
                "scores": json_value(dict(scores)),
            },
            causer=staff,
        )
        return result

    def external(
        self,
        record: Any,
        kind: AssessmentType,
        taken_date: date,
        passed: bool,
        staff: Any,
        total: Any = None,
        level: str | None = None,
        certificate_number: str | None = None,
        note: str | None = None,
        evidence: File[Any] | IO[bytes] | None = None,
    ) -> AssessmentResult:
        self._authorize(staff)
        if not record.is_visible_to(staff):
            raise PermissionDenied
        if not kind.allows_external:
            raise ValidationError({"assessment_type_id": _("This kind does not take external results.")})
        if taken_date > timezone.localdate():
            raise ValidationError({"taken_date": _("The date cannot be in the future.")})
        total_score = to_decimal(total)
        if total_score is not None:
            total_score = one_decimal(total_score)
        level = (level or "").strip() or None
        certificate_number = (certificate_number or "").strip() or None
        note = (note or "").strip() or None

        with transaction.atomic():
            result = AssessmentResult.objects.create(
                student_record_id=record.pk,
                assessment_type_id=kind.pk,
                source=ResultSource.EXTERNAL,
                taken_date=taken_date,
                total_score=total_score,
                level=level,
                is_passed=bool(passed),
                certificate_number=certificate_number,
                note=note,
                entered_by_id=staff.pk,
                entered_at=now(),
            )
            if evidence is not None:
                add_media(result, evidence, AssessmentResult.EVIDENCE_COLLECTION)

        audit(
            "assessment.external_recorded",
            result,
            reason=note,
            properties={
                "type": kind.code,
                "student_number": record.student_number,
                "taken_date": taken_date.isoformat(),
                "level": level,
                "passed": bool(passed),
                "evidence": evidence is not None,
            },
            causer=staff,
        )
        return result

    def remove(self, result: AssessmentResult, staff: Any, reason: str) -> None:
        self._authorize(staff)
        if result.is_locked():
            raise ValidationError(
                {"result": _("The results of this session are published: request a correction instead.")}
            )
        reason = require_reason(reason)
        record = result.student_record
        audit(
            "assessment.result_removed",
            result,
            reason=reason,
            properties={
                "student_number": record.student_number,
                "type_id": result.assessment_type_id,
                "session_id": result.session_id,
                "total": json_number(result.total_score),
                "passed": result.is_passed,
            },
            causer=staff,
        )
        with transaction.atomic():
            # spatie deletes a model's media with the model.
            clear_collection(result, AssessmentResult.EVIDENCE_COLLECTION)
            result.delete()

    def publish(self, session: AssessmentSession, staff: Any) -> AssessmentSession:
        if not staff.has_perm(Permission.ASSESSMENTS_RECORD):
            raise PermissionDenied
        session = AssessmentSession.objects.select_related("assessment_type").get(pk=session.pk)
        if session.is_published:
            raise ValidationError({"session": _("The results of this session are already published.")})
        session.results_published_at = now()
        session.save(update_fields=["results_published_at", "updated_at"])
        audit(
            "assessment.results_published",
            session,
            properties={"results": AssessmentResult.objects.filter(session_id=session.pk).count()},
            causer=staff,
        )
        return session

    # -- rules -------------------------------------------------------------------------------------
    def _component_scores(
        self, kind: AssessmentType, components: list[AssessmentComponent], scores: dict[str, Any], total: Decimal | None
    ) -> tuple[dict[int, Decimal], Decimal | None]:
        """Component scores keyed by component id, and the total."""
        by_id: dict[int, Decimal] = {}
        for component in components:
            value = scores.get(component.code)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                raise ValidationError(
                    {"scores": _("The score for %(component)s is missing.") % {"component": component.name}}
                )
            number = to_decimal(value)
            if number is None or number < 0 or number > component.max_score:
                raise ValidationError(
                    {
                        "scores": _("The score for %(component)s must be between 0 and %(max)s.")
                        % {"component": component.name, "max": format_score(component.max_score)}
                    }
                )
            by_id[component.pk] = one_decimal(number)

        if by_id:
            total = sum(by_id.values(), Decimal(0))
        elif total is not None and (total < 0 or (kind.max_score is not None and total > kind.max_score)):
            raise ValidationError(
                {"total": _("The total must be between 0 and %(max)s.") % {"max": format_score(kind.max_score) or ""}}
            )
        return by_id, (one_decimal(total) if total is not None else None)

    def _decide(
        self,
        kind: AssessmentType,
        components: list[AssessmentComponent],
        pass_score: Decimal | None,
        by_component: dict[int, Decimal],
        total: Decimal | None,
        passed: bool | None,
    ) -> bool:
        if kind.scoring == ScoringMethod.PASS_FAIL:
            if passed is None:
                raise ValidationError({"passed": _("Choose passed or not passed.")})
            return bool(passed)
        if pass_score is None or total is None:
            if passed is None:
                raise ValidationError({"passed": _("This kind has no pass score: choose passed or not passed.")})
            return bool(passed)
        for component in components:
            if component.min_score is not None and by_component.get(component.pk, Decimal(0)) < component.min_score:
                return False
        return total >= pass_score

    def _authorize(self, staff: Any) -> None:
        if not staff.has_perm(Permission.ASSESSMENTS_RECORD):
            raise PermissionDenied
