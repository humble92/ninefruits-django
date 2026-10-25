"""Course evaluation per term (original Filament ``TermEvaluationResource``): the form, the
minimum responses for results, response counts and publication to the instructors. The period
is the course evaluation window of each session (Terms). Terms are set up and changed through
``ManageTermEvaluation``."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminIntegerFieldWidget, UnfoldAdminSelectWidget

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.evaluation.actions import ManageTermEvaluation
from ninefruits.evaluation.models import EvaluationForm, EvaluationResponse, TermEvaluation
from ninefruits.registration.admin.common import ConfirmForm, run_form, term_choices
from ninefruits.term.models import Term


def response_count(term_field: str = "term_id") -> Any:
    responses = (
        EvaluationResponse.objects.filter(term_id=OuterRef(term_field))
        .order_by()
        .values("term_id")
        .annotate(total=Count("*"))
        .values("total")
    )
    return Coalesce(Subquery(responses, output_field=IntegerField()), 0)


class PrepareForm(forms.Form):
    """Setting up or changing a term's evaluation (original ``prepareAction``)."""

    term_id = forms.TypedChoiceField(label=_("term"), coerce=int, widget=UnfoldAdminSelectWidget)
    evaluation_form_id = forms.TypedChoiceField(label=_("evaluation form"), coerce=int, widget=UnfoldAdminSelectWidget)
    minimum_responses = forms.IntegerField(
        label=_("Minimum responses"),
        min_value=0,
        max_value=100,
        required=False,
        widget=UnfoldAdminIntegerFieldWidget,
        help_text=_(
            "A section's results show only with at least this many responses and this response rate, so few "
            "answers cannot point to a student."
        ),
    )
    minimum_response_percent = forms.IntegerField(
        label=_("Minimum response rate (%)"),
        min_value=0,
        max_value=100,
        required=False,
        widget=UnfoldAdminIntegerFieldWidget,
    )

    def __init__(self, *args: Any, evaluation: TermEvaluation | None = None, **kwargs: Any) -> None:
        if evaluation is not None:
            kwargs.setdefault(
                "initial",
                {
                    "term_id": evaluation.term_id,
                    "evaluation_form_id": evaluation.form_id,
                    "minimum_responses": evaluation.minimum_responses,
                    "minimum_response_percent": evaluation.minimum_response_percent,
                },
            )
        super().__init__(*args, **kwargs)
        self.fields["term_id"].choices = term_choices()  # type: ignore[attr-defined]
        if evaluation is not None:
            # The term of an existing evaluation stays.
            self.fields["term_id"].disabled = True
        self.fields["evaluation_form_id"].choices = [  # type: ignore[attr-defined]
            (form.pk, f"{form.code} {form.name or ''}".strip())
            for form in EvaluationForm.objects.filter(is_active=True).order_by("code")
        ]


@admin.register(TermEvaluation)
class TermEvaluationAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.EVALUATION
    navigation_icon = "calendar_month"
    navigation_order = 10
    list_display = ("term_name", "form_column", "minimums", "responses", "results_published_at")
    list_select_related = ("term", "form")
    ordering = ("-term_id",)
    list_per_page = 50
    actions_list = ("prepare",)
    actions_row = ("change_row", "publish_row")

    # -- access ----------------------------------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", TermEvaluation)

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(_responses=response_count())

    # -- columns ---------------------------------------------------------------------------------
    @display(description=_("term"), ordering="term__start_date")
    def term_name(self, obj: TermEvaluation) -> str:
        return str(obj.term.name)

    @display(description=_("evaluation form"))
    def form_column(self, obj: TermEvaluation) -> str:
        return f"{obj.form.code} · {obj.form.name or ''}".rstrip(" ·")

    @display(description=_("Minimum responses"))
    def minimums(self, obj: TermEvaluation) -> str:
        return f"{obj.minimum_responses} / {obj.minimum_response_percent}%"

    @display(description=_("Responses"), ordering="_responses")
    def responses(self, obj: TermEvaluation) -> int:
        return int(getattr(obj, "_responses", 0))

    # -- actions ---------------------------------------------------------------------------------
    def _changelist_url(self) -> str:
        return reverse("admin:evaluation_termevaluation_changelist")

    def _evaluation(self, request: HttpRequest, object_id: Any) -> TermEvaluation:
        evaluation: TermEvaluation = get_object_or_404(
            self.get_queryset(request).select_related("term", "form"), pk=object_id
        )
        return evaluation

    def has_prepare_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.policy_allows(request, "create", TermEvaluation)

    def _prepare(self, request: HttpRequest, evaluation: TermEvaluation | None, title: Any) -> HttpResponse:
        form = PrepareForm(request.POST or None, evaluation=evaluation)

        def perform(form: Any) -> str:
            data = form.cleaned_data
            term = get_object_or_404(Term, pk=evaluation.term_id if evaluation is not None else data["term_id"])
            chosen = get_object_or_404(EvaluationForm, pk=data["evaluation_form_id"])
            ManageTermEvaluation().prepare(
                term,
                chosen,
                request.user,
                data.get("minimum_responses"),
                data.get("minimum_response_percent"),
            )
            return gettext("Saved")

        return run_form(
            self,
            request,
            form,
            title,
            self._changelist_url(),
            perform,
            subtitle=str(evaluation.term) if evaluation is not None else "",
        )

    @action(description=_("Set up a term"), url_path="prepare", permissions=["prepare"], icon="add")
    def prepare(self, request: HttpRequest) -> HttpResponse:
        return self._prepare(request, None, _("Set up a term"))

    @action(description=pgettext_lazy("evaluation", "Change"), url_path="change", permissions=["prepare"], icon="edit")
    def change_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        evaluation = self._evaluation(request, object_id)
        return self._prepare(request, evaluation, pgettext_lazy("evaluation", "Change"))

    def has_publish_row_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.policy_allows(request, "update", TermEvaluation)

    @action(
        description=pgettext_lazy("evaluation", "Publish results"),
        url_path="publish",
        permissions=["publish_row"],
        icon="campaign",
    )
    def publish_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        evaluation = self._evaluation(request, object_id)
        if not request.user.has_perm("update", evaluation):
            raise PermissionDenied
        if evaluation.results_published_at is not None:
            messages.info(request, gettext("Already published."))
            return HttpResponseRedirect(self._changelist_url())
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            ManageTermEvaluation().publish(evaluation, request.user)
            return gettext("Instructors see their sections' results from now on (sections with enough responses).")

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("evaluation", "Publish results"),
            self._changelist_url(),
            perform,
            subtitle=str(evaluation.term),
            description=_("Instructors see their sections' results from now on (sections with enough responses)."),
        )
