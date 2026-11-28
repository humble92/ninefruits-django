from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from ninefruits.i18n.fields import TranslatableJSONField


class YearLevelRule(models.Model):
    name = TranslatableJSONField(_("Name"))
    basis = models.CharField(max_length=16)
    thresholds = models.JSONField(default=list)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, default=now)
    updated_at = models.DateTimeField(null=True, auto_now=True)

    class Meta:
        db_table = "year_level_rules"

    def __str__(self) -> str:
        return str(self.name)


class YearLevelRun(models.Model):
    term = models.ForeignKey("term.Term", on_delete=models.RESTRICT)
    cutoff_date = models.DateField()
    status = models.CharField(max_length=16, default="draft")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True)
    created_at = models.DateTimeField(null=True, default=now)
    updated_at = models.DateTimeField(null=True, auto_now=True)

    class Meta:
        db_table = "year_level_runs"

    def __str__(self) -> str:
        return f"{self.term_id}:{self.pk}"


class YearLevelChange(models.Model):
    year_level_run = models.ForeignKey(YearLevelRun, on_delete=models.RESTRICT, related_name="changes")
    student_record = models.ForeignKey("person.StudentRecord", on_delete=models.RESTRICT)
    program = models.ForeignKey("organization.Program", on_delete=models.RESTRICT)
    from_level = models.SmallIntegerField()
    to_level = models.SmallIntegerField()
    rule_name = models.CharField(max_length=255)
    basis = models.CharField(max_length=16)
    measured_value = models.DecimalField(max_digits=10, decimal_places=1)
    outcome = models.CharField(max_length=16, null=True, blank=True)

    class Meta:
        db_table = "year_level_changes"

    def __str__(self) -> str:
        return f"{self.year_level_run_id}:{self.pk}"
