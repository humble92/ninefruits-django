"""Form field and widget for translatable values (original Filament ``TranslatableFields``): one
input per supported language, the fallback language (English) first and required.

``TranslatableJSONField.formfield()`` returns :class:`TranslatableFormField`, so ModelForms and
``ModelAdmin`` use it without configuration. In a plain form::

    name = TranslatableFormField(label=_("Institution name"))

The languages are read when the form renders (institution settings), plus any language already
present in the value, so disabling a language in the settings never drops stored translations.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminTextareaWidget, UnfoldAdminTextInputWidget

from ninefruits.i18n.translation import fallback_language

SEPARATOR = "__"


def _languages(explicit: Sequence[str] | None, value: Mapping[str, Any] | None) -> list[str]:
    if explicit is not None:
        languages = list(explicit)
    else:
        from ninefruits.institution.services.supported_locales import SupportedLocales

        languages = SupportedLocales().all()
    fallback = fallback_language()
    ordered = [fallback] + [code for code in languages if code != fallback]
    ordered += [code for code in (value or {}) if code not in ordered]
    return ordered


def _label(code: str) -> str:
    from ninefruits.institution.services.supported_locales import SupportedLocales

    return SupportedLocales.label(code)


class TranslatableWidget(forms.Widget):
    template_name = "i18n/widgets/translatable.html"

    def __init__(
        self,
        attrs: dict[str, Any] | None = None,
        *,
        languages: Sequence[str] | None = None,
        textarea: bool = False,
        required_language: str | None = None,
    ) -> None:
        super().__init__(attrs)
        self.languages = list(languages) if languages is not None else None
        self.textarea = textarea
        self.required_language = required_language

    def _input(self) -> forms.Widget:
        widget: forms.Widget = (
            UnfoldAdminTextareaWidget(attrs={"rows": 3}) if self.textarea else UnfoldAdminTextInputWidget()
        )
        return widget

    def format_value(self, value: Any) -> dict[str, str]:
        return as_translations(value) or {}

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        values = self.format_value(value)
        final_attrs = context["widget"]["attrs"]
        base_id = final_attrs.get("id") or f"id_{name}"
        required_language = self.required_language or fallback_language()
        items = []
        for code in _languages(self.languages, values):
            sub_attrs = {**final_attrs, "id": f"{base_id}{SEPARATOR}{code}", "lang": code}
            required = bool(self.is_required and code == required_language)
            sub_attrs.pop("required", None)
            if required:
                sub_attrs["required"] = True
            widget = self._input()
            widget.is_required = required
            items.append(
                {
                    "code": code,
                    "label": _label(code),
                    "required": required,
                    "widget": widget.get_context(f"{name}{SEPARATOR}{code}", values.get(code, ""), sub_attrs)["widget"],
                }
            )
        context["widget"]["languages"] = items
        return context

    def value_from_datadict(self, data: Any, files: Any, name: str) -> dict[str, str]:
        prefix = f"{name}{SEPARATOR}"
        return {key[len(prefix) :]: data.get(key) or "" for key in data if key.startswith(prefix)}

    def value_omitted_from_data(self, data: Any, files: Any, name: str) -> bool:
        prefix = f"{name}{SEPARATOR}"
        return not any(key.startswith(prefix) for key in data)

    def id_for_label(self, id_: str) -> str:
        return f"{id_}{SEPARATOR}{fallback_language()}" if id_ else id_


def as_translations(value: Any) -> dict[str, str] | None:
    """Normalizes a form value (dict, ``TranslatedText``, JSON text) to a dict without empty values."""
    from ninefruits.i18n.fields import TranslatedText

    if value is None or value == "":
        return None
    if isinstance(value, TranslatedText):
        value = value.translations
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return None
    if not isinstance(value, Mapping):
        return None
    cleaned = {str(code): str(text).strip() for code, text in value.items() if text is not None}
    return {code: text for code, text in cleaned.items() if text} or None


class TranslatableFormField(forms.Field):
    widget = TranslatableWidget
    default_error_messages = {
        "required": _("This field is required."),
        "max_length": _("Ensure each translation has at most %(limit_value)d characters."),
    }

    def __init__(
        self,
        *,
        required_language: str | None = None,
        max_length: int | None = 255,
        textarea: bool = False,
        languages: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.required_language = required_language
        self.max_length = max_length
        widget = kwargs.pop("widget", None)
        if widget is None or (isinstance(widget, type) and issubclass(widget, TranslatableWidget)):
            widget = (widget or TranslatableWidget)(
                languages=languages, textarea=textarea, required_language=required_language
            )
        super().__init__(widget=widget, **kwargs)

    def prepare_value(self, value: Any) -> Any:
        return as_translations(value)

    def to_python(self, value: Any) -> dict[str, str] | None:
        return as_translations(value)

    def validate(self, value: dict[str, str] | None) -> None:
        language = self.required_language or fallback_language()
        if not value:
            if self.required:
                from ninefruits.i18n.fields import _required_message

                raise ValidationError(_required_message(language), code="required")
            return
        if not value.get(language):
            from ninefruits.i18n.fields import _required_message

            raise ValidationError(_required_message(language), code="required_language")
        if self.max_length:
            for text in value.values():
                if len(text) > self.max_length:
                    raise ValidationError(
                        self.error_messages["max_length"], code="max_length", params={"limit_value": self.max_length}
                    )

    def has_changed(self, initial: Any, data: Any) -> bool:
        return (as_translations(initial) or {}) != (as_translations(data) or {})
