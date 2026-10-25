"""Examinations for the student in the portal (original Livewire ``MyAssessments``, legacy
stu/cet*): the kinds the curriculum requires with the pass state, sessions open for registration
(register, cancel), own registrations and results (published sessions and external results,
with area scores and the evidence link).

GET renders the page. The buttons are forms: POST runs the action, keeps the message for the next
page and redirects back, so the page works without JavaScript; with HTMX the block
``#assessments`` is swapped."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View

from ninefruits.assessment.actions import RegisterForAssessment
from ninefruits.assessment.enums import AssessmentRegistrationStatus
from ninefruits.assessment.models import (
    AssessmentComponentScore,
    AssessmentRegistration,
    AssessmentResult,
    AssessmentSession,
)
from ninefruits.assessment.services import AssessmentPassCheck
from ninefruits.media.models import Media
from ninefruits.person.services import CurrentStudentRecord

FLASH_KEY = "assessment.flash"


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None


class MyAssessmentsView(LoginRequiredMixin, View):
    template_name = "assessment/portal/my_assessments.html"

    def _record(self, request: HttpRequest) -> Any:
        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        return record

    def get(self, request: HttpRequest) -> HttpResponse:
        record = self._record(request)
        registrations = list(
            AssessmentRegistration.objects.visible_to(request.user)
            .filter(student_record_id=record.pk)
            .select_related("session__assessment_type")
        )
        today = timezone.localdate()
        open_sessions = (
            AssessmentSession.objects.open_for_registration()
            .filter(held_date__gte=today, assessment_type__is_active=True)
            .select_related("assessment_type")
            .order_by("held_date", "id")
        )
        active = {r.session_id: r for r in registrations if r.status != AssessmentRegistrationStatus.CANCELLED}
        # Row level security hides session results until they are published.
        results = list(
            AssessmentResult.objects.visible_to(request.user)
            .filter(student_record_id=record.pk)
            .select_related("assessment_type")
            .prefetch_related(
                Prefetch(
                    "component_scores",
                    queryset=AssessmentComponentScore.objects.select_related("component").order_by(
                        "component__sort_order", "id"
                    ),
                )
            )
            .order_by("-taken_date", "-id")
        )
        with_evidence = set(
            Media.objects.filter(
                model_type="assessment.assessmentresult",
                model_id__in=[result.pk for result in results],
                collection_name=AssessmentResult.EVIDENCE_COLLECTION,
            ).values_list("model_id", flat=True)
        )
        context = {
            "title": _("Examinations"),
            "record": record,
            "flash": request.session.pop(FLASH_KEY, None) or {"tone": "info", "messages": []},
            "required": AssessmentPassCheck().required(record),
            "open": [{"session": session, "registration": active.get(session.pk)} for session in open_sessions],
            "registrations": sorted(
                (r for r in registrations if r.status != AssessmentRegistrationStatus.CANCELLED),
                key=lambda r: (r.session.held_date, r.pk),
                reverse=True,
            ),
            "results": [
                {
                    "result": result,
                    "scores": list(result.component_scores.all()),
                    "has_evidence": result.pk in with_evidence,
                }
                for result in results
            ],
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        record = self._record(request)
        action = request.POST.get("action", "")
        register = RegisterForAssessment()
        try:
            if action == "register":
                session = get_object_or_404(AssessmentSession, pk=_int(request.POST.get("session_id")))
                register.register(session, record, request.user)
                self._say(request, _("You are registered."), "success")
            elif action == "cancel":
                registration = get_object_or_404(
                    AssessmentRegistration.objects.visible_to(request.user),
                    pk=_int(request.POST.get("registration_id")),
                    student_record_id=record.pk,
                )
                register.cancel(registration, request.user)
                self._say(request, _("Your registration is cancelled."), "success")
            else:
                raise Http404
        except ValidationError as error:
            self._say(request, " ".join(str(message) for message in error.messages), "error")
        except PermissionDenied:
            raise Http404 from None
        return HttpResponseRedirect(reverse("portal:assessments"))

    def _say(self, request: HttpRequest, message: str, tone: str) -> None:
        request.session[FLASH_KEY] = {"tone": tone, "messages": [str(message)]}
