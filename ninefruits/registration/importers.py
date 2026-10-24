"""Hold CSV import (original ``RegistrationHoldImporter``), registered with
``ninefruits.importing.registry`` as type ``registration_holds`` (permission
``registration_holds.manage``) for the hold list's "Import CSV" button and
``manage.py reference_import registration_holds``."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, time
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from ninefruits.core import context as request_context
from ninefruits.importing.resources import Column, ReferenceResource, RowImportFailed, attribute_label
from ninefruits.registration.enums import HoldSource, HoldType
from ninefruits.registration.models import RegistrationHold


def parse_moment(value: str, column: str) -> datetime:
    """A date or date and time; without a time zone the current one (UTC) applies."""
    moment = parse_datetime(value)
    if moment is None:
        day = parse_date(value)
        if day is None:
            raise ValidationError(
                _("The %(attribute)s field must be a valid date.") % {"attribute": attribute_label(column)}
            )
        moment = datetime.combine(day, time())
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    return moment.replace(microsecond=0)


def _fill_moment(field: str) -> Any:
    def fill(resource: ReferenceResource, record: models.Model, value: Any) -> None:
        setattr(record, field, None if value is None else parse_moment(str(value), field))

    return fill


def _fill_flag(field: str) -> Any:
    def fill(resource: ReferenceResource, record: models.Model, value: Any) -> None:
        if value is not None:
            setattr(record, field, bool(value))

    return fill


class RegistrationHoldResource(ReferenceResource):
    """Places a new hold per row (source "import"), e.g. holds from the legacy SRDENY table or from
    the finance office.

    Columns: student_number, hold_type, reason, starts_at, ends_at, blocks_registration,
    blocks_grades, blocks_certificates."""

    type_key = "registration_holds"
    label = gettext_lazy("holds")

    class Meta(ReferenceResource.Meta):
        model = RegistrationHold

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("student_number", None, required_mapping=True, required=True, max_length=32),
            Column("hold_type", "hold_type", required_mapping=True, required=True, choices=HoldType),
            Column("reason", "reason", required_mapping=True, required=True, max_length=1000),
            Column("starts_at", None, fill=_fill_moment("starts_at")),
            Column("ends_at", None, fill=_fill_moment("ends_at")),
            Column("blocks_registration", None, kind="boolean", fill=_fill_flag("blocks_registration")),
            Column("blocks_grades", None, kind="boolean", fill=_fill_flag("blocks_grades")),
            Column("blocks_certificates", None, kind="boolean", fill=_fill_flag("blocks_certificates")),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> RegistrationHold:
        from ninefruits.person.models import StudentRecord

        number = str(row.get("student_number") or "").strip()
        record = StudentRecord.objects.filter(student_number=number).first()
        if record is None:
            raise RowImportFailed(_("No student record with number %(number)s.") % {"number": number})
        return RegistrationHold(
            student_record=record,
            source=HoldSource.IMPORT,
            created_by_id=request_context.current().user_id,
        )

    def import_instance(self, instance: models.Model, row: Mapping[str, Any], **kwargs: Any) -> None:
        # Dates are checked as text: they carry times.
        for column in ("starts_at", "ends_at"):
            text = str(row.get(column) or "").strip()
            if text:
                parse_moment(text, column)
        super().import_instance(instance, row, **kwargs)
        hold: RegistrationHold = instance  # type: ignore[assignment]
        if hold.starts_at is None:
            hold.starts_at = timezone.now().replace(microsecond=0)
        if hold.ends_at is not None and hold.ends_at <= hold.starts_at:
            raise ValidationError(
                _("The %(attribute)s field must be a date after %(date)s.")
                % {"attribute": attribute_label("ends_at"), "date": attribute_label("starts_at")}
            )


def register_importers() -> None:
    from ninefruits.importing import registry
    from ninefruits.security.enums import Permission

    registry.register(RegistrationHoldResource, Permission.REGISTRATION_HOLDS_MANAGE)
