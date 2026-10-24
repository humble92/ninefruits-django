"""People in the admin panel (original Filament ``PersonResource`` with ``PersonForm``,
``PersonInfolist``, ``ViewPerson`` header actions and the guardians and student records relation
managers).

Only people the user may see are listed (``Person.objects.visible_to``, and row level security in
the database). National ID and passport numbers are shown masked; revealing one needs
``people.view_sensitive``, a reason, and is recorded in the security log."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Exists, OuterRef
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import TabularInline
from unfold.contrib.filters.admin import RadioFilter
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm
from unfold.widgets import (
    UnfoldAdminDateWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
)

from ninefruits.adminpanel.mixins import CatalogAdmin, CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.media.services import MediaError, add_media
from ninefruits.person.actions import InvitePerson, MergePeople
from ninefruits.person.enums import Gender, StudentStatus
from ninefruits.person.models import Guardian, Person, StudentRecord
from ninefruits.pii.actions import RevealSensitiveValue
from ninefruits.security.enums import Permission
from ninefruits.security.models import User

from .common import admin_change_url, apply_errors, form_page, reason_field, record_changes

PHOTO_MAX_SIZE = 2 * 1024 * 1024


def _other_languages() -> list[tuple[str, str]]:
    from ninefruits.i18n.translation import fallback_language
    from ninefruits.institution.services.supported_locales import SupportedLocales

    fallback = fallback_language()
    return [(code, SupportedLocales.label(code)) for code in SupportedLocales().all() if code != fallback]


def _secret_input() -> forms.PasswordInput:
    return forms.PasswordInput(
        render_value=False, attrs={"class": UnfoldAdminTextInputWidget().attrs["class"], "autocomplete": "off"}
    )


def person_field_definitions(instance: Person | None = None) -> dict[str, forms.Field]:
    """Fields of a person (original ``PersonForm::components``)."""
    from ninefruits.institution.models import Country, LookupValue

    text = UnfoldAdminTextInputWidget
    fields: dict[str, forms.Field] = {
        "family_name": forms.CharField(
            label=_("Family name"),
            max_length=255,
            widget=text,
            help_text=_(
                "Legal name in Latin letters, as in the passport. Add the name as written in other languages below."
            ),
        ),
        "given_name": forms.CharField(label=_("Given name"), max_length=255, required=False, widget=text),
    }
    for code, label in _other_languages():
        fields[f"name_{code}"] = forms.CharField(label=label, max_length=255, required=False, widget=text)
    keep = _("Leave empty to keep the stored value. Enter a new value to replace it.")
    encrypted = _("Stored encrypted. Shown masked; revealing it is logged.")
    fields.update(
        {
            "birth_date": forms.DateField(label=_("Birth date"), required=False, widget=UnfoldAdminDateWidget),
            "gender": forms.ChoiceField(
                label=_("Gender"), required=False, choices=[("", "-"), *Gender.choices], widget=UnfoldAdminSelectWidget
            ),
            "nationality": forms.ModelChoiceField(
                label=_("Nationality"),
                required=False,
                queryset=Country.objects.filter(is_active=True).order_by("code"),
                widget=UnfoldAdminSelectWidget,
            ),
            "ethnicity": forms.ModelChoiceField(
                label=_("Ethnicity"),
                required=False,
                queryset=LookupValue.objects.of_type("ethnicity").filter(is_active=True),
                widget=UnfoldAdminSelectWidget,
            ),
            "national_id_input": forms.CharField(
                label=_("National ID number"),
                required=False,
                max_length=64,
                widget=_secret_input(),
                help_text=keep if instance is not None and instance.national_id_encrypted else encrypted,
            ),
            "passport_number_input": forms.CharField(
                label=_("Passport number"),
                required=False,
                max_length=64,
                widget=_secret_input(),
                help_text=keep if instance is not None and instance.passport_number_encrypted else encrypted,
            ),
            "email": forms.EmailField(label=_("Contact email"), required=False, max_length=255, widget=text),
            "phone": forms.CharField(label=_("Phone"), required=False, max_length=32, widget=text),
            "address": forms.CharField(
                label=_("Address"), required=False, widget=UnfoldAdminTextareaWidget(attrs={"rows": 2})
            ),
            "postal_code": forms.CharField(label=_("Postal code"), required=False, max_length=16, widget=text),
        }
    )
    return fields


class PersonFields(forms.Form):
    """Person fields shared by the person form and the "register student" and "new instructor"
    forms for new people (original ``PersonForm::components``)."""

    def add_person_fields(self, instance: Person | None, prefix: str = "") -> None:
        for name, field in person_field_definitions(instance).items():
            self.fields[f"{prefix}{name}"] = field
            if instance is not None and not prefix:
                self.initial.setdefault(name, _initial(instance, name))

    def clean_birth_date_value(self, value: Any) -> Any:
        if value is not None and value > timezone.localdate():
            raise ValidationError(_("The birth date must not be in the future."))
        return value

    def person_attributes(self, prefix: str = "") -> dict[str, Any]:
        """Form state -> model attributes (original ``PersonForm::toAttributes``): empty name
        variants are dropped and identity numbers are only replaced when something was typed."""
        data = self.cleaned_data
        attributes: dict[str, Any] = {
            name: data.get(f"{prefix}{name}") or None
            for name in (
                "family_name",
                "given_name",
                "birth_date",
                "gender",
                "nationality",
                "ethnicity",
                "email",
                "phone",
                "address",
                "postal_code",
            )
        }
        variants = {
            code: data[f"{prefix}name_{code}"]
            for code, _label in _other_languages()
            if data.get(f"{prefix}name_{code}")
        }
        attributes["name_variants"] = variants or None
        for name in ("national_id", "passport_number"):
            if data.get(f"{prefix}{name}_input"):
                attributes[f"{name}_encrypted"] = data[f"{prefix}{name}_input"]
        return attributes


def _initial(person: Person, name: str) -> Any:
    if name.startswith("name_"):
        return (person.name_variants or {}).get(name.removeprefix("name_"))
    if name.endswith("_input"):
        return ""
    if name in ("nationality", "ethnicity"):
        return getattr(person, f"{name}_id")
    return getattr(person, name)


class PersonAdminForm(PersonFields, forms.ModelForm):  # type: ignore[type-arg,misc]
    photo = forms.ImageField(label=_("Photo"), required=False, help_text=_("JPEG, PNG or WebP, at most 2 MB."))

    class Meta:
        model = Person
        fields: tuple[str, ...] = ()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.add_person_fields(self.instance if self.instance.pk else None)
        self.order_fields(["family_name", "given_name"])

    def clean_birth_date(self) -> Any:
        return self.clean_birth_date_value(self.cleaned_data.get("birth_date"))

    def clean_photo(self) -> Any:
        photo = self.cleaned_data.get("photo")
        if photo is not None and photo.size > PHOTO_MAX_SIZE:
            raise ValidationError(_("The photo must not be larger than 2 MB."))
        return photo

    def save(self, commit: bool = True) -> Person:
        person: Person = self.instance
        for name, value in self.person_attributes().items():
            setattr(person, name, value)
        if commit:
            person.save()
        else:
            self.save_m2m = lambda: None  # no many-to-many fields
        return person


class GuardianInline(CatalogPermissionMixin, TabularInline):  # type: ignore[misc]
    model = Guardian
    extra = 0
    tab = True
    fields = ("relationship", "full_name", "phone", "email", "address", "is_primary_contact")
    verbose_name = _("guardian")
    verbose_name_plural = _("guardians")
    permissions: ClassVar[dict[str, str]] = {"view": Permission.PEOPLE_VIEW}

    def _can_change_person(self, request: HttpRequest, obj: Any) -> bool:
        return obj is not None and request.user.has_perm("update", obj)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return obj is None or request.user.has_perm("view", obj)

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._can_change_person(request, obj)

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._can_change_person(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._can_change_person(request, obj)


class StudentRecordInline(CatalogPermissionMixin, TabularInline):  # type: ignore[misc]
    """The person's student records (one per admission), read only with links."""

    model = StudentRecord
    extra = 0
    tab = True
    can_delete = False
    show_change_link = True
    fields = ("student_number", "program", "status_display", "year_level", "admission_date")
    readonly_fields = fields
    verbose_name = _("student record")
    verbose_name_plural = _("student records")

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return True

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return StudentRecord.objects.visible_to(request.user).select_related("program")

    @display(description=pgettext_lazy("people", "Status"))
    def status_display(self, obj: StudentRecord) -> str:
        return str(StudentStatus(obj.status).label)


class RevealForm(BaseDialogForm):
    reason = reason_field(500)


class InviteForm(forms.Form):
    email = forms.EmailField(
        label=_("Sign-in email"),
        help_text=_("The invitation link is sent here. This becomes the sign-in email."),
        widget=UnfoldAdminTextInputWidget,
    )


class MergeForm(forms.Form):
    target = forms.ModelChoiceField(
        label=_("Keep this person"), queryset=Person.objects.none(), widget=UnfoldAdminSelectWidget
    )
    reason = reason_field()

    def __init__(self, *args: Any, queryset: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if queryset is not None:
            self.fields["target"].queryset = queryset  # type: ignore[attr-defined]


class MergedFilter(RadioFilter):
    title = pgettext_lazy("people", "Merged")
    parameter_name = "merged"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, Any]]:
        return [("0", _("No")), ("1", _("Yes")), ("all", _("All"))]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        if value in (None, "0"):
            return queryset.filter(merged_into__isnull=True)
        if value == "1":
            return queryset.filter(merged_into__isnull=False)
        return queryset


@admin.register(Person)
class PersonAdmin(CatalogAdmin):
    """People (one row per person for life)."""

    permissions: ClassVar[dict[str, str]] = {"view": Permission.PEOPLE_VIEW}
    navigation_group = NavigationGroup.STUDENT_RECORDS
    navigation_icon = "badge"
    navigation_order = 30
    form = PersonAdminForm
    list_display = ("name_column", "birth_date", "email", "records_count", "has_account")
    list_filter = (MergedFilter,)
    search_fields: tuple[str, ...] = ()
    show_full_result_count = False
    ordering = ("family_name", "given_name", "id")
    inlines = (StudentRecordInline, GuardianInline)
    actions_detail = ("reveal_national_id", "reveal_passport_number", "invite", "merge")
    change_form_after_template = "person/admin/history.html"
    readonly_fields = (
        "display_name_view",
        "romanized_name_view",
        "photo_view",
        "birth_date",
        "gender_view",
        "nationality",
        "ethnicity",
        "national_id_masked",
        "passport_number_masked",
        "email",
        "phone",
        "address",
        "postal_code",
        "login_email",
        "merged_into_view",
    )

    # -- permissions (original PersonPolicy) -----------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None:
            return bool(request.user.has_perm("view", obj))
        return bool(request.user.has_perm("view_any", Person))

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return bool(request.user.has_perm("create", Person))

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is None:
            return bool(request.user.has_perm("create", Person) or request.user.has_perm(Permission.PEOPLE_MANAGE))
        return bool(request.user.has_perm("update", obj))

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_form(self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any) -> Any:
        kwargs["form"] = type("PersonAdminForm", (PersonAdminForm,), person_field_definitions())
        return super().get_form(request, obj, change, **kwargs)

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    # -- list -----------------------------------------------------------------------------------
    def get_queryset(self, request: HttpRequest) -> Any:
        return (
            super()
            .get_queryset(request)
            .annotate(
                student_records_count=Count("student_records", distinct=True),
                account_exists=Exists(User.objects.filter(person_id=OuterRef("pk"))),
            )
        )

    def get_search_fields(self, request: HttpRequest) -> tuple[str, ...]:
        return ("family_name",)

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        return queryset.search(term), False

    @display(description=pgettext_lazy("people", "Name"), ordering="family_name")
    def name_column(self, obj: Person) -> Any:
        return format_html(
            "{}<br><span class='text-xs text-base-500'>{}</span>", obj.display_name(), obj.romanized_name()
        )

    @display(description=_("Student records"))
    def records_count(self, obj: Person) -> int:
        return int(getattr(obj, "student_records_count", 0) or 0)

    @display(description=_("Account"), boolean=True)
    def has_account(self, obj: Person) -> bool:
        return bool(getattr(obj, "account_exists", False))

    # -- detail ---------------------------------------------------------------------------------
    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is not None and not self.has_change_permission(request, obj):
            return [
                (
                    pgettext_lazy("people", "Name"),
                    {"fields": ("photo_view", "display_name_view", "romanized_name_view")},
                ),
                (
                    _("Personal details"),
                    {
                        "fields": (
                            "birth_date",
                            "gender_view",
                            "nationality",
                            "ethnicity",
                            "national_id_masked",
                            "passport_number_masked",
                        )
                    },
                ),
                (_("Contact"), {"fields": ("email", "phone", "address", "postal_code")}),
                (_("Account"), {"fields": ("login_email", "merged_into_view")}),
            ]
        names = ["family_name", "given_name", *(f"name_{code}" for code, _label in _other_languages())]
        fieldsets: list[Any] = [
            (pgettext_lazy("people", "Name"), {"fields": names}),
            (
                _("Personal details"),
                {
                    "fields": [
                        "birth_date",
                        "gender",
                        "nationality",
                        "ethnicity",
                        "national_id_input",
                        "passport_number_input",
                    ]
                },
            ),
            (_("Contact"), {"fields": ["email", "phone", "address", "postal_code"]}),
            (_("Photo"), {"fields": ["photo"]}),
        ]
        if obj is not None:
            fieldsets[1][1]["fields"][4:4] = ["national_id_masked", "passport_number_masked"]
            fieldsets[3] = (_("Photo"), {"fields": ["photo_view", "photo"]})
            fieldsets.append((_("Account"), {"fields": ["login_email", "merged_into_view"]}))
        return fieldsets

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is not None and not self.has_change_permission(request, obj):
            return self.readonly_fields
        return ("photo_view", "national_id_masked", "passport_number_masked", "login_email", "merged_into_view")

    def get_inlines(self, request: HttpRequest, obj: Any) -> Any:
        return self.inlines if obj is not None else ()

    def save_model(self, request: HttpRequest, obj: Person, form: Any, change: bool) -> None:
        super().save_model(request, obj, form, change)
        photo = form.cleaned_data.get("photo")
        if photo:
            try:
                add_media(obj, photo, Person.PHOTO_COLLECTION)
            except MediaError as error:
                messages.error(request, " ".join(error.messages))

    def change_view(self, request: HttpRequest, object_id: str, form_url: str = "", extra_context: Any = None) -> Any:
        extra_context = extra_context or {}
        person = self.get_object(request, object_id)
        if person is not None:
            extra_context["change_history"] = record_changes(
                [("people", [person.pk]), ("guardians", person.guardians.values_list("pk", flat=True))]
            )
            extra_context["can_view_audit"] = request.user.has_perm(Permission.AUDIT_RECORDS_VIEW)
        return super().change_view(request, object_id, form_url, extra_context)

    @display(description=pgettext_lazy("people", "Name"))
    def display_name_view(self, obj: Person) -> str:
        return obj.display_name()

    @display(description=_("Romanized name"))
    def romanized_name_view(self, obj: Person) -> str:
        return obj.romanized_name()

    @display(description=_("Gender"))
    def gender_view(self, obj: Person) -> str:
        return str(Gender(obj.gender).label) if obj.gender else "-"

    @display(description=_("National ID number"))
    def national_id_masked(self, obj: Person) -> str:
        return obj.masked_pii("national_id") or "-"

    @display(description=_("Passport number"))
    def passport_number_masked(self, obj: Person) -> str:
        return obj.masked_pii("passport_number") or "-"

    @display(description=_("Photo"))
    def photo_view(self, obj: Person) -> Any:
        if obj.pk is None or obj.get_first_media(Person.PHOTO_COLLECTION) is None:
            return "-"
        return format_html(
            '<img src="{}" alt="" class="h-32 rounded border border-base-200">', reverse("person:photo", args=[obj.pk])
        )

    @display(description=_("Sign-in email"))
    def login_email(self, obj: Person) -> str:
        account = obj.account()
        return account.email if account is not None else str(_("No account"))

    @display(description=_("Merged into"))
    def merged_into_view(self, obj: Person) -> Any:
        if obj.merged_into_id is None:
            return "-"
        return format_html('<a class="underline" href="{}">{}</a>', admin_change_url(obj.merged_into), obj.merged_into)

    # -- detail actions (original ViewPerson header actions) -------------------------------------
    def _person(self, request: HttpRequest, object_id: Any) -> Person:
        return get_object_or_404(Person.objects.visible_to(request.user), pk=object_id)

    def has_reveal_national_id_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._may_reveal(request, object_id, "national_id")

    def has_reveal_passport_number_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._may_reveal(request, object_id, "passport_number")

    def _may_reveal(self, request: HttpRequest, object_id: Any, attribute: str) -> bool:
        if object_id is None or not request.user.has_perm(Permission.PEOPLE_VIEW_SENSITIVE):
            return False
        person = Person.objects.visible_to(request.user).filter(pk=object_id).first()
        return (
            person is not None
            and getattr(person, f"{attribute}_encrypted") is not None
            and request.user.has_perm("view_sensitive", person)
        )

    def has_invite_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if object_id is None:
            return False
        person = Person.objects.visible_to(request.user).filter(pk=object_id).first()
        return (
            person is not None
            and person.merged_into_id is None
            and person.account() is None
            and request.user.has_perm("invite", person)
        )

    def has_merge_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if object_id is None:
            return False
        person = Person.objects.visible_to(request.user).filter(pk=object_id).first()
        return person is not None and request.user.has_perm("merge", person)

    @action(
        description=_("Show national ID number"),
        url_path="reveal-national-id",
        permissions=["reveal_national_id"],
        icon="visibility",
        dialog={
            "title": _("Show national ID number"),
            "description": _("The full value is shown once and the reveal is recorded in the security log."),
            "form_class": RevealForm,
        },
    )
    def reveal_national_id(self, request: HttpRequest, form: RevealForm, object_id: Any) -> HttpResponse:
        return self._reveal(request, object_id, "national_id", form.cleaned_data["reason"], _("National ID number"))

    @action(
        description=_("Show passport number"),
        url_path="reveal-passport-number",
        permissions=["reveal_passport_number"],
        icon="visibility",
        dialog={
            "title": _("Show passport number"),
            "description": _("The full value is shown once and the reveal is recorded in the security log."),
            "form_class": RevealForm,
        },
    )
    def reveal_passport_number(self, request: HttpRequest, form: RevealForm, object_id: Any) -> HttpResponse:
        return self._reveal(request, object_id, "passport_number", form.cleaned_data["reason"], _("Passport number"))

    def _reveal(self, request: HttpRequest, object_id: Any, attribute: str, reason: str, label: Any) -> HttpResponse:
        person = self._person(request, object_id)
        if not request.user.has_perm("view_sensitive", person):
            raise PermissionDenied
        value = RevealSensitiveValue()(request.user, person, attribute, Permission.PEOPLE_VIEW_SENSITIVE, reason)
        # Shown on this response only: never stored in the session (flash messages) or logs.
        response = render(
            request,
            "person/admin/revealed.html",
            {
                **self.admin_site.each_context(request),
                "title": label,
                "subtitle": person.display_name(),
                "value": value,
                "opts": self.model._meta,
                "back_url": admin_change_url(person),
            },
        )
        response["Cache-Control"] = "no-store"
        return response

    @action(description=_("Invite to create an account"), url_path="invite", permissions=["invite"], icon="mail")
    def invite(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        person = self._person(request, object_id)
        form = InviteForm(request.POST or None, initial={"email": person.email})
        if request.method == "POST" and form.is_valid():
            try:
                InvitePerson().handle(person, form.cleaned_data["email"], request.user, request.build_absolute_uri("/"))
            except ValidationError as error:
                apply_errors(form, error)
            else:
                messages.success(request, _("Invitation sent."))
                return HttpResponseRedirect(admin_change_url(person))
        return form_page(
            self,
            request,
            form,
            _("Invite to create an account"),
            admin_change_url(person),
            subtitle=person.display_name(),
        )

    @action(
        description=_("Merge duplicate"),
        url_path="merge",
        permissions=["merge"],
        icon="merge",
        variant=ActionVariant.DANGER,
    )
    def merge(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        person = self._person(request, object_id)
        candidates = (
            Person.objects.visible_to(request.user)
            .not_merged()
            .exclude(pk=person.pk)
            .order_by("family_name", "given_name")
        )
        form = MergeForm(request.POST or None, queryset=candidates)
        if request.method == "POST" and form.is_valid():
            try:
                target = MergePeople().handle(
                    person, form.cleaned_data["target"], form.cleaned_data["reason"], request.user
                )
            except ValidationError as error:
                apply_errors(form, error)
            else:
                messages.success(request, _("People merged."))
                return HttpResponseRedirect(admin_change_url(target))
        return form_page(
            self,
            request,
            form,
            _("Merge duplicate"),
            admin_change_url(person),
            subtitle=person.display_name(),
            description=_(
                "The other person's student records, instructor record, guardians and account move to the person "
                "you keep. The other person is marked as merged and cannot be used again. This cannot be undone."
            ),
        )
