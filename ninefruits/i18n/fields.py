"""Translatable jsonb columns (original spatie/laravel-translatable + ``HasTranslatableAttributes``,
porting-plan 6.2).

    class Role(models.Model):
        display_name = TranslatableJSONField()
        description = TranslatableJSONField(null=True, blank=True)

    role.display_name                  # "학적 담당" in Korean, "Registrar" otherwise (str)
    role.display_name_translations     # {"en": "Registrar", "ko": "학적 담당"} (a copy)
    role.display_name = {"en": "Registrar", "ko": "학적 담당"}   # replaces all translations
    role.display_name = "학적 담당"      # sets the active language only

    Role.objects.order_by(I18n("display_name"))
    Role.objects.annotate(t=I18nSearchText("display_name")).filter(t__icontains="학적")

Reading the attribute returns a :class:`TranslatedText` (a ``str``) in the active language with
the fallback order of ``util.i18n``. It remembers every translation, so Django internals that
copy attribute values (``refresh_from_db``, ``Model.clean_fields``, forms) keep the dict.

Assigning a dict replaces all translations (spatie merges them, so a cleared language could never
be removed); empty values are dropped and nothing left stores ``NULL``, as in the original. The
database already has ``CHECK (jsonb_typeof(col) = 'object')`` constraints. ``validate`` requires the
fallback language (English) value, like the original admin form (``TranslatableFields``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query_utils import DeferredAttribute
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from ninefruits.i18n.translation import current_language, fallback_language, search_text, translate

TRANSLATIONS_SUFFIX = "_translations"


class TranslatedText(str):
    """The translated value of a translatable attribute. Behaves as a ``str`` and carries all
    translations in ``translations``."""

    translations: dict[str, str]

    def __new__(cls, text: str, translations: Mapping[str, str]) -> TranslatedText:
        instance = super().__new__(cls, text)
        instance.translations = dict(translations)
        return instance

    def __reduce__(self) -> tuple[Any, ...]:
        return (TranslatedText, (str(self), self.translations))

    def __deepcopy__(self, memo: dict[int, Any]) -> TranslatedText:
        return TranslatedText(str(self), self.translations)

    def get(self, language: str) -> str | None:
        """Exact value for one language (no fallback)."""
        return self.translations.get(language) or None


def normalize_translations(value: Any) -> dict[str, str] | None:
    """Drops empty values; an empty result is ``None`` (original setAttribute)."""
    if value is None:
        return None
    if isinstance(value, TranslatedText):
        value = value.translations
    if not isinstance(value, Mapping):
        raise TypeError(f"Translatable values are dicts of language code to text, not {type(value).__name__}.")
    cleaned = {str(code): str(text) for code, text in value.items() if text is not None and text != ""}
    return cleaned or None


def _raw(instance: models.Model, attname: str) -> Any:
    return instance.__dict__.get(attname)


class TranslatableAttribute(DeferredAttribute):
    """Descriptor for the field's attribute: reading gives :class:`TranslatedText`."""

    def __get__(self, instance: models.Model | None, cls: type | None = None) -> Any:
        if instance is None:
            return self
        raw = super().__get__(instance, cls)
        if raw is None:
            return None
        if not isinstance(raw, Mapping):  # not an object: the database CHECK forbids it
            return raw
        return TranslatedText(translate(raw) or "", raw)

    def __set__(self, instance: models.Model, value: Any) -> None:
        attname = self.field.attname
        if isinstance(value, TranslatedText | Mapping) or value is None:
            instance.__dict__[attname] = normalize_translations(value)
            return
        if isinstance(value, str):
            # Assigning text sets the active language only (spatie setAttribute with a string).
            current = dict(_raw(instance, attname) or {})
            current[current_language()] = value
            instance.__dict__[attname] = normalize_translations(current)
            return
        raise TypeError(f"{self.field.name}: assign a dict of translations or a str, not {type(value).__name__}.")


class TranslationsAccessor:
    """``obj.<name>_translations``: a copy of the stored dict (``{}`` when NULL)."""

    def __init__(self, field: TranslatableJSONField) -> None:
        self.field = field

    def __get__(self, instance: models.Model | None, cls: type | None = None) -> Any:
        if instance is None:
            return self
        getattr(instance, self.field.attname)  # loads a deferred value
        return dict(_raw(instance, self.field.attname) or {})

    def __set__(self, instance: models.Model, value: Mapping[str, str] | None) -> None:
        instance.__dict__[self.field.attname] = normalize_translations(value)


class TranslatableJSONField(models.JSONField):
    descriptor_class = TranslatableAttribute
    description = "Translatable text (JSON object of language code to text)"

    def __init__(self, *args: Any, required_language: str | None = None, max_length: int | None = 255, **kwargs: Any):
        self.required_language = required_language
        self.text_max_length = max_length
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        if self.required_language is not None:
            kwargs["required_language"] = self.required_language
        if self.text_max_length != 255:
            kwargs["max_length"] = self.text_max_length
        return name, path, args, kwargs

    def contribute_to_class(self, cls: type[models.Model], name: str, private_only: bool = False) -> None:
        super().contribute_to_class(cls, name, private_only)
        setattr(cls, name + TRANSLATIONS_SUFFIX, TranslationsAccessor(self))

    # -- values Django reads from the instance --------------------------------------------------
    def value_from_object(self, obj: models.Model) -> Any:
        return _raw(obj, self.attname)

    def pre_save(self, model_instance: models.Model, add: bool) -> Any:
        return _raw(model_instance, self.attname)

    def get_prep_value(self, value: Any) -> Any:
        if isinstance(value, TranslatedText):
            value = value.translations
        return super().get_prep_value(value)

    def to_python(self, value: Any) -> Any:
        if isinstance(value, TranslatedText):
            return value.translations
        return value

    # -- validation ------------------------------------------------------------------------------
    def clean(self, value: Any, model_instance: models.Model | None) -> Any:
        if model_instance is not None:
            value = _raw(model_instance, self.attname)
        value = normalize_translations(value) if isinstance(value, Mapping) else self.to_python(value)
        self.validate(value, model_instance)
        self.run_validators(value)
        return value

    def validate(self, value: Any, model_instance: models.Model | None) -> None:
        if value is not None and not isinstance(value, Mapping):
            raise ValidationError(_("Translations must be an object of language code to text."), code="invalid")
        language = self.required_language or fallback_language()
        if not value:
            if not self.blank:
                raise ValidationError(_required_message(language), code="required_language")
            return
        if not value.get(language):
            raise ValidationError(_required_message(language), code="required_language")
        if self.text_max_length:
            for text in value.values():
                if len(text) > self.text_max_length:
                    raise ValidationError(
                        _("Ensure each translation has at most %(limit_value)d characters."),
                        code="max_length",
                        params={"limit_value": self.text_max_length},
                    )

    def formfield(self, **kwargs: Any) -> Any:
        """One input per supported language (:class:`ninefruits.i18n.forms.TranslatableFormField`).
        Widgets set for ``JSONField`` (admin ``formfield_overrides``) are ignored."""
        from ninefruits.i18n.forms import TranslatableFormField, TranslatableWidget

        widget = kwargs.pop("widget", None)
        kwargs.pop("form_class", None)
        kwargs.pop("encoder", None)
        kwargs.pop("decoder", None)
        if isinstance(widget, TranslatableWidget) or (
            isinstance(widget, type) and issubclass(widget, TranslatableWidget)
        ):
            kwargs["widget"] = widget
        defaults: dict[str, Any] = {
            "required": not self.blank,
            "label": capfirst(self.verbose_name),
            "help_text": self.help_text,
            "required_language": self.required_language,
            "max_length": self.text_max_length,
        }
        defaults.update(kwargs)
        return TranslatableFormField(**defaults)


def _required_message(language: str) -> str:
    from django.utils.translation import get_language_info

    try:
        name = get_language_info(language)["name_translated"]
    except KeyError:
        name = language
    return str(_("The %(language)s value is required.") % {"language": name})


def validate_translations(instance: models.Model, *field_names: str) -> None:
    """For ``Model.clean()``: validates the named translatable fields (all when none given)
    and raises one ``ValidationError`` keyed by field name."""
    errors: dict[str, list[ValidationError]] = {}
    for field in instance._meta.concrete_fields:
        if not isinstance(field, TranslatableJSONField):
            continue
        if field_names and field.name not in field_names:
            continue
        try:
            field.clean(None, instance)
        except ValidationError as error:
            errors.setdefault(field.name, []).append(error)
    if errors:
        raise ValidationError(errors)


class I18n(models.Func):
    """``util.i18n(column)``: the value in the database session language (``app.locale`` is set by
    the request middleware), for ``order_by`` and ``annotate``. With ``language`` it calls
    ``util.i18n(column, language, fallback)``."""

    function = "util.i18n"
    output_field = models.TextField()

    def __init__(self, expression: Any, language: str | None = None, fallback: str | None = None, **extra: Any):
        if language is None:
            super().__init__(expression, **extra)
        else:
            super().__init__(expression, models.Value(language), models.Value(fallback or fallback_language()), **extra)


class I18nSearchText(models.Func):
    """``util.i18n_search_text(column)``: every translation joined, for language independent
    search (``icontains``; trigram indexes use the same expression)."""

    function = "util.i18n_search_text"
    output_field = models.TextField()

    def __init__(self, expression: Any, **extra: Any):
        super().__init__(expression, **extra)


__all__ = [
    "I18n",
    "I18nSearchText",
    "TranslatableJSONField",
    "TranslatedText",
    "normalize_translations",
    "search_text",
    "translate",
    "validate_translations",
]
