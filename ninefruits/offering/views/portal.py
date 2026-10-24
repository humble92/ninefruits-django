"""Portal pages of the offering (original Livewire ``CourseCatalog``, ``SectionDetail``,
``SyllabusEditor`` and ``MyTeaching``)."""

from __future__ import annotations

import math
from itertools import groupby
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef, Q
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language, pgettext
from django.utils.translation import gettext as _
from django.views import View

from ninefruits.curriculum.enums import GradingBasis, RequisiteKind
from ninefruits.i18n.fields import I18nSearchText
from ninefruits.offering import teaching
from ninefruits.offering.actions import UpdateSyllabus
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section, SectionMeeting, Syllabus
from ninefruits.offering.services import Timetable, room_label, summary
from ninefruits.organization.models import OrgUnit
from ninefruits.term.models import Term
from ninefruits.term.services import TermResolver

PAGE_SIZE = 25


def _instructor_names(section: Section) -> str:
    return ", ".join(assignment.instructor.person.display_name() for assignment in section.instructor_assignments.all())


def _prefetched(queryset: Any) -> Any:
    return queryset.select_related("course", "version__category", "session", "term").prefetch_related(
        "instructor_assignments__instructor__person", "meetings__room__building"
    )


def can_edit_syllabus(user: Any, section: Section) -> bool:
    return bool(user.has_perm("edit_syllabus", section))


class CourseCatalogView(LoginRequiredMixin, View):
    """Published sections of a term with times, rooms, instructors and syllabi. Students plan
    here before registration."""

    template_name = "offering/portal/catalog.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        term_id = _int(request.GET.get("term")) or default_catalog_term_id()
        search = (request.GET.get("q") or "").strip()
        unit_id = _int(request.GET.get("org_unit"))

        sections = Section.objects.visible_to(request.user).published().filter(term_id=term_id)
        if unit_id is not None:
            sections = sections.filter(org_unit_id=unit_id)
        if search:
            matches = (
                Section.objects.annotate(_search=I18nSearchText("version__title"))
                .filter(Q(course__code__istartswith=search) | Q(_search__icontains=search))
                .values("pk")
            )
            sections = sections.filter(pk__in=matches)
        sections = _prefetched(sections).order_by("course__code", "section_code")
        page = Paginator(sections, PAGE_SIZE).get_page(request.GET.get("page"))
        published = Syllabus.objects.filter(section_id__in=[s.pk for s in page], published_at__isnull=False)
        published_ids = set(published.values_list("section_id", flat=True))
        rows = []
        for section in page:
            row = _describe_light(section)
            row["has_syllabus"] = section.pk in published_ids
            rows.append(row)

        published_sections = Section.objects.filter(term_id=OuterRef("pk"), status=SectionStatus.PUBLISHED)
        terms = Term.objects.filter(Exists(published_sections)).order_by("-start_date")
        units = sorted(
            OrgUnit.objects.filter(pk__in=Section.objects.published().filter(term_id=term_id).values("org_unit_id")),
            key=lambda unit: str(unit.name or unit.code),
        )
        context = {
            "title": pgettext("offering", "Course catalog"),
            "terms": terms,
            "units": units,
            "term_id": term_id,
            "org_unit_id": unit_id,
            "search": search,
            "rows": rows,
            "page": page,
        }
        template = f"{self.template_name}#results" if request.headers.get("HX-Request") else self.template_name
        return render(request, template, context)


def _describe_light(section: Section) -> dict[str, Any]:
    meetings = list(section.meetings.all())
    return {
        "section": section,
        "label": section.label(),
        "title": str(section.version.title or ""),
        "credits": section.version.credits,
        "category": str(section.version.category.name) if section.version.category else "",
        "instructors": _instructor_names(section),
        "schedule": summary(meetings),
        "session": section.session,
    }


def _int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except TypeError, ValueError:
        return None


def default_catalog_term_id() -> int | None:
    in_session = TermResolver().in_session()
    if in_session:
        return int(in_session[0].pk)
    return (
        Term.objects.filter(start_date__gte=timezone.localdate())
        .order_by("start_date")
        .values_list("pk", flat=True)
        .first()
    )


class SectionDetailView(LoginRequiredMixin, View):
    """A section as students see it: course details, requisites, schedule and the published
    syllabus. Instructors and staff also see drafts."""

    template_name = "offering/portal/section_detail.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = get_object_or_404(_prefetched(Section.objects.all()), pk=pk)
        can_edit = can_edit_syllabus(request.user, section)
        if section.status != SectionStatus.PUBLISHED and not can_edit:
            raise Http404
        syllabus = Syllabus.objects.filter(section_id=section.pk).first()
        if syllabus is not None and syllabus.published_at is None and not can_edit:
            syllabus = None
        requisites = list(section.version.requisites.select_related("required_course").order_by("kind", "group_number"))
        groups = []
        for (kind, _number), items in groupby(requisites, key=lambda r: (r.kind, r.group_number)):
            courses = [item.required_course.code for item in items]
            groups.append(f"{RequisiteKind(kind).label}: {(' ' + _('or') + ' ').join(courses)}")
        context = {
            "title": section.label(),
            "section": section,
            "version": section.version,
            "grading_basis": GradingBasis(section.version.grading_basis).label,
            "instructors": _instructor_names(section),
            "schedule": summary(section.meetings.all()),
            "requisite_groups": groups,
            "can_edit": can_edit,
            "syllabus": syllabus,
            "syllabus_parts": _syllabus_parts(syllabus),
            "lms_links": _lms_links(section, request.user),
        }
        return render(request, self.template_name, context)


def _lms_links(section: Section, user: Any) -> list[dict[str, str]]:
    """The section's linked LMS courses: URL and label (Phase 12, original ``SectionDetail``)."""
    from ninefruits.lms.services import portal_links

    return portal_links(section, user)


def _part_labels() -> dict[str, str]:
    return {
        "overview": _("Overview"),
        "objectives": _("Learning objectives"),
        "materials": _("Textbooks and materials"),
        "policies": _("Course policies"),
    }


def _syllabus_parts(syllabus: Syllabus | None) -> list[dict[str, str]]:
    if syllabus is None:
        return []
    labels = _part_labels()
    return [
        {"key": key, "label": labels[key], "text": str(syllabus.content.get(key))}
        for key in Syllabus.PARTS
        if syllabus.content.get(key)
    ]


class SyllabusEditorView(LoginRequiredMixin, View):
    """Instructors of a section (and staff who manage it) write its syllabus."""

    template_name = "offering/portal/syllabus_editor.html"

    def _section(self, request: HttpRequest, pk: int) -> Section:
        section = get_object_or_404(Section.objects.select_related("course", "version", "term", "session"), pk=pk)
        if not can_edit_syllabus(request.user, section):
            raise PermissionDenied
        return section

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = self._section(request, pk)
        syllabus = Syllabus.objects.filter(section_id=section.pk).first()
        content: dict[str, Any] = {
            "overview": "",
            "objectives": "",
            "materials": "",
            "policies": "",
            "assessment": [],
            "weekly_plan": [],
        }
        content.update(
            {key: value for key, value in (syllabus.content if syllabus else {}).items() if value is not None}
        )
        if not content["weekly_plan"]:
            days = (section.session.end_date - section.session.start_date).days + 1
            weeks = max(1, min(30, math.ceil(days / 7)))
            content["weekly_plan"] = [{"week": week, "topic": ""} for week in range(1, weeks + 1)]
        language = syllabus.language if syllabus else (section.instruction_language or get_language() or "en")
        return self.render_editor(request, section, language, content, syllabus is not None and syllabus.is_published)

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = self._section(request, pk)
        language = (request.POST.get("language") or "").strip()
        published = request.POST.get("published") == "1"
        content: dict[str, Any] = {part: request.POST.get(part, "") for part in Syllabus.PARTS}
        content["assessment"] = [
            {"item": item, "weight": weight}
            for item, weight in zip(
                request.POST.getlist("assessment_item"), request.POST.getlist("assessment_weight"), strict=False
            )
        ]
        content["weekly_plan"] = [
            {"week": week, "topic": topic}
            for week, topic in zip(request.POST.getlist("week"), request.POST.getlist("topic"), strict=False)
        ]
        if "add_assessment" in request.POST:
            content["assessment"].append({"item": "", "weight": None})
            return self.render_editor(request, section, language, content, published)
        if "remove_assessment" in request.POST:
            index = _int(request.POST.get("remove_assessment"))
            if index is not None and 0 <= index < len(content["assessment"]):
                del content["assessment"][index]
            return self.render_editor(request, section, language, content, published)

        to_save = dict(content)
        to_save["weekly_plan"] = [week for week in content["weekly_plan"] if str(week["topic"]).strip()]
        to_save["assessment"] = [item for item in content["assessment"] if str(item["item"]).strip()]
        try:
            UpdateSyllabus()(section, language, to_save, request.user, published)
        except ValidationError as error:
            return self.render_editor(request, section, language, content, published, errors=error.message_dict)
        messages.success(request, _("Syllabus saved."))
        return HttpResponseRedirect(reverse("portal:syllabus_edit", args=[section.pk]))

    def render_editor(
        self,
        request: HttpRequest,
        section: Section,
        language: str,
        content: dict[str, Any],
        published: bool,
        errors: dict[str, list[str]] | None = None,
    ) -> HttpResponse:
        errors = errors or {}
        labels = _part_labels()
        context = {
            "title": f"{_('Edit syllabus')} {section.label()}",
            "section": section,
            "language": language,
            "published": published,
            "parts": [
                {"key": key, "label": labels[key], "value": content.get(key) or "", "errors": errors.get(key, [])}
                for key in Syllabus.PARTS
            ],
            "assessment": [
                {
                    **item,
                    "index": index,
                    "errors": errors.get(f"assessment.{index}.item", []) + errors.get(f"assessment.{index}.weight", []),
                }
                for index, item in enumerate(content.get("assessment") or [])
            ],
            "weekly_plan": [
                {
                    **week,
                    "errors": errors.get(f"weekly_plan.{index}.week", [])
                    + errors.get(f"weekly_plan.{index}.topic", []),
                }
                for index, week in enumerate(content.get("weekly_plan") or [])
            ],
            "errors": errors,
        }
        return render(request, self.template_name, context, status=422 if errors else 200)


class MyTeachingView(LoginRequiredMixin, View):
    """An instructor's sections and weekly timetable for a term, with links to the syllabi."""

    template_name = "offering/portal/teaching.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        person_id = getattr(request.user, "person_id", None)
        if person_id is None:
            raise Http404
        taught = Section.objects.taught_by(person_id)
        terms = list(Term.objects.filter(pk__in=taught.values("term_id")).order_by("start_date"))
        term_id = _int(request.GET.get("term"))
        if term_id is None and terms:
            today = timezone.localdate()
            upcoming = [term for term in terms if term.end_date >= today]
            term_id = (upcoming[0] if upcoming else terms[-1]).pk
        sections = sorted(
            Section.objects.taught_by(person_id)
            .filter(term_id=term_id)
            .exclude(status=SectionStatus.CANCELLED)
            .select_related("course", "version", "session")
            .prefetch_related("meetings__room__building"),
            key=lambda section: section.label(),
        )
        syllabi = {s.section_id: s for s in Syllabus.objects.filter(section_id__in=[s.pk for s in sections])}
        labels = {section.pk: section.label() for section in sections}
        meetings: list[SectionMeeting] = [meeting for section in sections for meeting in section.meetings.all()]
        timetable = Timetable().build(meetings, lambda m: (labels.get(m.section_id, ""), room_label(m)))
        extra_columns = teaching.columns()
        rows = []
        for section in sections:
            syllabus = syllabi.get(section.pk)
            if syllabus is not None and syllabus.is_published:
                status = pgettext("offering.syllabus", "Published")
            elif syllabus is not None:
                status = pgettext("offering", "Draft")
            else:
                status = _("Write")
            rows.append(
                {
                    "section": section,
                    "label": section.label(),
                    "title": str(section.version.title or ""),
                    "schedule": summary(section.meetings.all()) or "-",
                    "syllabus_status": status,
                    "extra": [column.render(request, section) for column in extra_columns],
                }
            )
        context = {
            "title": _("My teaching"),
            "terms": terms,
            "term_id": term_id,
            "rows": rows,
            "timetable": timetable,
            "extra_headers": [column.header for column in extra_columns],
        }
        return render(request, self.template_name, context)
