"""Reference data CSV resources (original ``App\\Filament\\Admin\\Imports\\ReferenceImporter`` and
its importers), built on django-import-export and used by the admin screens and by
``manage.py reference_import`` alike.

- Rows are matched by code, so importing the same file again updates instead of duplicating.
- Translatable attributes have one column per supported language (``name_en``, ``name_ko``,
  ``name_zh-hans``; the original's ``name_zh_CN`` is accepted too). Empty cells keep existing
  translations; the fallback language (English) is required for new rows.
- Each row is validated (the original's Laravel rules) and saved in a savepoint: a database
  error fails that row only (PostgreSQL would otherwise abort the whole chunk).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import DatabaseError, models, transaction
from django.utils.translation import gettext as _
from import_export import resources
from import_export.results import RowResult

from ninefruits.i18n.translation import fallback_language

_TRUE = {"1", "true", "yes", "y", "on"}
_FALSE = {"0", "false", "no", "n", "off"}

#: Original (Laravel) locale spellings accepted in column names.
_LOCALE_ALIASES = {"zh-cn": "zh-hans", "zh_cn": "zh-hans"}


class RowImportFailed(ValidationError):
    """The row cannot be imported (original ``RowImportFailedException``)."""


def attribute_label(name: str) -> str:
    """Laravel's attribute name in validation messages: ``name_en`` -> ``name en``."""
    return name.replace("_", " ")


@dataclass
class Column:
    """One CSV column with the original importer's rules.

    ``kind``: ``string``, ``integer``, ``numeric``, ``boolean`` or ``date``. ``relation``: a
    model and lookup field (``(OrgUnitType, "code")``) resolved to the foreign key ``attribute``.
    ``fill``: custom setter ``(resource, instance, value)``; ``None`` attribute means the column
    is only read by ``resolve_record``.
    """

    name: str
    attribute: str | None = None
    required_mapping: bool = False
    required: bool | Callable[[models.Model], bool] = False
    kind: str = "string"
    max_length: int | None = None
    minimum: Decimal | float | None = None
    maximum: Decimal | float | None = None
    choices: type[models.TextChoices] | None = None
    after_or_equal: str | None = None
    relation: tuple[type[models.Model], str] | None = None
    fill: Callable[[Any, models.Model, Any], None] | None = None
    translatable_of: str | None = None
    language: str | None = None
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def is_required(self, instance: models.Model) -> bool:
        return bool(self.required(instance) if callable(self.required) else self.required)


def is_new_record(instance: models.Model) -> bool:
    return bool(instance._state.adding)


def translatable_columns(attribute: str, *, required: bool = True, max_length: int = 255) -> list[Column]:
    """One column per supported language; the fallback language is required for new rows."""
    from ninefruits.institution.services.supported_locales import SupportedLocales

    fallback = fallback_language()
    columns = []
    for code in SupportedLocales().all():
        aliases = tuple(
            f"{attribute}_{alias}"
            for alias in {code.replace("-", "_"), *[key for key, value in _LOCALE_ALIASES.items() if value == code]}
            if alias != code
        )
        columns.append(
            Column(
                name=f"{attribute}_{code}",
                attribute=attribute,
                required=is_new_record if required and code == fallback else False,
                max_length=max_length,
                translatable_of=attribute,
                language=code,
                aliases=aliases,
            )
        )
    return columns


class ReferenceResource(resources.ModelResource):
    """Base for the reference data importers. Subclasses define :meth:`columns` and
    :meth:`resolve_record` (match by code)."""

    #: Import type key (``reference_import <type>``, ``imports.importer``).
    type_key: ClassVar[str] = ""
    #: Plural label of the imported rows (completion message).
    label: ClassVar[Any] = ""

    class Meta:
        fields: tuple[str, ...] = ()
        import_id_fields: tuple[str, ...] = ()
        skip_diff = True
        clean_model_instances = False
        use_transactions = False
        report_skipped = True

    # -- definition ------------------------------------------------------------------------------
    @classmethod
    def columns(cls) -> list[Column]:
        raise NotImplementedError

    @classmethod
    def column_names(cls) -> list[str]:
        return [column.name for column in cls.columns()]

    @classmethod
    def required_columns(cls) -> list[str]:
        return [column.name for column in cls.columns() if column.required_mapping]

    @classmethod
    def normalize_headers(cls, headers: Iterable[str]) -> dict[str, str]:
        """Header in the file -> column name (aliases such as ``name_zh_CN`` resolved)."""
        names: dict[str, str] = {}
        for column in cls.columns():
            names[column.name] = column.name
            names[column.name.lower()] = column.name
            for alias in column.aliases:
                names[alias] = column.name
                names[alias.lower()] = column.name
        mapping = {}
        for header in headers:
            name = names.get(header.strip()) or names.get(header.strip().lower())
            if name is not None:
                mapping[header] = name
        return mapping

    def resolve_record(self, row: Mapping[str, Any]) -> models.Model:
        raise NotImplementedError

    # -- django-import-export hooks --------------------------------------------------------------
    def get_or_init_instance(self, instance_loader: Any, row: Mapping[str, Any]) -> tuple[models.Model, bool]:
        instance = self.resolve_record(row)
        return instance, instance._state.adding

    def import_instance(self, instance: models.Model, row: Mapping[str, Any], **kwargs: Any) -> None:
        errors: list[str] = []
        values: dict[str, Any] = {}
        for column in self.columns():
            raw = row.get(column.name)
            text = "" if raw is None else str(raw).strip()
            present = column.name in row
            if text == "":
                if column.is_required(instance) and (present or column.required_mapping or column.translatable_of):
                    errors.append(
                        _("The %(attribute)s field is required.") % {"attribute": attribute_label(column.name)}
                    )
                values[column.name] = None
                continue
            try:
                values[column.name] = self._convert(column, text)
            except ValidationError as error:
                errors.extend(error.messages)
        for column in self.columns():
            if column.after_or_equal and values.get(column.name) is not None:
                other = values.get(column.after_or_equal)
                if other is not None and values[column.name] < other:
                    errors.append(
                        _("The %(attribute)s field must be a date after or equal to %(date)s.")
                        % {"attribute": attribute_label(column.name), "date": attribute_label(column.after_or_equal)}
                    )
        if errors:
            raise ValidationError(" ".join(errors))

        for column in self.columns():
            if column.name not in row and not column.translatable_of:
                continue
            value = values.get(column.name)
            if column.fill is not None:
                column.fill(self, instance, value)
            elif column.translatable_of:
                if value is not None:
                    translations = dict(getattr(instance, f"{column.translatable_of}_translations"))
                    translations[str(column.language)] = value
                    setattr(instance, column.translatable_of, translations)
            elif column.relation is not None:
                self._fill_relation(column, instance, value)
            elif column.attribute is not None:
                if value is None and not instance._meta.get_field(column.attribute).null:
                    continue  # keeps the model default (e.g. sort_order 0, is_active true)
                setattr(instance, column.attribute, value)

    def after_import(self, dataset: Any, result: Any, **kwargs: Any) -> None:
        """No sequence reset: ids always come from the sequences (and the runtime role may not
        change them)."""

    def import_row(self, row: Any, instance_loader: Any, **kwargs: Any) -> RowResult:
        """The row in its own savepoint: a failed row leaves nothing behind."""
        with transaction.atomic():
            result: RowResult = super().import_row(row, instance_loader, **kwargs)
            if result.errors or result.validation_error is not None:
                transaction.set_rollback(True)
        return result

    # -- helpers ---------------------------------------------------------------------------------
    def _convert(self, column: Column, text: str) -> Any:
        label = attribute_label(column.name)
        if column.kind == "string":
            if column.max_length is not None and len(text) > column.max_length:
                raise ValidationError(
                    _("The %(attribute)s field must not be greater than %(max)s characters.")
                    % {"attribute": label, "max": column.max_length}
                )
            if column.choices is not None and text not in column.choices.values:
                raise ValidationError(_("The selected %(attribute)s is invalid.") % {"attribute": label})
            return text
        if column.kind == "integer":
            try:
                number: Any = int(text)
            except ValueError:
                raise ValidationError(_("The %(attribute)s field must be an integer.") % {"attribute": label}) from None
        elif column.kind == "numeric":
            try:
                number = Decimal(text)
            except InvalidOperation:
                raise ValidationError(_("The %(attribute)s field must be a number.") % {"attribute": label}) from None
        elif column.kind == "boolean":
            lowered = text.lower()
            if lowered in _TRUE:
                return True
            if lowered in _FALSE:
                return False
            raise ValidationError(_("The %(attribute)s field must be true or false.") % {"attribute": label})
        elif column.kind == "date":
            try:
                return dt.date.fromisoformat(text[:10]) if len(text) >= 10 else dt.date.fromisoformat(text)
            except ValueError:
                raise ValidationError(
                    _("The %(attribute)s field must be a valid date.") % {"attribute": label}
                ) from None
        else:
            raise ValueError(f"Unknown column kind {column.kind!r}")
        if column.minimum is not None and column.maximum is not None:
            if not column.minimum <= number <= column.maximum:
                raise ValidationError(
                    _("The %(attribute)s field must be between %(min)s and %(max)s.")
                    % {"attribute": label, "min": column.minimum, "max": column.maximum}
                )
        elif column.minimum is not None and number < column.minimum:
            raise ValidationError(
                _("The %(attribute)s field must be at least %(min)s.") % {"attribute": label, "min": column.minimum}
            )
        return number

    def _fill_relation(self, column: Column, instance: models.Model, value: Any) -> None:
        assert column.relation is not None and column.attribute is not None
        model, lookup = column.relation
        if value is None:
            setattr(instance, column.attribute, None)
            return
        related = model._default_manager.filter(**{lookup: value}).first()
        if related is None:
            raise RowImportFailed(unknown_code(column.name, value))
        setattr(instance, column.attribute, related)


def unknown_code(column: str, code: Any) -> str:
    return _('Unknown %(column)s code "%(code)s".') % {"column": column, "code": code}


def row_error_message(error: Exception) -> str:
    """The reason stored with a failed row."""
    if isinstance(error, ValidationError):
        return " ".join(error.messages)
    if isinstance(error, DatabaseError):
        cause = error.__cause__ or error
        first_line = str(cause).strip().splitlines()[0] if str(cause).strip() else type(cause).__name__
        return _("Rejected by the database: %(message)s") % {"message": first_line}
    return str(error)
