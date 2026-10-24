"""Grades in the portal (original Livewire ``GradeEntry`` and ``MyGrades``).

Grade entry (``/portal/sections/<id>/grades/``): absolute evaluation takes scores and shows the
grade each gives right away (an HTMX request per score, partial ``preview``); relative evaluation
takes grades only, and the grade caps are checked before submission. Drafts and submission while
the grade entry window is open; after finalization a grade change request with a reason. The page
is one form: its buttons POST an ``action``; a successful action keeps its messages for the next
page and redirects back (the page works without JavaScript), an action that fails shows the page
again with what was entered. With HTMX the block ``#grade-entry`` is swapped.

My grades (``/portal/grades/``): a student's finalized grades by term with credits, GPA and
standing. A hold that blocks grades hides them, and terms a provider hides (Phase 7: an open,
unfinished course evaluation) are left out; enforced here, not only in the menu (the legacy
greyed out the link but served the page)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import View

from ninefruits.curriculum.enums import GradingBasis
from ninefruits.grading.actions import ManageEvaluationMethodRequests, ManageGradeChanges, SaveGrades
from ninefruits.grading.enums import EvaluationMethod, GradeChangeStatus, GradeStatus
from ninefruits.grading.models import EvaluationMethodRequest, GradeChangeRequest
from ninefruits.grading.services import GradeDistributionCheck, GradeOptions, GradeReport, score_text
from ninefruits.grading.services.report import hidden_term_ids, hidden_terms
from ninefruits.offering.models import Section
from ninefruits.security.enums import Permission
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services import TermResolver

FLASH_KEY = "grading.flash"
REASON_MAX = 2000


def _int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except TypeError, ValueError:
        return None


def register_teaching_column() -> None:
    """The grade entry link on the portal teaching page (original ``my-teaching``)."""
    from ninefruits.offering.teaching import register_column

    def render_link(request: HttpRequest, section: Any) -> str:
        return format_html(
            '<a href="{}" class="underline">{}</a>', reverse("portal:grade_entry", args=[section.pk]), _("Enter grades")
        )

    register_column("grades", gettext_lazy("Grade entry"), render_link, order=20)


def _lms_import(section: Section) -> dict[str, str] | None:
    """The **Load scores from the LMS** button when a platform pulling scores has the section
    linked (Phase 12, original ``hasLmsScores``)."""
    from ninefruits.lms.services.grades import LmsScoreImport

    lms = LmsScoreImport()
    return {"label": lms.button_label()} if lms.available(section) else None


class GradeEntryView(LoginRequiredMixin, View):
    template_name = "grading/portal/grade_entry.html"

    # -- access ----------------------------------------------------------------------------------
    def _section(self, request: HttpRequest, pk: int) -> Section:
        section = get_object_or_404(Section.objects.select_related("course", "version", "session", "term"), pk=pk)
        user = request.user
        allowed = section.is_taught_by(user) or any(
            section.is_in_scope_of(user, permission)
            for permission in (Permission.GRADES_MANAGE, Permission.GRADES_VIEW, Permission.GRADE_CHANGES_REQUEST)
        )
        if not allowed:
            raise PermissionDenied
        return section

    def _enrollments(self, section: Section) -> list[Any]:
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        rows = (
            Enrollment.objects.filter(
                section_id=section.pk,
                status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED, EnrollmentStatus.WITHDRAWN],
            )
            .select_related("student_record__person", "student_record__program", "version", "section")
            .prefetch_related(
                Prefetch(
                    "grade_change_requests",
                    queryset=GradeChangeRequest.objects.filter(status=GradeChangeStatus.PENDING).order_by("id"),
                    to_attr="pending_changes",
                )
            )
        )
        return sorted(rows, key=lambda enrollment: enrollment.student_record.student_number)

    # -- GET -------------------------------------------------------------------------------------------
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = self._section(request, pk)
        preview_id = _int(request.GET.get("preview"))
        if preview_id is not None:
            return self._preview(request, section, preview_id)
        flash = request.session.pop(FLASH_KEY, None) or {"tone": "info", "messages": []}
        context = self._context(request, section, flash, change_for=_int(request.GET.get("change")))
        return render(request, self.template_name, context)

    def _preview(self, request: HttpRequest, section: Section, enrollment_id: int) -> HttpResponse:
        """The grade a score gives (absolute evaluation), for the score field's HTMX request."""
        enrollment = next((e for e in self._enrollments(section) if e.pk == enrollment_id), None)
        code = ""
        if enrollment is not None:
            try:
                choice = GradeOptions().resolve(enrollment, None, request.GET.get(f"grade-{enrollment_id}-score"))
                code = choice.item.code if choice.item is not None else ""
            except ValidationError:
                code = ""
        context = {"row": {"enrollment": enrollment, "preview": code}, "enrollment_id": enrollment_id}
        return render(request, f"{self.template_name}#preview", context)

    def _context(
        self,
        request: HttpRequest,
        section: Section,
        flash: dict[str, Any],
        posted: dict[int, dict[str, str]] | None = None,
        change_for: int | None = None,
        change_values: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        from ninefruits.registration.enums import EnrollmentStatus

        user = request.user
        options = GradeOptions()
        saver = SaveGrades(options)
        enrollments = self._enrollments(section)
        counts = Counter(str(enrollment.grade_status) for enrollment in enrollments)
        can_enter = saver.can_enter(section, user)
        by_staff = saver.is_staff(section, user)
        taught = section.is_taught_by(user)
        may_request_change = taught or section.is_in_scope_of(user, Permission.GRADE_CHANGES_REQUEST)
        absolute = section.evaluation_method == EvaluationMethod.ABSOLUTE
        relative = (
            section.evaluation_method == EvaluationMethod.RELATIVE
            and section.version.grading_basis == GradingBasis.GRADED
        )
        distribution = GradeDistributionCheck(options.settings).for_section(section) if relative else None
        editable_statuses = {GradeStatus.NONE, GradeStatus.DRAFT} | ({GradeStatus.SUBMITTED} if by_staff else set())
        rows = []
        for enrollment in enrollments:
            values = (posted or {}).get(enrollment.pk)
            takes_score = options.takes_score(enrollment)
            editable = (
                can_enter
                and enrollment.status == EnrollmentStatus.ENROLLED
                and enrollment.grade_status in editable_statuses
            )
            pending = list(getattr(enrollment, "pending_changes", []))
            rows.append(
                {
                    "enrollment": enrollment,
                    "record": enrollment.student_record,
                    "takes_score": takes_score,
                    "codes": options.codes_for(enrollment),
                    "editable": editable,
                    "score": values["score"] if values is not None else score_text(enrollment.score),
                    "code": values["grade_code"] if values is not None else (enrollment.grade_code or ""),
                    "preview": enrollment.grade_code if values is None else "",
                    "score_shown": score_text(enrollment.score),
                    "grade": enrollment.display_grade() or "",
                    "status": (
                        EnrollmentStatus(enrollment.status).label
                        if enrollment.status == EnrollmentStatus.WITHDRAWN
                        else GradeStatus(enrollment.grade_status).label
                    ),
                    "pending_changes": pending,
                    "can_request_change": (
                        may_request_change and enrollment.grade_status == GradeStatus.FINALIZED and not pending
                    ),
                    "change_open": change_for == enrollment.pk,
                }
            )
        method_request = EvaluationMethodRequest.objects.filter(section_id=section.pk).pending().first()
        exception_by = None
        if section.grade_exception_at is not None and section.grade_exception_by_id is not None:
            from ninefruits.security.models import User

            exception_by = User.objects.filter(pk=section.grade_exception_by_id).values_list("email", flat=True).first()
        other = EvaluationMethod(section.evaluation_method).other()
        return {
            "title": f"{_('Grade entry')} {section.label()}",
            "section": section,
            "rows": rows,
            "counts": {status.value: counts.get(status.value, 0) for status in GradeStatus},
            "absolute": absolute,
            "relative": relative,
            "scale": options.scale(),
            "method_label": EvaluationMethod(section.evaluation_method).label,
            "distribution": distribution,
            "method_request": method_request,
            "method_request_label": (
                EvaluationMethod(method_request.requested_method).label if method_request is not None else None
            ),
            "can_request_method": taught and counts.get("submitted", 0) + counts.get("finalized", 0) == 0,
            "other_method": other,
            "other_method_label": other.label,
            "exception_by": exception_by,
            "can_enter": can_enter,
            "by_staff": by_staff,
            "window_open": TermResolver().is_open_in_session(TermWindowType.GRADE_ENTRY, section.session),
            "show_exception_reason": relative and distribution is not None and not distribution.passes() and by_staff,
            "flash": flash,
            "change_values": change_values or {},
            "reason_max": REASON_MAX,
            # Original: next to the method request, for the instructor before submission.
            "lms_import": (
                _lms_import(section)
                if can_enter
                and method_request is None
                and taught
                and counts.get("submitted", 0) + counts.get("finalized", 0) == 0
                else None
            ),
        }

    # -- POST ------------------------------------------------------------------------------------------
    ACTIONS = (
        "save",
        "validate",
        "submit",
        "request_method",
        "cancel_method_request",
        "request_change",
        "cancel_change",
        "import_lms",
    )

    def _import_lms(self, request: HttpRequest, section: Section) -> HttpResponse:
        """Loads the LMS final scores into the score fields as a draft and shows the page again;
        nothing is saved until the user saves (Phase 12, original ``importLmsScores``)."""
        from ninefruits.lms.services.grades import LmsScoreImport

        lms = LmsScoreImport()
        scores = lms.load(section, request.user)
        posted = self._posted(request, section)
        imported = 0
        for enrollment in self._enrollments(section):
            if enrollment.pk not in scores:
                continue
            entry = posted.get(enrollment.pk) or {
                "score": score_text(enrollment.score),
                "grade_code": enrollment.grade_code or "",
            }
            entry["score"] = lms.score_text(scores[enrollment.pk])
            posted[enrollment.pk] = entry
            imported += 1
        flash = {"tone": "success" if imported else "info", "messages": [lms.message(imported)]}
        return render(request, self.template_name, self._context(request, section, flash, posted=posted))

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = self._section(request, pk)
        action, _sep, argument = request.POST.get("action", "").partition(":")
        if action not in self.ACTIONS:
            raise Http404
        if argument:
            request.POST = request.POST.copy()
            request.POST["request_id"] = argument
        if action == "import_lms":
            return self._import_lms(request, section)
        handler: Callable[[HttpRequest, Section], tuple[list[Any], str]] = getattr(self, f"_{action}")
        try:
            messages, tone = handler(request, section)
        except ValidationError as error:
            flash = {"tone": "error", "messages": [str(message) for message in error.messages]}
            change_for = _int(request.POST.get("enrollment_id")) if action == "request_change" else None
            context = self._context(
                request,
                section,
                flash,
                posted=self._posted(request, section),
                change_for=change_for,
                change_values={
                    "score": request.POST.get("change_score", ""),
                    "grade": request.POST.get("change_grade", ""),
                    "reason": request.POST.get("change_reason", ""),
                },
            )
            return render(request, self.template_name, context)
        request.session[FLASH_KEY] = {"tone": tone, "messages": [str(message) for message in messages if message]}
        return HttpResponseRedirect(reverse("portal:grade_entry", args=[section.pk]))

    def _posted(self, request: HttpRequest, section: Section) -> dict[int, dict[str, str]]:
        """The grade fields of the form by enrollment id (``grade-<id>-score``, ``grade-<id>-code``)."""
        grades: dict[int, dict[str, str]] = {}
        for key in request.POST:
            parts = key.split("-")
            if len(parts) == 3 and parts[0] == "grade" and parts[2] in ("score", "code"):
                enrollment_id = _int(parts[1])
                if enrollment_id is None:
                    continue
                entry = grades.setdefault(enrollment_id, {"score": "", "grade_code": ""})
                entry["score" if parts[2] == "score" else "grade_code"] = request.POST.get(key, "").strip()
        return grades

    def _editable_grades(self, request: HttpRequest, section: Section) -> dict[int, dict[str, str]]:
        """Only the rows the user may still change (original ``editableGrades``)."""
        saver = SaveGrades()
        if not saver.can_enter(section, request.user):
            return {}
        editable = set(saver.editable(section, saver.is_staff(section, request.user)).values_list("pk", flat=True))
        return {key: value for key, value in self._posted(request, section).items() if key in editable}

    def _save(self, request: HttpRequest, section: Section) -> tuple[list[Any], str]:
        count = SaveGrades().save(section, self._editable_grades(request, section), request.user)
        return [_("%(count)s grade(s) saved.") % {"count": count}], "success"

    def _validate(self, request: HttpRequest, section: Section) -> tuple[list[Any], str]:
        """Relative evaluation: saves the drafts and shows how the grades sit against the caps."""
        SaveGrades().save(section, self._editable_grades(request, section), request.user)
        section.refresh_from_db()
        distribution = GradeDistributionCheck().for_section(section)
        if distribution.passes():
            return [_("The grades are within the caps.")], "success"
        return list(distribution.violations), "error"

    def _submit(self, request: HttpRequest, section: Section) -> tuple[list[Any], str]:
        saver = SaveGrades()
        saver.save(section, self._editable_grades(request, section), request.user)
        reason = (request.POST.get("exception_reason") or "").strip()[:REASON_MAX] or None
        count = saver.submit(section, request.user, reason)
        return [_("%(count)s grade(s) submitted.") % {"count": count}], "success"

    def _request_method(self, request: HttpRequest, section: Section) -> tuple[list[Any], str]:
        reason = (request.POST.get("method_reason") or "").strip()
        if len(reason) > REASON_MAX:
            raise ValidationError(_("The reason is too long."))
        other = EvaluationMethod(section.evaluation_method).other()
        ManageEvaluationMethodRequests().request(section, other, reason, request.user)
        return [_("Change to %(method)s requested. You will be told by email.") % {"method": other.label}], "success"

    def _cancel_method_request(self, request: HttpRequest, section: Section) -> tuple[list[Any], str]:
        method_request = get_object_or_404(
            EvaluationMethodRequest, section_id=section.pk, pk=_int(request.POST.get("request_id"))
        )
        ManageEvaluationMethodRequests().cancel(method_request, request.user)
        return [], "info"

    def _request_change(self, request: HttpRequest, section: Section) -> tuple[list[Any], str]:
        from ninefruits.registration.models import Enrollment

        enrollment = get_object_or_404(
            Enrollment.objects.select_related("section", "version"),
            section_id=section.pk,
            pk=_int(request.POST.get("enrollment_id")),
        )
        grade = (request.POST.get("change_grade") or "").strip() or None
        score = (request.POST.get("change_score") or "").strip() or None
        reason = (request.POST.get("change_reason") or "").strip()
        if grade is None and score is None:
            raise ValidationError(_("Enter the new score or grade."))
        if len(reason) > REASON_MAX:
            raise ValidationError(_("The reason is too long."))
        ManageGradeChanges().request(enrollment, grade, reason, request.user, score)
        return [_("Grade change requested.")], "success"

    def _cancel_change(self, request: HttpRequest, section: Section) -> tuple[list[Any], str]:
        change = get_object_or_404(
            GradeChangeRequest, enrollment__section_id=section.pk, pk=_int(request.POST.get("request_id"))
        )
        ManageGradeChanges().cancel(change, request.user)
        return [], "info"


class MyGradesView(LoginRequiredMixin, View):
    template_name = "grading/portal/my_grades.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from ninefruits.person.services import CurrentStudentRecord

        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        report = GradeReport()
        hold = report.blocking_hold(record)
        hidden = hidden_terms(record) if hold is None else []
        hidden_ids = hidden_term_ids(record) if hold is None else []
        terms = report.terms(record, hidden_ids) if hold is None else []
        context = {
            "title": _("Grades"),
            "record": record,
            "hold": hold,
            "hidden": hidden,
            "terms": list(reversed(terms)),
            "superseded": report.superseded(record) if hold is None else set(),
            "latest": report.latest_record(record, hidden_ids) if hold is None else None,
        }
        return render(request, self.template_name, context)
