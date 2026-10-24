"""Forms of the graduation admin screens."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import UnfoldAdminDateWidget, UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget

YEAR_LEVELS = [(level, str(level)) for level in range(1, 7)]


def reason_field(label: Any = None, required: bool = True) -> forms.CharField:
    return forms.CharField(
        label=label or pgettext_lazy("common", "Reason"),
        max_length=1000,
        required=required,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


class RunAuditsForm(forms.Form):
    """Original "Run audits" header action: the term the audits belong to and the year level."""

    term = forms.TypedChoiceField(
        label=_("Term"), coerce=int, required=False, empty_value=None, widget=UnfoldAdminSelectWidget
    )
    min_year_level = forms.TypedChoiceField(
        label=_("From year level"),
        coerce=int,
        required=False,
        empty_value=None,
        choices=[("", "---------"), *YEAR_LEVELS],
        initial=4,
        widget=UnfoldAdminSelectWidget,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        from ninefruits.registration.admin.common import term_choices

        super().__init__(*args, **kwargs)
        self.fields["term"].choices = [("", "---------"), *term_choices()]  # type: ignore[attr-defined]


class GraduateForm(forms.Form):
    """Original "Graduate" bulk action: the graduation date and the reason."""

    graduation_date = forms.DateField(label=_("Graduation date"), widget=UnfoldAdminDateWidget)
    reason = reason_field()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.initial.setdefault("graduation_date", timezone.localdate())


class WaiverRequestForm(forms.Form):
    """Original "Waive a requirement" on a student record: the requirements of the record's
    program for its catalog year, and the reason."""

    requirement = forms.TypedChoiceField(label=_("Requirements"), coerce=int, widget=UnfoldAdminSelectWidget)
    reason = reason_field()

    def __init__(self, *args: Any, record: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["requirement"].choices = requirement_choices(record)  # type: ignore[attr-defined]


def requirement_name(requirement: Any) -> str:
    """The requirement's name, else its examination kind, else its kind (original waiver screens)."""
    from ninefruits.curriculum.enums import RequirementKind

    if requirement.name:
        return str(requirement.name)
    if requirement.assessment_type_id is not None:
        return str(requirement.assessment_type.name)
    return str(RequirementKind(requirement.kind).label)


def requirement_choices(record: Any) -> list[tuple[int, str]]:
    from ninefruits.curriculum.enums import ProgramRole
    from ninefruits.curriculum.models import CurriculumRequirementSet

    choices: list[tuple[int, str]] = []
    sets = (
        CurriculumRequirementSet.objects.filter(program_id=record.program_id)
        .for_catalog_year(record.catalog_year)
        .prefetch_related("requirements__assessment_type")
    )
    for requirement_set in sets:
        role = ProgramRole(requirement_set.program_role).label
        for requirement in requirement_set.requirements.all():
            choices.append((requirement.pk, f"{role} · {requirement_name(requirement)}"))
    return choices
