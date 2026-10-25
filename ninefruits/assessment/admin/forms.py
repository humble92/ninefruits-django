"""Forms of the examination admin screens (original Filament form schemas and action dialogs)."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import (
    UnfoldAdminDecimalFieldWidget,
    UnfoldAdminFileFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminSingleDateWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
)

from ninefruits.assessment.enums import ScoringMethod
from ninefruits.assessment.models import (
    EVIDENCE_MAX_SIZE,
    AssessmentComponent,
    AssessmentRegistration,
    AssessmentResult,
    AssessmentSession,
    AssessmentType,
    format_score,
)
from ninefruits.registration.admin.common import REASON_MAX, UserForm, reason_field

CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
CSV_MAX_SIZE = 5 * 1024 * 1024


def _alpha_dash(value: str, label: Any) -> None:
    if not CODE_PATTERN.match(value or ""):
        raise forms.ValidationError(
            _("The %(attribute)s field must only contain letters, numbers, dashes, and underscores.")
            % {"attribute": label}
        )


def passed_choices() -> list[tuple[str, Any]]:
    return [("", "-"), ("1", _("Passed")), ("0", pgettext_lazy("assessment", "Not passed"))]


def passed_value(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    return str(value) == "1"


def note_field() -> forms.CharField:
    return forms.CharField(
        label=pgettext_lazy("assessment", "Note"),
        max_length=REASON_MAX,
        required=False,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


def score_field(label: Any, maximum: Decimal | None, required: bool) -> forms.DecimalField:
    return forms.DecimalField(
        label=label,
        required=required,
        min_value=Decimal(0),
        max_value=maximum,
        decimal_places=1,
        max_digits=6,
        widget=UnfoldAdminDecimalFieldWidget(attrs={"step": "0.1"}),
    )


# -- kinds and areas --------------------------------------------------------------------------------
class AssessmentTypeForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = AssessmentType
        fields = (
            "code",
            "category",
            "name",
            "scoring",
            "max_score",
            "pass_score",
            "allows_external",
            "is_active",
            "sort_order",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name in ("max_score", "pass_score"):
            self.fields[name].validators.append(MinValueValidator(Decimal(0)))

    def clean_code(self) -> str:
        code = str(self.cleaned_data["code"]).strip()
        _alpha_dash(code, _("Code"))
        return code


class AssessmentComponentForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = AssessmentComponent
        fields = ("code", "max_score", "min_score", "name", "sort_order")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name in ("max_score", "min_score"):
            self.fields[name].validators.append(MinValueValidator(Decimal(0)))

    def clean_code(self) -> str:
        code = str(self.cleaned_data["code"]).strip()
        _alpha_dash(code, _("Code"))
        return code


class AssessmentComponentFormSet(forms.BaseInlineFormSet):  # type: ignore[type-arg]
    def clean(self) -> None:
        """Codes are unique per kind (``assessment_components_assessment_type_id_code_unique``)."""
        super().clean()
        seen: set[str] = set()
        for form in self.forms:
            data = getattr(form, "cleaned_data", None) or {}
            if not data or data.get("DELETE"):
                continue
            code = str(data.get("code") or "").lower()
            if code in seen:
                form.add_error("code", _("The %(attribute)s has already been taken.") % {"attribute": _("Code")})
            seen.add(code)


# -- sessions -----------------------------------------------------------------------------------------
class AssessmentSessionForm(forms.ModelForm):  # type: ignore[type-arg]
    pass_score_reason = forms.CharField(
        label=_("Reason for changing the pass score"),
        max_length=500,
        required=False,
        help_text=_("Recorded in the audit log with the students whose result changed."),
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 2}),
    )

    class Meta:
        model = AssessmentSession
        fields = (
            "assessment_type",
            "held_date",
            "venue",
            "capacity",
            "registration_opens_at",
            "registration_closes_at",
            "pass_score",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "assessment_type" in self.fields:
            kinds = AssessmentType.objects.filter(is_active=True)
            if self.instance.assessment_type_id is not None:
                kinds = kinds | AssessmentType.objects.filter(pk=self.instance.assessment_type_id)
            self.fields["assessment_type"].queryset = kinds.order_by("sort_order", "code")  # type: ignore[attr-defined]
        if "capacity" in self.fields:
            self.fields["capacity"].validators.append(MinValueValidator(1))
        if "pass_score" in self.fields:
            self.fields["pass_score"].validators.append(MinValueValidator(Decimal(0)))

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        opens, closes = cleaned.get("registration_opens_at"), cleaned.get("registration_closes_at")
        if opens is not None and closes is not None and closes <= opens:
            self.add_error(
                "registration_closes_at",
                _("The %(attribute)s field must be a date after %(date)s.")
                % {"attribute": _("Registration closes"), "date": _("Registration opens")},
            )
        return cleaned


class StudentNumberForm(UserForm):
    """Register a student (original ``RegistrationsRelationManager`` ``register`` action)."""

    student_number = forms.CharField(label=_("Student number"), max_length=32, widget=UnfoldAdminTextInputWidget)


class CancelRegistrationForm(forms.Form):
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"),
        max_length=REASON_MAX,
        required=False,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


class ImportResultsForm(forms.Form):
    file = forms.FileField(label=_("CSV file"), widget=UnfoldAdminFileFieldWidget)

    def clean_file(self) -> Any:
        upload = self.cleaned_data["file"]
        if upload.size > CSV_MAX_SIZE:
            raise forms.ValidationError(
                _("The file is too big (%(size)s bytes, at most %(limit)s).")
                % {
                    "size": upload.size,
                    "limit": CSV_MAX_SIZE,
                }
            )
        return upload


class ResultEntryForm(forms.Form):
    """Result of a registration (original ``resultForm``): a score per area (or the total), the
    decision when staff decide, and a note. Built for the session's kind."""

    def __init__(self, *args: Any, session: AssessmentSession, result: AssessmentResult | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.session = session
        kind = session.assessment_type
        self.components = kind.ordered_components()
        pass_score = session.effective_pass_score()
        for component in self.components:
            self.fields[f"score_{component.code}"] = score_field(component.label(), component.max_score, True)
        if not self.components:
            self.fields["total"] = score_field(
                _("Total"), kind.max_score, kind.scoring == ScoringMethod.SCORE and pass_score is not None
            )
        automatic = kind.scoring == ScoringMethod.SCORE and pass_score is not None
        self.fields["passed"] = forms.ChoiceField(
            label=_("Passed"),
            choices=passed_choices(),
            required=not automatic,
            widget=UnfoldAdminSelectWidget,
            help_text=(
                _("Decided from the scores: total at or above %(score)s and every area at or above its minimum.")
                % {"score": format_score(pass_score)}
                if automatic
                else ""
            ),
        )
        self.fields["note"] = note_field()
        if result is not None and not self.is_bound:
            scores = result.scores_by_code()
            for component in self.components:
                self.initial[f"score_{component.code}"] = scores.get(component.code)
            self.initial["total"] = format_score(result.total_score)
            self.initial["passed"] = "1" if result.is_passed else "0"
            self.initial["note"] = result.note

    def scores(self) -> dict[str, Any]:
        return {component.code: self.cleaned_data.get(f"score_{component.code}") for component in self.components}

    def total(self) -> Decimal | None:
        value = self.cleaned_data.get("total")
        return value if isinstance(value, Decimal) else None

    def passed(self) -> bool | None:
        return passed_value(self.cleaned_data.get("passed"))

    def proposal(self) -> dict[str, Any]:
        """The values of a correction request."""
        return {
            "scores": self.scores(),
            "total": self.total(),
            "passed": self.passed(),
            "note": self.cleaned_data.get("note") or None,
        }


class CorrectionRequestForm(ResultEntryForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["reason"] = reason_field()


class ExternalResultForm(UserForm):
    """Record an external result (original ``AssessmentResultResource`` ``external`` action)."""

    student_number = forms.CharField(label=_("Student number"), max_length=32, widget=UnfoldAdminTextInputWidget)
    assessment_type = forms.ModelChoiceField(
        label=pgettext_lazy("assessment", "Kind"),
        queryset=AssessmentType.objects.none(),
        widget=UnfoldAdminSelectWidget,
    )
    taken_date = forms.DateField(label=_("Taken on"), widget=UnfoldAdminSingleDateWidget)
    total = score_field(_("Total"), None, False)
    level = forms.CharField(label=_("Level"), max_length=32, required=False, widget=UnfoldAdminTextInputWidget)
    passed = forms.ChoiceField(label=_("Passed"), widget=UnfoldAdminSelectWidget)
    certificate_number = forms.CharField(
        label=_("Certificate number"), max_length=64, required=False, widget=UnfoldAdminTextInputWidget
    )
    evidence = forms.FileField(label=_("Evidence"), required=False, widget=UnfoldAdminFileFieldWidget)
    note = note_field()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["assessment_type"].queryset = AssessmentType.objects.filter(  # type: ignore[attr-defined]
            is_active=True, allows_external=True
        ).order_by("sort_order", "code")
        self.fields["passed"].choices = [choice for choice in passed_choices() if choice[0]]  # type: ignore[attr-defined]

    def clean_taken_date(self) -> Any:
        taken = self.cleaned_data["taken_date"]
        if taken > timezone.localdate():
            raise forms.ValidationError(_("The date cannot be in the future."))
        return taken

    def clean_evidence(self) -> Any:
        upload = self.cleaned_data.get("evidence")
        if upload is not None and upload.size > EVIDENCE_MAX_SIZE:
            raise forms.ValidationError(
                _("The file is too big (%(size)s bytes, at most %(limit)s).")
                % {
                    "size": upload.size,
                    "limit": EVIDENCE_MAX_SIZE,
                }
            )
        return upload


def registration_subtitle(registration: AssessmentRegistration) -> str:
    record = registration.student_record
    return f"{registration.session.label()} · {record.student_number} {record.person.display_name()}"
