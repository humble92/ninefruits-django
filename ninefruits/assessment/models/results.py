"""Examination results, area scores and corrections (original
``App\\Models\\Assessment\\{AssessmentResult, AssessmentComponentScore, AssessmentResultCorrection}``).

A result is a student's result for a kind: from one of our sessions (one per registration, with
the area scores) or from an outside body (with the evidence file in the media collection
``evidence``). Whether it passed is decided when it is entered and stored (``is_passed``): a later
change of the rules does not change past decisions, and graduation checks read the stored value.

Once a session's results are published they are locked: a change goes through a correction
request with a reason, decided by someone else with ``assessments.manage``."""

from __future__ import annotations

from typing import Any, ClassVar, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.assessment.enums import CorrectionStatus, ResultSource
from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.media.services import PDF_AND_IMAGES, HasMedia, MediaCollection
from ninefruits.security.enums import Permission

from .sessions import AssessmentRegistration, AssessmentSession
from .types import AssessmentComponent, AssessmentType, format_score

#: Evidence files: PDF, JPG or PNG up to 5 MB (original admin upload limit).
EVIDENCE_MAX_SIZE = 5 * 1024 * 1024


def _is_global(user: Any, permission: Permission) -> bool:
    from ninefruits.security.services.authorization import authorization

    return bool(authorization().scope_for(user, permission).is_global)


class AssessmentResultQuerySet(VisibleQuerySet):
    def passed(self) -> Self:
        return self.filter(is_passed=True)

    def visible_to(self, user: Any) -> Self:
        """Mirrors the row level security of ``assessment_results``: staff with
        ``assessments.record`` or ``assessments.manage`` (global, like ``util.has_permission``)
        see the results of the records they can see; a student sees their own results from
        published sessions and their external results."""
        from ninefruits.person.models import StudentRecord

        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        condition = Q(pk__in=[])
        if _is_global(user, Permission.ASSESSMENTS_RECORD) or _is_global(user, Permission.ASSESSMENTS_MANAGE):
            condition |= Q(student_record_id__in=StudentRecord.objects.visible_to(user).values("pk"))
        if user.person_id is not None:
            condition |= Q(student_record__person_id=user.person_id) & (
                Q(session_id__isnull=True) | Q(session__results_published_at__isnull=False)
            )
        return self.filter(condition)


class AssessmentResult(HasMedia, TimeStampedModel):
    EVIDENCE_COLLECTION: ClassVar[str] = "evidence"
    media_collections: ClassVar[dict[str, MediaCollection]] = {
        "evidence": MediaCollection("evidence", accepts=PDF_AND_IMAGES, max_size=EVIDENCE_MAX_SIZE),
    }

    student_record = models.ForeignKey(
        "person.StudentRecord",
        on_delete=models.PROTECT,
        related_name="assessment_results",
        verbose_name=_("student record"),
    )
    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.PROTECT,
        related_name="results",
        verbose_name=pgettext_lazy("assessment", "Kind"),
    )
    session = models.ForeignKey(
        AssessmentSession,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="results",
        db_column="assessment_session_id",
        verbose_name=_("Examination session"),
    )
    registration = models.OneToOneField(
        AssessmentRegistration,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="result",
        db_column="assessment_registration_id",
    )
    source = models.CharField(pgettext_lazy("assessment", "Source"), max_length=16, choices=ResultSource.choices)
    taken_date = models.DateField(_("Taken on"))
    total_score = models.DecimalField(_("Total"), max_digits=6, decimal_places=1, null=True, blank=True)
    #: Level or grade of an external test (TOPIK 5, HSK 6).
    level = models.CharField(_("Level"), max_length=32, null=True, blank=True)
    is_passed = models.BooleanField(_("Passed"))
    certificate_number = models.CharField(_("Certificate number"), max_length=64, null=True, blank=True)
    note = models.TextField(pgettext_lazy("assessment", "Note"), null=True, blank=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    entered_at = models.DateTimeField()

    objects = AssessmentResultQuerySet.as_manager()

    class Meta:
        db_table = "assessment_results"
        ordering = ["-taken_date", "-id"]
        verbose_name = _("Examination result")
        verbose_name_plural = _("Examination results")
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student_record"],
                name="assessment_results_assessment_session_id_student_record_id_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.assessment_type_id} {self.taken_date}"

    def __repr__(self) -> str:
        return f"<AssessmentResult {self.pk} record={self.student_record_id} type={self.assessment_type_id}>"

    @property
    def assessment_session_id(self) -> int | None:
        return self.session_id

    @property
    def assessment_registration_id(self) -> int | None:
        return self.registration_id

    def is_locked(self) -> bool:
        """Published session results change only through an approved correction. Queried, not
        read from a possibly stale loaded relation."""
        return (
            self.session_id is not None
            and AssessmentSession.objects.filter(pk=self.session_id, results_published_at__isnull=False).exists()
        )

    def has_evidence(self) -> bool:
        return self.get_media(self.EVIDENCE_COLLECTION).exists()

    def scores_by_code(self) -> dict[str, str]:
        """Area scores by component code, as ``"20.0"`` strings."""
        scores = self.component_scores.select_related("component").order_by("component__sort_order", "id")
        return {score.component.code: format_score(score.score) or "" for score in scores}

    def values(self) -> dict[str, Any]:
        """The values a correction proposes or records: scores by component code, total, passed,
        note."""
        return {
            "scores": self.scores_by_code(),
            "total": format_score(self.total_score),
            "passed": bool(self.is_passed),
            "note": self.note,
        }


class AssessmentComponentScoreQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Scores of results the user can see (RLS ``assessment_component_scores_result_select``)."""
        return self.filter(result_id__in=AssessmentResult.objects.visible_to(user).values("pk"))


class AssessmentComponentScore(TimeStampedModel):
    """The score of one area of a result."""

    result = models.ForeignKey(
        AssessmentResult, on_delete=models.CASCADE, related_name="component_scores", db_column="assessment_result_id"
    )
    component = models.ForeignKey(
        AssessmentComponent, on_delete=models.PROTECT, related_name="scores", db_column="assessment_component_id"
    )
    score = models.DecimalField(_("Score"), max_digits=6, decimal_places=1)

    objects = AssessmentComponentScoreQuerySet.as_manager()

    class Meta:
        db_table = "assessment_component_scores"
        ordering = ["id"]
        verbose_name = _("Score")
        verbose_name_plural = _("Score")
        constraints = [
            models.UniqueConstraint(
                fields=["result", "component"],
                name="assessment_component_scores_assessment_result_id_assessment_com",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.component_id}: {format_score(self.score)}"

    def __repr__(self) -> str:
        return f"<AssessmentComponentScore {self.pk} result={self.result_id} component={self.component_id}>"


class AssessmentResultCorrectionQuerySet(VisibleQuerySet):
    def pending(self) -> Self:
        return self.filter(status=CorrectionStatus.PENDING)

    def visible_to(self, user: Any) -> Self:
        """Corrections of results the user can see (RLS
        ``assessment_result_corrections_result_select``)."""
        return self.filter(result_id__in=AssessmentResult.objects.visible_to(user).values("pk"))


class AssessmentResultCorrection(TimeStampedModel):
    """A requested change to a published result: the proposed values, the reason, and the
    decision by someone else."""

    result = models.ForeignKey(
        AssessmentResult, on_delete=models.CASCADE, related_name="corrections", db_column="assessment_result_id"
    )
    #: The proposed values: scores (component code => score), total, passed, note.
    proposed = models.JSONField(_("Proposed values"))
    previous = models.JSONField(_("Current values"))
    reason = models.TextField(pgettext_lazy("common", "Reason"))
    status = models.CharField(
        pgettext_lazy("registration", "Status"),
        max_length=16,
        choices=CorrectionStatus.choices,
        default=CorrectionStatus.PENDING,
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name="+")
    requested_at = models.DateTimeField(pgettext_lazy("grading", "Requested"))
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True, blank=True, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(pgettext_lazy("grading", "Note"), null=True, blank=True)

    objects = AssessmentResultCorrectionQuerySet.as_manager()

    class Meta:
        db_table = "assessment_result_corrections"
        ordering = ["-requested_at", "-id"]
        verbose_name = _("Result correction")
        verbose_name_plural = _("Result corrections")
        constraints = [
            models.UniqueConstraint(
                fields=["result"],
                condition=Q(status="pending"),
                name="assessment_result_corrections_single_pending_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.result_id}: {self.status}"

    def __repr__(self) -> str:
        return f"<AssessmentResultCorrection {self.pk} result={self.result_id} {self.status}>"

    @property
    def is_pending(self) -> bool:
        return self.status == CorrectionStatus.PENDING
