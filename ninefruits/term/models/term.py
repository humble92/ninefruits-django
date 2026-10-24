"""Academic years, term types, terms and term sessions (original ``App\\Models\\Term\\*``,
ADR 0006).

There is no global "current term" flag: ``TermResolver`` answers per business question. The
database refuses overlapping academic years and overlapping terms of the same type (GiST
exclusion constraints) and sessions outside their term (trigger
``term_sessions_before_write_within_term``)."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.term.enums import TermStatus


class AcademicYear(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"))

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "academic_years"
        ordering = ["start_date"]
        verbose_name = _("academic year")
        verbose_name_plural = _("academic years")

    def __str__(self) -> str:
        return str(self.name or self.code)


class TermType(TimeStampedModel):
    """E.g. spring, summer, fall, winter. Regular terms and intensive terms follow different
    rules later (credit limits)."""

    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    is_regular = models.BooleanField(
        _("Regular term"),
        default=True,
        help_text=_(
            "Regular terms (e.g. spring, fall) and intensive sessions follow different rules later, "
            "such as credit limits."
        ),
    )
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "term_types"
        ordering = ["sort_order", "code"]
        verbose_name = _("term type")
        verbose_name_plural = _("term types")

    def __str__(self) -> str:
        return str(self.name or self.code)


class TermQuerySet(VisibleQuerySet):
    pass


class Term(TimeStampedModel):
    """A term (semester, quarter, session). The code (e.g. 2026-FA) is for display only and
    carries no business meaning. Every term has a full-term session with the term's dates; it
    follows date changes. Shorter sessions must stay inside the term."""

    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.RESTRICT, related_name="terms", verbose_name=_("Academic year")
    )
    term_type = models.ForeignKey(
        TermType, on_delete=models.RESTRICT, related_name="terms", verbose_name=_("Term type")
    )
    code = models.CharField(
        pgettext_lazy("reference", "Code"),
        max_length=32,
        unique=True,
        help_text=_("For display only, e.g. 2026-FA. The code carries no business meaning."),
    )
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    start_date = models.DateField(_("Classes start"))
    end_date = models.DateField(_("Classes end"))
    status = models.CharField(
        pgettext_lazy("reference", "Status"), max_length=32, choices=TermStatus.choices, default=TermStatus.PLANNED
    )

    objects = TermQuerySet.as_manager()

    class Meta:
        db_table = "terms"
        ordering = ["-start_date"]
        verbose_name = _("term")
        verbose_name_plural = _("terms")
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "term_type"], name="terms_academic_year_id_term_type_id_unique"
            ),
        ]

    def __str__(self) -> str:
        return str(self.name or self.code)

    @property
    def type(self) -> TermType:
        return self.term_type

    @property
    def term_status(self) -> TermStatus:
        return TermStatus(self.status)

    def save(self, *args: Any, **kwargs: Any) -> None:
        creating = self._state.adding
        dates_changed = False
        if not creating:
            stored = Term.objects.filter(pk=self.pk).values_list("start_date", "end_date").first()
            dates_changed = stored is not None and stored != (self._date("start_date"), self._date("end_date"))
            if dates_changed:
                self._check_sessions_inside()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creating:
                TermSession.objects.create(
                    term=self,
                    code=TermSession.FULL_TERM_CODE,
                    name=TermSession.full_term_name(),
                    start_date=self.start_date,
                    end_date=self.end_date,
                    is_full_term=True,
                )
            elif dates_changed:
                TermSession.objects.filter(term=self, is_full_term=True).update(
                    start_date=self.start_date, end_date=self.end_date
                )

    def _date(self, name: str) -> Any:
        from datetime import date

        value = getattr(self, name)
        return date.fromisoformat(value) if isinstance(value, str) else value

    def _check_sessions_inside(self) -> None:
        outside = (
            TermSession.objects.filter(term_id=self.pk, is_full_term=False)
            .filter(models.Q(start_date__lt=self._date("start_date")) | models.Q(end_date__gt=self._date("end_date")))
            .exists()
        )
        if outside:
            raise ValidationError(
                {"start_date": _("Some sessions would fall outside the new dates. Change them first.")}
            )

    def full_term_session(self) -> TermSession:
        return TermSession.objects.get(term_id=self.pk, is_full_term=True)


class TermSession(TimeStampedModel):
    """A part of a term in which sections meet: the full term, a first or second half, an
    intensive block. Course deadlines (add/drop, withdrawal, grading, evaluation) are the
    session's windows, so every section follows its session."""

    FULL_TERM_CODE = "FULL"

    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="sessions")
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"))
    is_full_term = models.BooleanField(_("Full term"), default=False)
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "term_sessions"
        ordering = ["-is_full_term", "start_date", "sort_order"]
        verbose_name = _("session")
        verbose_name_plural = _("sessions")
        constraints = [
            models.UniqueConstraint(fields=["term", "code"], name="term_sessions_term_id_code_unique"),
        ]

    def __str__(self) -> str:
        return str(self.name or self.code)

    @staticmethod
    def full_term_name() -> dict[str, str]:
        """Name of the automatic full-term session in every language with a translation."""
        from ninefruits.institution.services.supported_locales import has_catalog

        names: dict[str, str] = {}
        for code, _label in settings.LANGUAGES:
            if code != settings.LANGUAGE_CODE and not has_catalog(code):
                continue
            with translation.override(code):
                text = str(_("Full term"))
            if code == settings.LANGUAGE_CODE or text != "Full term":
                names[code] = text
        return names or {"en": "Full term"}
