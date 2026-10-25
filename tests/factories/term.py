"""Factories for academic years, terms, sessions, windows and class periods (original
``Database\\Factories\\Term``)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

import factory
from django.utils import timezone

from ninefruits.core.targeting import TargetCriteria
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import AcademicYear, Term, TermSession, TermType, TermWindow, TimeSlot


def academic_year_for(year: int, **kwargs: Any) -> AcademicYear:
    """Original ``AcademicYearFactory::forYear``."""
    return AcademicYearFactory(
        code=str(year),
        name={"en": f"{year} academic year", "ko": f"{year}학년도"},
        start_date=date(year, 3, 1),
        end_date=date(year + 1, 3, 1) - timedelta(days=1),
        **kwargs,
    )


class AcademicYearFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AcademicYear
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: str(1900 + n))
    name = factory.LazyAttribute(lambda year: {"en": f"{year.code} academic year"})
    start_date = factory.LazyAttribute(lambda year: date(int(year.code), 3, 1))
    end_date = factory.LazyAttribute(lambda year: date(int(year.code) + 1, 2, 28))


class TermTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TermType

    code = factory.Sequence(lambda n: f"termtype{n}")
    name = factory.Sequence(lambda n: {"en": f"Term type {n}"})


class TermFactory(factory.django.DjangoModelFactory):
    """``TermFactory(published=True)``; dates with ``start_date``/``end_date``."""

    class Meta:
        model = Term

    academic_year = factory.SubFactory(AcademicYearFactory)
    term_type = factory.SubFactory(TermTypeFactory)
    code = factory.Sequence(lambda n: f"T{n:04d}-XX")
    name = factory.Sequence(lambda n: {"en": f"Term {n}"})
    start_date = date(2026, 3, 2)
    end_date = date(2026, 6, 20)
    status = TermStatus.PLANNED

    class Params:
        published = factory.Trait(status=TermStatus.PUBLISHED)


class TermSessionFactory(factory.django.DjangoModelFactory):
    """Original ``within($term, $start, $end, $code)``: ``TermSessionFactory(term=term,
    start_date=..., end_date=..., code="A")``."""

    class Meta:
        model = TermSession

    term = factory.SubFactory(TermFactory)
    code = factory.Sequence(lambda n: f"S{n:02d}")
    name = {"en": "First half", "ko": "전반기", "zh-hans": "前半学期"}
    start_date = factory.LazyAttribute(lambda session: session.term.start_date)
    end_date = factory.LazyAttribute(lambda session: session.term.start_date + timedelta(weeks=8))


def _now() -> datetime:
    return timezone.now().replace(microsecond=0)


class TermWindowFactory(factory.django.DjangoModelFactory):
    """``TermWindowFactory(term=..., window_type=TermWindowType.X, opens_at=..., closes_at=...,
    eligibility=TargetCriteria(...))``."""

    class Meta:
        model = TermWindow

    term = factory.SubFactory(TermFactory, published=True)
    window_type = TermWindowType.REGISTRATION
    opens_at = factory.LazyFunction(lambda: _now() - timedelta(days=1))
    closes_at = factory.LazyFunction(lambda: _now() + timedelta(weeks=1))
    eligibility = factory.LazyFunction(TargetCriteria)


class TimeSlotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TimeSlot

    code = factory.Sequence(lambda n: str(n + 1))
    name = {"en": "Period"}
    start_time = time(9, 0)
    end_time = time(9, 50)
    weekdays = [1, 2, 3, 4, 5]
