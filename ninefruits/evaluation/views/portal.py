"""Course evaluation in the portal (original Livewire ``Evaluations`` and ``SectionEvaluation``).

Evaluations (``/portal/evaluations/``, students; legacy counsel/student*.php): the courses open for
evaluation and, with ``?enrollment=<id>``, the questionnaire. Answers are anonymous and final once
submitted. The form posts to the same page; a submission that succeeds keeps its message for the
next page and redirects to the list, one that fails shows the questionnaire again with what was
entered. With HTMX the block ``#evaluations`` is swapped (``hx-confirm`` asks first).

Results (``/portal/sections/<id>/evaluation/``): a section's results for its instructors after
publication and for staff with evaluation access (legacy counsel/professor_view.php showed any
section's results and comments to any professor, unescaped).

Also the results column of the teaching page and the grade page's hidden terms (an open,
unfinished evaluation hides that term's grades, setting ``grades_require_evaluation``)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext, pgettext_lazy
from django.views import View

from ninefruits.evaluation.actions import SubmitEvaluation
from ninefruits.evaluation.models import TermEvaluation
from ninefruits.evaluation.services import EvaluationResults, EvaluationTasks
from ninefruits.offering.models import Section

FLASH_KEY = "evaluation.flash"
ANSWER_PREFIX = "answer-"


def _int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except TypeError, ValueError:
        return None


# -- hooks into other screens ---------------------------------------------------------------------
def _published_term_ids(request: HttpRequest) -> set[int]:
    cached = getattr(request, "_evaluation_published_terms", None)
    if cached is None:
        cached = set(
            TermEvaluation.objects.filter(results_published_at__isnull=False).values_list("term_id", flat=True)
        )
        request._evaluation_published_terms = cached  # type: ignore[attr-defined]
    return cached


def register_teaching_column() -> None:
    """The results link on the portal teaching page (original ``my-teaching``): once the term's
    results are published."""
    from ninefruits.offering.teaching import register_column

    def render_link(request: HttpRequest, section: Any) -> str:
        if section.term_id in _published_term_ids(request):
            return format_html(
                '<a href="{}" class="underline">{}</a>',
                reverse("portal:evaluation_results", args=[section.pk]),
                pgettext("evaluation", "Results"),
            )
        return format_html('<span class="text-zinc-500">{}</span>', _("Not published"))

    register_column("evaluation", gettext_lazy("Course evaluation results"), render_link, order=40)


def _hidden_terms(record: Any) -> list[int]:
    return EvaluationTasks().blocked_term_ids(record)


def _hidden_notice(term: Any) -> str:
    return _("The grades of %(term)s show after you finish its course evaluation.") % {"term": term.name}


def register_grade_hiding() -> None:
    """The grades of a term whose evaluation is open and unfinished stay hidden on the grade
    page and the transcript (original ``EvaluationTasks::blockedTermIds`` in ``MyGrades`` and
    ``TranscriptController::own``)."""
    from ninefruits.grading.services.report import register_hidden_terms

    register_hidden_terms(
        "evaluation",
        _hidden_terms,
        notice=_hidden_notice,
        link=("portal:evaluations", pgettext_lazy("evaluation.portal", "Course evaluation")),
    )


# -- student evaluations --------------------------------------------------------------------------
class EvaluationsView(LoginRequiredMixin, View):
    template_name = "evaluation/portal/evaluations.html"

    def _record(self, request: HttpRequest) -> Any:
        from ninefruits.person.services import CurrentStudentRecord

        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        return record

    def get(self, request: HttpRequest) -> HttpResponse:
        record = self._record(request)
        flash = request.session.pop(FLASH_KEY, None) or {"tone": "info", "messages": []}
        return render(request, self.template_name, self._context(record, _int(request.GET.get("enrollment")), flash))

    def post(self, request: HttpRequest) -> HttpResponse:
        record = self._record(request)
        tasks = EvaluationTasks()
        enrollment_id = _int(request.POST.get("enrollment_id"))
        enrollment = next((e for e in tasks.open(record) if e.pk == enrollment_id), None)
        if enrollment is None:
            raise Http404
        answers = {
            key[len(ANSWER_PREFIX) :]: value for key, value in request.POST.items() if key.startswith(ANSWER_PREFIX)
        }
        try:
            SubmitEvaluation(tasks)(enrollment, answers, request.user)
        except ValidationError as error:
            flash = {"tone": "error", "messages": [str(message) for message in error.messages]}
            context = self._context(record, enrollment.pk, flash, answers)
            return render(request, self.template_name, context)
        request.session[FLASH_KEY] = {"tone": "success", "messages": [_("Thank you. Your evaluation was submitted.")]}
        return HttpResponseRedirect(reverse("portal:evaluations"))

    def _context(
        self,
        record: Any,
        enrollment_id: int | None,
        flash: dict[str, Any],
        posted: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        tasks = EvaluationTasks()
        found = tasks.open(record)
        done = tasks.done_ids(found)
        selected = None
        if enrollment_id is not None and enrollment_id not in done:
            selected = next((enrollment for enrollment in found if enrollment.pk == enrollment_id), None)
        form = None
        questions: list[dict[str, Any]] = []
        if selected is not None:
            evaluation = TermEvaluation.objects.select_related("form").filter(term_id=selected.term_id).first()
            form = evaluation.form if evaluation is not None else None
        if form is not None:
            category = None
            for number, question in enumerate(form.ordered_questions(), start=1):
                label = str(question.category or "")
                questions.append(
                    {
                        "question": question,
                        "number": number,
                        "heading": label if label and label != category else "",
                        "value": (posted or {}).get(str(question.pk), ""),
                    }
                )
                if label:
                    category = label
        return {
            "title": pgettext("evaluation.portal", "Course evaluation"),
            "rows": [{"enrollment": enrollment, "done": enrollment.pk in done} for enrollment in found],
            "selected": selected,
            "form": form,
            "questions": questions,
            "points": list(range(1, form.scale_points + 1)) if form is not None else [],
            "flash": flash,
            "answer_prefix": ANSWER_PREFIX,
        }


# -- section results ------------------------------------------------------------------------------
class SectionEvaluationView(LoginRequiredMixin, View):
    template_name = "evaluation/portal/section_evaluation.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = get_object_or_404(Section.objects.select_related("course", "version", "term"), pk=pk)
        results = EvaluationResults()
        if not results.can_view(section, request.user):
            raise PermissionDenied
        result = results.for_section(section)
        form = result.term_evaluation.form if result.shown and result.term_evaluation is not None else None
        rows = []
        comment_sections = []
        for number, question in enumerate(result.form_questions, start=1):
            if question.pk in result.questions:
                rows.append({"question": question, "number": number, "result": result.questions[question.pk]})
            if question.pk in result.comments:
                comment_sections.append({"question": question, "comments": result.comments[question.pk]})
        context = {
            "title": f"{_('Course evaluation results')} {section.label()}",
            "section": section,
            "result": result,
            "form": form,
            "points": list(range(1, form.scale_points + 1)) if form is not None else [],
            "rows": rows,
            "comment_sections": comment_sections,
            "published": result.term_evaluation is not None and result.term_evaluation.is_published,
        }
        return render(request, self.template_name, context)
