"""Factories for sections (original ``Database\\Factories\\Offering\\SectionFactory``).

Draft sections of a course in the full-term session of a published term. Meetings and
instructors are added through the actions or directly in tests::

    SectionFactory(term=term)                 # original inTerm($term)
    SectionFactory(course=course, published=True)
"""

from __future__ import annotations

import factory

from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section
from tests.factories.curriculum import CourseFactory
from tests.factories.term import TermFactory


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Section

    term = factory.SubFactory(TermFactory, published=True)
    session = factory.LazyAttribute(lambda section: section.term.full_term_session())
    course = factory.SubFactory(CourseFactory)
    version = factory.LazyAttribute(lambda section: section.course.versions.order_by("effective_start_date").first())
    section_code = factory.Sequence(lambda n: f"{n % 100:02d}")
    org_unit = factory.LazyAttribute(lambda section: section.course.org_unit)
    capacity = 40

    class Params:
        published = factory.Trait(status=SectionStatus.PUBLISHED)
