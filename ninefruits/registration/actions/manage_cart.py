"""The cart (original ``ManageCart``, porting-plan 10.7): students collect sections while the
cart window (or registration) is open and see every rule's result in advance; only the window,
the section being published and the same course twice stop an item. When registration opens
they submit the cart at once instead of searching under load."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError

from ninefruits.offering.models import Section
from ninefruits.registration.data import EnrollOptions, RegistrationContext, RegistrationOutcome, RuleEvaluation
from ninefruits.registration.enums import AttemptAction, RuleCode
from ninefruits.registration.models import CartItem
from ninefruits.registration.services.rule_engine import RegistrationRuleEngine

from .enroll_student import EnrollStudent, now

#: Failed rules that keep a section out of the cart.
STOPPING = (RuleCode.WINDOW, RuleCode.SECTION_OPEN, RuleCode.DUPLICATE_COURSE)


class ManageCart:
    def __init__(self, engine: RegistrationRuleEngine | None = None, enroll: EnrollStudent | None = None) -> None:
        self.engine = engine or RegistrationRuleEngine()
        self.enroll = enroll or EnrollStudent(self.engine)

    def add(self, record: Any, section: Section, student: Any) -> RuleEvaluation:
        """Returns the pre-check of the section for the student."""
        self._authorize(record, student)
        evaluation = self.engine.evaluate(RegistrationContext(record, section, AttemptAction.CART, now(), student))
        stopping = [result for result in evaluation.blocking() if result.code in STOPPING]
        if stopping:
            raise ValidationError({"section": [str(result.message) for result in stopping]})
        CartItem.objects.get_or_create(
            student_record_id=record.pk, section_id=section.pk, defaults={"term_id": section.term_id}
        )
        return evaluation

    def remove(self, record: Any, section_id: int, student: Any) -> None:
        self._authorize(record, student)
        CartItem.objects.filter(student_record_id=record.pk, section_id=section_id).delete()

    def submit(
        self, record: Any, term: Any, student: Any, waitlist_if_full: bool = False
    ) -> dict[int, RegistrationOutcome]:
        """Registers every section in the cart for the term, in the order they were added."""
        self._authorize(record, student)
        outcomes: dict[int, RegistrationOutcome] = {}
        items = CartItem.objects.filter(student_record_id=record.pk, term_id=term.pk).select_related("section")
        for item in items.order_by("id"):
            outcomes[item.section_id] = self.enroll.handle(
                record, item.section, student, EnrollOptions(waitlist_if_full=waitlist_if_full)
            )
        return outcomes

    def _authorize(self, record: Any, student: Any) -> None:
        if getattr(student, "person_id", None) is None or student.person_id != record.person_id:
            raise PermissionDenied
