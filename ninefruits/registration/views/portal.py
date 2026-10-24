"""Student registration in the portal (original Livewire ``Registration`` and its views):
term choice, window state, credits against the limit, the student timetable, registrations with
drop or withdraw, the waitlist, the cart and section search with register, add to cart and join
waitlist.

GET renders the page (``?term=&q=``); the search box reloads only the results with HTMX
(partial ``results``). Buttons are forms: POST runs the action, keeps the messages for the next
page and redirects back, so the page works without JavaScript; with HTMX the whole registration
block is swapped. Registration actions are limited to 30 a minute per user (porting-plan 10.7)."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch, Q
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.views import View
from django_ratelimit.core import is_ratelimited

from ninefruits.i18n.fields import I18nSearchText
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section, SectionInstructor, SectionMeeting
from ninefruits.offering.services import Timetable, room_label, summary
from ninefruits.person.services import CurrentStudentRecord
from ninefruits.registration.actions import DropEnrollment, EnrollStudent, LeaveWaitlist, ManageCart
from ninefruits.registration.data import EnrollOptions, RegistrationOutcome
from ninefruits.registration.enums import AttemptOutcome, EnrollmentStatus, WaitlistStatus
from ninefruits.registration.models import CartItem, CreditLimitPolicy, Enrollment, WaitlistEntry
from ninefruits.registration.rules.credit_limit import credits_text
from ninefruits.registration.services.seat_allocator import SeatAllocator
from ninefruits.registration.services.waitlists import position as waitlist_position
from ninefruits.registration.services.waitlists import waiting_counts
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import Term
from ninefruits.term.services import TermResolver

FLASH_KEY = "registration.flash"
RATE = "30/m"
SEARCH_LIMIT = 30


def _int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except TypeError, ValueError:
        return None


class RegistrationView(LoginRequiredMixin, View):
    template_name = "registration/portal/registration.html"

    # -- helpers -----------------------------------------------------------------------------------
    def _record(self, request: HttpRequest) -> Any:
        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        return record

    def _terms(self, record: Any) -> list[Term]:
        """Terms that are running or coming, and terms the student has registrations in."""
        today = timezone.localdate()
        return list(
            Term.objects.filter(status=TermStatus.PUBLISHED)
            .filter(
                Q(end_date__gte=today) | Q(pk__in=Enrollment.objects.filter(student_record=record).values("term_id"))
            )
            .order_by("start_date")
        )

    def _default_term_id(self, record: Any, terms: list[Term], resolver: TermResolver) -> int | None:
        for window_type in (TermWindowType.REGISTRATION, TermWindowType.REGISTRATION_CART):
            open_terms = resolver.terms_open_for(window_type, record)
            if open_terms:
                return int(open_terms[0].pk)
        return int(terms[0].pk) if terms else None

    def _back(self, request: HttpRequest, term_id: int | None, search: str) -> HttpResponse:
        query = {key: value for key, value in (("term", term_id), ("q", search)) if value not in (None, "")}
        url = reverse("portal:registration") + (f"?{urlencode(query)}" if query else "")
        return HttpResponseRedirect(url)

    def _say(self, request: HttpRequest, messages: list[str | None], tone: str) -> None:
        request.session[FLASH_KEY] = {
            "tone": tone,
            "messages": [str(message) for message in messages if message],
        }

    # -- GET ---------------------------------------------------------------------------------------
    def get(self, request: HttpRequest) -> HttpResponse:
        record = self._record(request)
        resolver = TermResolver()
        terms = self._terms(record)
        term_id = _int(request.GET.get("term")) or self._default_term_id(record, terms, resolver)
        term = next((t for t in terms if t.pk == term_id), None) or (
            Term.objects.filter(pk=term_id).first() if term_id else None
        )
        search = (request.GET.get("q") or "").strip()
        context = self._context(request, record, terms, term, search, resolver)
        if request.headers.get("HX-Request") and request.GET.get("partial") == "results":
            return render(request, f"{self.template_name}#results", context)
        return render(request, self.template_name, context)

    def _context(
        self,
        request: HttpRequest,
        record: Any,
        terms: list[Term],
        term: Term | None,
        search: str,
        resolver: TermResolver,
    ) -> dict[str, Any]:
        flash = request.session.pop(FLASH_KEY, None) or {"tone": "info", "messages": []}
        context: dict[str, Any] = {
            "title": _("Registration"),
            "record": record,
            "terms": terms,
            "term": term,
            "search": search,
            "flash": flash,
        }
        if term is None:
            return context

        now = timezone.now()
        registration_terms = {t.pk for t in resolver.terms_open_for(TermWindowType.REGISTRATION, record, now)}
        cart_terms = {t.pk for t in resolver.terms_open_for(TermWindowType.REGISTRATION_CART, record, now)}
        add_drop = resolver.open_windows(TermWindowType.ADD_DROP, now)
        withdrawal = resolver.open_windows(TermWindowType.WITHDRAWAL, now)

        def session_open(windows: list[Any], session_id: int) -> bool:
            return any(w.session_id == session_id and w.eligibility.matches(record) for w in windows)

        meetings = Prefetch(
            "section__meetings",
            queryset=SectionMeeting.objects.select_related("room__building").order_by("weekday", "start_time"),
        )
        enrollments = sorted(
            Enrollment.objects.visible_to(request.user)
            .filter(
                student_record=record, term=term, status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.WITHDRAWN]
            )
            .select_related("section__course", "section__version", "section__session")
            .prefetch_related(meetings),
            key=lambda e: e.section.label(),
        )
        active = [e for e in enrollments if e.status == EnrollmentStatus.ENROLLED]
        rows = []
        for enrollment in enrollments:
            is_enrolled = enrollment.status == EnrollmentStatus.ENROLLED
            can_drop = is_enrolled and (
                enrollment.term_id in registration_terms or session_open(add_drop, enrollment.section.session_id)
            )
            can_withdraw = is_enrolled and not can_drop and session_open(withdrawal, enrollment.section.session_id)
            rows.append(
                {
                    "enrollment": enrollment,
                    "label": enrollment.section.label(),
                    "title": str(enrollment.section.version.title or ""),
                    "credits": credits_text(enrollment.credits),
                    "status": EnrollmentStatus(enrollment.status).label,
                    "is_enrolled": is_enrolled,
                    "schedule": summary(enrollment.section.meetings.all()),
                    "can_drop": can_drop,
                    "can_withdraw": can_withdraw,
                }
            )
        credits = sum((Decimal(e.credits) for e in active if e.counts_toward_credit_limit), Decimal(0))
        policy = CreditLimitPolicy.applicable_to(record, term.term_type_id)
        labels = {e.section_id: e.section.label() for e in active}
        timetable = Timetable().build(
            [meeting for e in active for meeting in e.section.meetings.all()],
            lambda meeting: (labels.get(meeting.section_id, ""), room_label(meeting)),
        )
        waitlist = [
            {"entry": entry, "label": entry.section.label(), "position": waitlist_position(entry)}
            for entry in WaitlistEntry.objects.visible_to(request.user)
            .filter(student_record=record, status=WaitlistStatus.WAITING, section__term=term)
            .select_related("section__course")
        ]
        cart = [
            {
                "item": item,
                "label": item.section.label(),
                "title": str(item.section.version.title or ""),
                "credits": credits_text(item.section.version.credits),
            }
            for item in CartItem.objects.visible_to(request.user)
            .filter(student_record=record, term=term)
            .select_related("section__course", "section__version")
            .order_by("id")
        ]
        next_window = resolver.next_window(TermWindowType.REGISTRATION, record, now)
        context.update(
            {
                "registration_open": term.pk in registration_terms,
                "cart_open": term.pk in cart_terms,
                "opens_at": (
                    formats.date_format(timezone.localtime(next_window.opens_at, resolver.zone()), "DATETIME_FORMAT")
                    if next_window is not None
                    else None
                ),
                "rows": rows,
                "active_count": len(active),
                "credits": credits_text(credits),
                "limit": credits_text(policy.max_credits) if policy is not None else None,
                "timetable": timetable,
                "waitlist": waitlist,
                "cart": cart,
                "results": self._results(request, term, search, now),
            }
        )
        return context

    def _results(self, request: HttpRequest, term: Term, search: str, now: Any) -> list[dict[str, Any]]:
        if len(search) < 2:
            return []
        matches = (
            Section.objects.annotate(_search=I18nSearchText("version__title"))
            .filter(Q(course__code__istartswith=search) | Q(_search__icontains=search))
            .values("pk")
        )
        sections = (
            Section.objects.visible_to(request.user)
            .filter(status=SectionStatus.PUBLISHED, term=term, pk__in=matches)
            .select_related("course", "version", "session")
            .prefetch_related(
                Prefetch(
                    "instructor_assignments",
                    queryset=SectionInstructor.objects.select_related("instructor__person").order_by("id"),
                ),
                Prefetch(
                    "meetings",
                    queryset=SectionMeeting.objects.select_related("room__building").order_by("weekday", "start_time"),
                ),
                "seat_groups",
            )
            .order_by("course__code", "section_code")[:SEARCH_LIMIT]
        )
        sections = list(sections)
        waiting = waiting_counts([section.pk for section in sections])
        seats = SeatAllocator()
        rows = []
        for section in sections:
            free = seats.availability(section, now, list(section.seat_groups.all()))
            rows.append(
                {
                    "section": section,
                    "label": section.label(),
                    "title": str(section.version.title or ""),
                    "credits": credits_text(section.version.credits),
                    "instructors": ", ".join(
                        a.instructor.person.display_name() for a in section.instructor_assignments.all()
                    ),
                    "schedule": summary(section.meetings.all()),
                    "general": free.general,
                    "reserved": free.reserved,
                    "capacity": section.capacity,
                    "can_waitlist": section.waitlist_capacity > waiting.get(section.pk, 0) and free.general == 0,
                }
            )
        return rows

    # -- POST --------------------------------------------------------------------------------------
    ACTIONS = (
        "enroll",
        "waitlist",
        "add_to_cart",
        "remove_from_cart",
        "submit_cart",
        "drop",
        "withdraw",
        "leave_waitlist",
    )
    LIMITED = frozenset({"enroll", "waitlist", "add_to_cart", "submit_cart"})

    def post(self, request: HttpRequest) -> HttpResponse:
        record = self._record(request)
        action = request.POST.get("action", "")
        if action not in self.ACTIONS:
            raise Http404
        term_id = _int(request.POST.get("term"))
        search = (request.POST.get("q") or "").strip()
        if action in self.LIMITED and is_ratelimited(
            request, group="registration", key="user", rate=RATE, method="POST", increment=True
        ):
            self._say(request, [_("Too many requests. Wait a minute and try again.")], "error")
            return self._back(request, term_id, search)
        handler: Callable[[HttpRequest, Any, int | None], None] = getattr(self, f"_{action}")
        try:
            handler(request, record, term_id)
        except ValidationError as error:
            self._say(request, list(error.messages), "error")
        except PermissionDenied:
            raise Http404 from None
        return self._back(request, term_id, search)

    def _section(self, request: HttpRequest, term_id: int | None) -> Section:
        return get_object_or_404(
            Section.objects.visible_to(request.user), pk=_int(request.POST.get("section_id")), term_id=term_id
        )

    def _enroll(self, request: HttpRequest, record: Any, term_id: int | None, waitlist: bool = False) -> None:
        outcome = EnrollStudent().handle(
            record, self._section(request, term_id), request.user, EnrollOptions(waitlist_if_full=waitlist)
        )
        self._show(request, outcome)

    def _waitlist(self, request: HttpRequest, record: Any, term_id: int | None) -> None:
        self._enroll(request, record, term_id, waitlist=True)

    def _show(self, request: HttpRequest, outcome: RegistrationOutcome) -> None:
        if outcome.outcome == AttemptOutcome.SUCCEEDED:
            self._say(request, [_("Registered."), *outcome.messages()], "success")
        elif outcome.outcome == AttemptOutcome.WAITLISTED:
            self._say(request, [result.message for result in outcome.evaluation.results[-1:]], "info")
        else:
            self._say(request, list(outcome.messages()), "error")

    def _add_to_cart(self, request: HttpRequest, record: Any, term_id: int | None) -> None:
        evaluation = ManageCart().add(record, self._section(request, term_id), request.user)
        self._say(
            request,
            [_("Added to the cart."), *evaluation.blocking_messages(), *evaluation.warnings()],
            "warning" if evaluation.is_blocked() else "success",
        )

    def _remove_from_cart(self, request: HttpRequest, record: Any, term_id: int | None) -> None:
        section_id = _int(request.POST.get("section_id"))
        if section_id is not None:
            ManageCart().remove(record, section_id, request.user)

    def _submit_cart(self, request: HttpRequest, record: Any, term_id: int | None) -> None:
        term = get_object_or_404(Term, pk=term_id)
        lines = []
        outcomes = ManageCart().submit(record, term, request.user)
        labels = {s.pk: s.label() for s in Section.objects.filter(pk__in=list(outcomes)).select_related("course")}
        for section_id, outcome in outcomes.items():
            result = _("Registered.") if outcome.succeeded() else " ".join(outcome.messages())
            lines.append(f"{labels.get(section_id, '')}: {result}")
        self._say(request, lines or [_("The cart is empty.")], "info")

    def _enrollment(self, request: HttpRequest, record: Any) -> Enrollment:
        return get_object_or_404(
            Enrollment.objects.visible_to(request.user).select_related("section", "student_record"),
            pk=_int(request.POST.get("enrollment_id")),
            student_record=record,
        )

    def _drop(self, request: HttpRequest, record: Any, term_id: int | None) -> None:
        DropEnrollment().drop(self._enrollment(request, record), request.user)
        self._say(request, [_("Dropped.")], "success")

    def _withdraw(self, request: HttpRequest, record: Any, term_id: int | None) -> None:
        DropEnrollment().withdraw(self._enrollment(request, record), request.user)
        self._say(request, [_("Withdrawn.")], "success")

    def _leave_waitlist(self, request: HttpRequest, record: Any, term_id: int | None) -> None:
        entry = get_object_or_404(
            WaitlistEntry.objects.visible_to(request.user).select_related("section", "student_record"),
            pk=_int(request.POST.get("entry_id")),
            student_record=record,
        )
        LeaveWaitlist().handle(entry, request.user)
