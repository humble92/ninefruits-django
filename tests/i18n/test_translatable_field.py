"""TranslatableJSONField: descriptor, validation, form field and the util.i18n expressions
(original HasTranslatableAttributes, TranslatableFields, porting-plan 6.2)."""

from __future__ import annotations

import copy
import pickle

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower
from django.utils import translation

from ninefruits.core.db import session_context
from ninefruits.i18n.fields import I18n, I18nSearchText, TranslatableJSONField, TranslatedText, validate_translations
from ninefruits.i18n.forms import TranslatableFormField, TranslatableWidget
from ninefruits.security.models import Role


def make_role(name: str, display_name: dict[str, str], **fields: object) -> Role:
    return Role.objects.create(name=name, guard_name="web", display_name=display_name, **fields)


class TestDescriptor:
    def test_reading_gives_the_active_language_with_fallback_order(self) -> None:
        role = Role(display_name={"en": "Registrar", "ko": "학적 담당", "zh": "学籍管理"})
        with translation.override("ko"):
            assert role.display_name == "학적 담당"
        with translation.override("zh-hans"):
            assert role.display_name == "学籍管理"  # base language
        with translation.override("lo"):
            assert role.display_name == "Registrar"  # fallback language
        assert Role(display_name={"ko": "학적 담당"}).display_name == "학적 담당"  # first value

    def test_translations_accessor_returns_a_copy(self) -> None:
        role = Role(display_name={"en": "Registrar", "ko": "학적 담당"})
        translations = role.display_name_translations
        translations["ko"] = "changed"
        assert role.display_name_translations == {"en": "Registrar", "ko": "학적 담당"}
        assert Role(description=None).description_translations == {}

    def test_assigning_a_dict_replaces_all_translations_and_drops_empty_values(self) -> None:
        role = Role(display_name={"en": "Registrar", "ko": "학적 담당"})
        role.display_name = {"en": "Dean", "ko": "", "lo": None}
        assert role.display_name_translations == {"en": "Dean"}
        role.description = {"en": ""}
        assert role.description is None

    def test_assigning_text_sets_the_active_language_only(self) -> None:
        role = Role(display_name={"en": "Registrar"})
        with translation.override("ko"):
            role.display_name = "학적 담당"
        assert role.display_name_translations == {"en": "Registrar", "ko": "학적 담당"}

    def test_translated_text_keeps_the_translations_through_copies(self) -> None:
        text = TranslatedText("Registrar", {"en": "Registrar", "ko": "학적 담당"})
        assert pickle.loads(pickle.dumps(text)).translations == text.translations  # noqa: S301
        assert copy.deepcopy(text).translations == text.translations
        role = Role(display_name={"en": "x"})
        role.display_name = text  # e.g. refresh_from_db copies attribute values
        assert role.display_name_translations == {"en": "Registrar", "ko": "학적 담당"}
        assert text.get("ko") == "학적 담당" and text.get("lo") is None

    def test_rejects_other_types(self) -> None:
        with pytest.raises(TypeError):
            Role(display_name=["en"])

    @pytest.mark.django_db
    def test_round_trip_save_refresh_and_update(self) -> None:
        role = make_role("translatable_round_trip", {"en": "Registrar", "ko": "학적 담당"})
        role.refresh_from_db()
        assert role.display_name_translations == {"en": "Registrar", "ko": "학적 담당"}
        role.display_name = {"en": "Dean", "zh-hans": "院长"}
        role.save()
        loaded = Role.objects.get(pk=role.pk)
        with translation.override("zh-hans"):
            assert loaded.display_name == "院长"
        Role.objects.bulk_update([loaded], ["display_name"])
        assert Role.objects.get(pk=role.pk).display_name_translations == {"en": "Dean", "zh-hans": "院长"}
        deferred = Role.objects.only("name").get(pk=role.pk)
        assert deferred.display_name_translations == {"en": "Dean", "zh-hans": "院长"}

    @pytest.mark.django_db
    def test_json_lookups_still_work(self) -> None:
        make_role("translatable_lookup", {"en": "Registrar", "ko": "학적 담당"})
        assert Role.objects.filter(display_name__ko="학적 담당", name="translatable_lookup").exists()


class TestValidation:
    def test_requires_the_fallback_language(self) -> None:
        role = Role(name="x", guard_name="web", display_name={"ko": "학적 담당"})
        with pytest.raises(ValidationError) as error:
            validate_translations(role)
        assert "display_name" in error.value.message_dict
        assert error.value.message_dict["display_name"] == ["The English value is required."]

    def test_blank_fields_may_be_empty_but_not_without_english(self) -> None:
        role = Role(name="x", guard_name="web", display_name={"en": "Registrar"}, description=None)
        validate_translations(role)
        role.description = {"ko": "설명"}
        with pytest.raises(ValidationError) as error:
            validate_translations(role, "description")
        assert list(error.value.message_dict) == ["description"]

    def test_full_clean_keeps_the_dict(self) -> None:
        role = Role(name="clean_keeps", guard_name="web", display_name={"en": "Registrar", "ko": "학적 담당"})
        role.clean_fields(exclude=["id", "persona", "created_at", "updated_at"])
        assert role.display_name_translations == {"en": "Registrar", "ko": "학적 담당"}

    def test_max_length_per_translation(self) -> None:
        field = TranslatableJSONField(max_length=5)
        field.set_attributes_from_name("title")
        with pytest.raises(ValidationError):
            field.clean({"en": "too long"}, None)
        assert field.clean({"en": "short"}, None) == {"en": "short"}

    def test_deconstruct(self) -> None:
        _name, path, _args, kwargs = TranslatableJSONField(null=True, max_length=None).deconstruct()
        assert path == "ninefruits.i18n.fields.TranslatableJSONField"
        assert kwargs["max_length"] is None and kwargs["null"] is True


class TranslatableForm(forms.Form):
    name = TranslatableFormField(label="Name", languages=["en", "ko", "zh-hans", "lo"])
    note = TranslatableFormField(label="Note", required=False, languages=["en", "ko"], textarea=True)


class TestFormField:
    def test_one_input_per_language_with_the_fallback_language_first_and_required(self) -> None:
        html = str(TranslatableForm(initial={"name": {"ko": "학적 담당", "en": "Registrar"}})["name"])
        assert html.index('name="name__en"') < html.index('name="name__ko"') < html.index('name="name__lo"')
        assert 'name="name__zh-hans"' in html
        assert 'value="학적 담당"' in html
        assert "한국어" in html and "ລາວ" in html
        assert html.count("required") >= 1

    def test_keeps_languages_already_stored(self) -> None:
        html = str(TranslatableForm(initial={"note": {"en": "x", "lo": "ບັນທຶກ"}})["note"])
        assert 'name="note__lo"' in html and "<textarea" in html

    def test_cleans_to_a_dict_without_empty_values(self) -> None:
        form = TranslatableForm(data={"name__en": " Registrar ", "name__ko": "학적 담당", "name__lo": ""})
        assert form.is_valid(), form.errors
        assert form.cleaned_data["name"] == {"en": "Registrar", "ko": "학적 담당"}
        assert form.cleaned_data["note"] is None

    def test_requires_english(self) -> None:
        form = TranslatableForm(data={"name__ko": "학적 담당"})
        assert not form.is_valid()
        assert form.errors["name"] == ["The English value is required."]
        optional = TranslatableForm(data={"name__en": "x", "note__ko": "메모"})
        assert not optional.is_valid() and "note" in optional.errors

    def test_has_changed_compares_translations(self) -> None:
        field = TranslatableForm().fields["name"]
        assert not field.has_changed({"en": "a"}, {"en": "a", "ko": ""})
        assert field.has_changed({"en": "a"}, {"en": "b"})

    @pytest.mark.django_db
    def test_model_form_uses_the_translatable_field(self) -> None:
        class RoleForm(forms.ModelForm):
            class Meta:
                model = Role
                fields = ["display_name", "description"]

        form = RoleForm(instance=Role(display_name={"en": "Registrar", "ko": "학적 담당"}))
        assert isinstance(form.fields["display_name"], TranslatableFormField)
        assert isinstance(form.fields["display_name"].widget, TranslatableWidget)
        assert form.fields["display_name"].required and not form.fields["description"].required
        assert 'value="학적 담당"' in str(form["display_name"])
        bound = RoleForm(data={"display_name__en": "Dean", "display_name__ko": "학장"}, instance=Role(name="x"))
        assert bound.is_valid(), bound.errors
        assert bound.save(commit=False).display_name_translations == {"en": "Dean", "ko": "학장"}


@pytest.mark.django_db
class TestExpressions:
    @pytest.fixture
    def roles(self) -> list[Role]:
        return [
            make_role("expr_b", {"en": "Bravo", "ko": "나"}),
            make_role("expr_a", {"en": "Charlie", "ko": "가"}),
            make_role("expr_c", {"en": "Alpha", "ko": "다", "zh-hans": "数据"}),
        ]

    def test_orders_by_the_session_language(self, roles: list[Role]) -> None:
        names = Role.objects.filter(name__startswith="expr_")
        context = session_context()
        context.set_locale("ko", "en")
        try:
            assert list(names.order_by(I18n("display_name")).values_list("name", flat=True)) == [
                "expr_a",
                "expr_b",
                "expr_c",
            ]
        finally:
            context.reset()
        assert list(names.order_by(I18n("display_name", "en")).values_list("name", flat=True)) == [
            "expr_c",
            "expr_b",
            "expr_a",
        ]

    def test_annotates_the_value_in_a_given_language(self, roles: list[Role]) -> None:
        values = dict(
            Role.objects.filter(name__startswith="expr_")
            .annotate(label=I18n("display_name", "zh-hans"))
            .values_list("name", "label")
        )
        assert values == {"expr_a": "Charlie", "expr_b": "Bravo", "expr_c": "数据"}

    def test_searches_every_language(self, roles: list[Role]) -> None:
        found = (
            Role.objects.annotate(search=Lower(I18nSearchText("display_name")))
            .filter(search__contains="数据")
            .values_list("name", flat=True)
        )
        assert list(found) == ["expr_c"]
