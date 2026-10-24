"""The student's own degree audit in the portal (original Livewire ``MyGraduation``), evaluated
now (not the stored one): what is done and what is left per requirement. Runs in the student's
database context, so only their own rows are read."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from ninefruits.graduation.data import for_display
from ninefruits.graduation.services import DegreeAudit
from ninefruits.person.services import CurrentStudentRecord


class MyGraduationView(LoginRequiredMixin, View):
    template_name = "graduation/portal/my_graduation.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        results = [for_display(result.to_dict()) for result in DegreeAudit().evaluate_all(record)]
        return render(request, self.template_name, {"record": record, "results": results})
