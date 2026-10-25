"""Rule sets, rule configuration and credit limit policies (original
``App\\Models\\Registration\\{RegistrationRuleSet,RegistrationRule,CreditLimitPolicy}``)."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.core.targeting import TargetCriteriaField, TargetSubject
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.registration.enums import RuleCode, RuleSeverity


class RegistrationRuleSet(TimeStampedModel):
    """The registration rules of a term, usually copied from the previous term and adjusted."""

    term = models.OneToOneField(
        "term.Term", on_delete=models.CASCADE, related_name="registration_rule_set", verbose_name=_("term")
    )
    copied_from_rule_set = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="copies",
        verbose_name=_("Copied from"),
    )
    note = models.TextField(pgettext_lazy("offering", "Note"), null=True, blank=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "registration_rule_sets"
        ordering = ["-term_id"]
        verbose_name = _("rule set")
        verbose_name_plural = _("registration rules")

    def __str__(self) -> str:
        return str(self.term.name) if self.term_id else ""


class RegistrationRule(TimeStampedModel):
    """Configuration of one rule in a term's rule set."""

    rule_set = models.ForeignKey(
        RegistrationRuleSet, on_delete=models.CASCADE, related_name="rules", db_column="registration_rule_set_id"
    )
    rule_code = models.CharField(_("Rule"), max_length=64, choices=RuleCode.choices)
    is_enabled = models.BooleanField(_("On"), default=True)
    severity = models.CharField(
        _("When not met"), max_length=8, choices=RuleSeverity.choices, default=RuleSeverity.BLOCK
    )
    allows_override = models.BooleanField(_("Overrides allowed"), default=True)
    #: JSON object; no parameters are stored as NULL, never as ``{}`` or ``[]``.
    parameters = models.JSONField(null=True, blank=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "registration_rules"
        ordering = ["id"]
        verbose_name = _("Rule")
        verbose_name_plural = _("Rules")
        constraints = [
            models.UniqueConstraint(
                fields=["rule_set", "rule_code"], name="registration_rules_registration_rule_set_id_rule_code_unique"
            ),
        ]

    def __str__(self) -> str:
        return str(RuleCode(self.rule_code).label)

    @property
    def registration_rule_set_id(self) -> int | None:
        return self.rule_set_id

    @property
    def code(self) -> RuleCode:
        return RuleCode(self.rule_code)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.parameters:
            self.parameters = None
        super().save(*args, **kwargs)


class CreditLimitPolicy(TimeStampedModel):
    """Credits a student may register for in a term (legacy rule by student number digits).
    Policies match by term type and eligibility (programs, units, admission years ...); the
    matching policy with the highest priority applies."""

    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    term_type = models.ForeignKey(
        "term.TermType",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("term type"),
    )
    eligibility = TargetCriteriaField(pgettext_lazy("registration", "Students"), null=True, blank=True)
    min_credits = models.DecimalField(
        pgettext_lazy("registration", "Minimum credits"), max_digits=4, decimal_places=1, null=True, blank=True
    )
    max_credits = models.DecimalField(_("Maximum credits"), max_digits=4, decimal_places=1)
    priority = models.IntegerField(
        _("Priority"), default=0, help_text=_("When several limits match a student, the highest priority applies.")
    )
    is_active = models.BooleanField(pgettext_lazy("registration.fields", "Active"), default=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "credit_limit_policies"
        ordering = ["-priority", "id"]
        verbose_name = _("credit limit")
        verbose_name_plural = _("credit limits")

    def __str__(self) -> str:
        return str(self.name or "")

    @classmethod
    def applicable_to(cls, student: TargetSubject, term_type_id: int | None) -> CreditLimitPolicy | None:
        """The policy for a student in a term type, or ``None`` when none matches (no limit)."""
        candidates = (
            cls.objects.filter(is_active=True)
            .filter(models.Q(term_type_id__isnull=True) | models.Q(term_type_id=term_type_id))
            .order_by("-priority", "id")
        )
        return next((policy for policy in candidates if policy.eligibility.matches(student)), None)
