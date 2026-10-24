"""Public pages (original ``AdmissionCycleListController``, Fortify ``verifyEmailView``) and the
application document download (original ``ApplicationDocumentController``)."""

from __future__ import annotations

from typing import Any

from allauth.account.internal.flows.email_verification import send_verification_email_for_user
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views import View

from ninefruits.admission.actions.registration import registration_enabled
from ninefruits.admission.models import AdmissionCycle, AdmissionCycleProgram, Application
from ninefruits.media.models import Media
from ninefruits.media.views import PrivateMediaDownloadView


class AdmissionCycleListView(View):
    """Public list of cycles taking applications, the starting point for new applicants."""

    template_name = "admission/public/index.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        cycles = list(
            AdmissionCycle.objects.accepting_applications()
            .prefetch_related(
                Prefetch("programs", queryset=AdmissionCycleProgram.objects.select_related("program").order_by("id"))
            )
            .order_by("opens_at")
        )
        return render(
            request,
            self.template_name,
            {
                "title": pgettext("admissions", "Admissions"),
                "cycles": cycles,
                "registration_enabled": registration_enabled(),
            },
        )


class VerifyEmailView(LoginRequiredMixin, View):
    """Asks to verify the sign-in email before applying, with a button to send the link again."""

    template_name = "admission/public/verify_email.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        if request.user.has_verified_email():
            return HttpResponseRedirect(reverse("portal:applications"))
        return render(request, self.template_name, {"title": _("Verify your email")})

    def post(self, request: HttpRequest) -> HttpResponse:
        if not request.user.has_verified_email() and send_verification_email_for_user(request, request.user):
            # allauth adds its own "confirmation sent" message; keep only one notice.
            list(messages.get_messages(request))
            messages.success(request, _("A new link was sent."))
        return HttpResponseRedirect(reverse("admission:verify_email"))


class ApplicationDocumentView(PrivateMediaDownloadView):
    """Serves an uploaded application document to the applicant and to staff who may see the
    application."""

    def get_media(self, request: HttpRequest, **kwargs: Any) -> Media | None:
        application = get_object_or_404(Application.objects.visible_to(request.user), pk=kwargs["pk"])
        if not request.user.has_perm("view", application):
            raise PermissionDenied
        media = get_object_or_404(Media, pk=kwargs["media_id"])
        if not media.belongs_to(application) or media.collection_name != Application.DOCUMENTS_COLLECTION:
            return None
        return media
