"""Evaluation forms and their questions (original Filament ``EvaluationFormResource`` with
``QuestionsRelationManager``; legacy SURCATEGORY, SURCONTENT had no screen and were loaded by SQL
each term). A form with responses keeps its questions and scale; copy it to change them."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext, pgettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.admin import StackedInline
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminTextInputWidget

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.evaluation.actions import CopyEvaluationForm
from ninefruits.evaluation.enums import QuestionType
from ninefruits.evaluation.models import EvaluationForm, EvaluationQuestion
from ninefruits.institution.admin_support import ReferenceAdmin, render_action_form, show_errors
from ninefruits.security.enums import Permission


def clean_form_code(value: Any) -> str:
    """Letters, digits, dashes and underscores (original ``alphaDash``)."""
    code = str(value or "").strip()
    if not code or not all(char.isascii() and (char.isalnum() or char in "-_") for char in code):
        raise forms.ValidationError(
            gettext("The %(attribute)s field must only contain letters, numbers, dashes, and underscores.")
            % {"attribute": pgettext("reference", "Code")}
        )
    return code


class EvaluationFormAdminForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = EvaluationForm
        fields = ("code", "is_active", "name", "description", "scale_points", "scale_low_label", "scale_high_label")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # The scale stays while responses use the form (results must keep meaning what was asked).
        if self.instance.pk is not None and self.instance.is_locked():
            self.fields["scale_points"].disabled = True

    def clean_code(self) -> str:
        return clean_form_code(self.cleaned_data["code"])


class CopyFormForm(forms.Form):
    code = forms.CharField(
        label=pgettext_lazy("reference", "Code"),
        max_length=32,
        widget=UnfoldAdminTextInputWidget,
    )

    def clean_code(self) -> str:
        code = clean_form_code(self.cleaned_data["code"])
        if EvaluationForm.objects.filter(code=code).exists():
            raise forms.ValidationError(
                gettext("The %(attribute)s has already been taken.") % {"attribute": pgettext("reference", "Code")}
            )
        return code


class QuestionInline(CatalogPermissionMixin, StackedInline):  # type: ignore[misc]
    """The questions of a form. Locked once the form has responses; copy the form to change
    them."""

    model = EvaluationQuestion
    fk_name = "form"
    extra = 0
    tab = True
    verbose_name = _("Question")
    verbose_name_plural = _("Questions")
    fields = ("category", "text", ("question_type", "sort_order"), ("is_required", "is_reversed"))
    ordering = ("sort_order", "id")

    def _editable(self, request: HttpRequest, obj: Any) -> bool:
        if not request.user.has_perm(Permission.EVALUATIONS_MANAGE):
            return False
        return not (isinstance(obj, EvaluationForm) and obj.is_locked())

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", EvaluationQuestion))

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._editable(request, obj)

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._editable(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._editable(request, obj)

    def get_formset(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        formset = super().get_formset(request, obj, **kwargs)
        if "question_type" in formset.form.base_fields:
            formset.form.base_fields["question_type"].initial = QuestionType.SCALE
        if "sort_order" in formset.form.base_fields and isinstance(obj, EvaluationForm):
            last = obj.questions.order_by("-sort_order").values_list("sort_order", flat=True).first()
            formset.form.base_fields["sort_order"].initial = (last or 0) + 10
        return formset


@admin.register(EvaluationForm)
class EvaluationFormAdmin(ReferenceAdmin):
    manage_permission = Permission.EVALUATIONS_MANAGE
    navigation_group = NavigationGroup.EVALUATION
    navigation_icon = "fact_check"
    navigation_order = 20
    form = EvaluationFormAdminForm
    list_display = ("code", "name_column", "question_count", "scale_points", "is_active")
    search_fields = ("code",)
    ordering = ("code",)
    inlines = (QuestionInline,)
    actions_detail = ("copy_form",)

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(_questions=Count("questions"))

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: EvaluationForm) -> str:
        return str(obj.name or "")

    @display(description=_("Questions"), ordering="_questions")
    def question_count(self, obj: EvaluationForm) -> int:
        return int(getattr(obj, "_questions", 0))

    def has_copy_form_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm("create", EvaluationForm))

    @action(description=_("Copy form"), url_path="copy", permissions=["copy_form"], icon="content_copy")
    def copy_form(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        source = get_object_or_404(self.get_queryset(request), pk=object_id)
        back = reverse("admin:evaluation_evaluationform_change", args=[source.pk])
        form = CopyFormForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            from django.core.exceptions import ValidationError

            try:
                copy = CopyEvaluationForm()(source, form.cleaned_data["code"], request.user)
            except ValidationError as error:
                show_errors(request, error)
            else:
                return HttpResponseRedirect(reverse("admin:evaluation_evaluationform_change", args=[copy.pk]))
        return render_action_form(self, request, form, _("Copy form"), back, subtitle=str(source))
