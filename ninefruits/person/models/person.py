"""People (original ``App\\Models\\Person\\Person`` and ``Guardian``, ADR 0007).

A person is one row for life. Student records, the instructor record, guardians and the login
account all point here. The legal name is romanized (``family_name``, ``given_name``);
``name_variants`` holds the name as written in other languages or scripts, e.g.
``{"ko": "김민수", "zh-hans": "金敏秀"}``. National ID and passport numbers are encrypted
(``ninefruits.pii``) and searchable only by exact match through their HMAC hash."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.expressions import Func, RawSQL
from django.utils.translation import get_language, pgettext_lazy
from django.utils.translation import gettext_lazy as _

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.media.services import IMAGES, HasMedia, MediaCollection
from ninefruits.person.enums import Gender, GuardianRelationship
from ninefruits.pii.fields import EncryptedPiiField, EncryptedPiiModel, EncryptedPiiQuerySet, PiiHashField
from ninefruits.pii.hasher import pii_hash
from ninefruits.pii.types import PiiType
from ninefruits.security.enums import Permission

#: Extra conditions under which a person is visible (``user -> Q``). Phase 3 adds people whose
#: applications the user can see (original ``orWhereHas('applications', ...)``).
PERSON_VISIBILITY: list[Callable[[Any], Q]] = []

_SEARCH_SQL = (
    "SELECT people.id FROM people WHERE (people.family_name || ' ' || coalesce(people.given_name, '') || ' ' "
    "|| util.i18n_search_text(people.name_variants)) ILIKE %s"
)


class PersonQuerySet(EncryptedPiiQuerySet, VisibleQuerySet):  # type: ignore[override]  # both bases get a plugin as_manager
    def visible_to(self, user: Any) -> Self:
        """People the user may see: everyone with ``people.view``, otherwise themselves, people
        they created, people whose student records (or applications) they can see, and
        instructors. Mirrors the row level security policies on ``people``."""
        if user.has_perm(Permission.PEOPLE_VIEW):
            return self
        from .student_record import StudentRecord

        condition = Q(created_by_id=user.pk) | Q(instructor__isnull=False)
        if user.person_id is not None:
            condition |= Q(pk=user.person_id)
        condition |= Q(pk__in=StudentRecord.objects.visible_to(user).values("person_id"))
        for extension in PERSON_VISIBILITY:
            condition |= extension(user)
        return self.filter(condition).distinct()

    def not_merged(self) -> Self:
        return self.filter(merged_into__isnull=True)

    def search(self, term: str) -> Self:
        """Romanized name, any name variant, or exact national ID / passport number."""
        term = term.strip()
        condition = Q(pk__in=RawSQL(_SEARCH_SQL, ["%" + term + "%"]))  # noqa: S611 - constant SQL, bound value  # nosec B611
        condition |= Q(national_id_hash=pii_hash(term, PiiType.NATIONAL_ID))
        condition |= Q(passport_number_hash=pii_hash(term, PiiType.PASSPORT_NUMBER))
        return self.filter(condition)


class Person(HasMedia, EncryptedPiiModel, TimeStampedModel):
    PHOTO_COLLECTION: ClassVar[str] = "photo"
    #: Fields a person may change about themselves in the portal.
    SELF_EDITABLE: ClassVar[tuple[str, ...]] = ("email", "phone", "address", "postal_code")
    media_collections: ClassVar[dict[str, MediaCollection]] = {
        "photo": MediaCollection("photo", single_file=True, accepts=IMAGES),
    }

    family_name = models.CharField(_("Family name"), max_length=255)
    given_name = models.CharField(_("Given name"), max_length=255, null=True, blank=True)
    name_variants = models.JSONField(_("Name in other languages"), null=True, blank=True)
    birth_date = models.DateField(_("Birth date"), null=True, blank=True)
    gender = models.CharField(_("Gender"), max_length=16, choices=Gender.choices, null=True, blank=True)
    nationality = models.ForeignKey(
        "institution.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="nationality_country_id",
        related_name="+",
        verbose_name=_("Nationality"),
    )
    ethnicity = models.ForeignKey(
        "institution.LookupValue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Ethnicity"),
    )
    email = models.CharField(_("Contact email"), max_length=255, null=True, blank=True)
    phone = models.CharField(_("Phone"), max_length=32, null=True, blank=True)
    address = models.TextField(_("Address"), null=True, blank=True)
    postal_code = models.CharField(_("Postal code"), max_length=16, null=True, blank=True)
    national_id_encrypted = EncryptedPiiField(PiiType.NATIONAL_ID, hash_field="national_id_hash")
    national_id_hash = PiiHashField()
    passport_number_encrypted = EncryptedPiiField(PiiType.PASSPORT_NUMBER, hash_field="passport_number_hash")
    passport_number_hash = PiiHashField()
    merged_into = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="merged_into_person_id",
        related_name="merged_people",
        verbose_name=_("Merged into"),
    )
    # The column defaults to util.current_user_id() so that INSERT ... RETURNING passes the
    # creator SELECT policy before the person has a student record (ADR 0007).
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_default=Func(function="util.current_user_id"),
        editable=False,
    )

    objects = PersonQuerySet.as_manager()  # type: ignore[misc]  # narrows the EncryptedPiiModel manager

    class Meta:
        db_table = "people"
        verbose_name = _("person")
        verbose_name_plural = _("people")

    def __str__(self) -> str:
        return self.display_name()

    def __repr__(self) -> str:
        return f"<Person {self.pk}>"

    def display_name(self, locale: str | None = None) -> str:
        """The variant for the locale (or its base language), else the romanized name."""
        locale = locale or get_language() or settings.LANGUAGE_CODE
        variants = self.name_variants if isinstance(self.name_variants, dict) else {}
        base = locale.replace("_", "-").split("-")[0]
        return str(variants.get(locale) or variants.get(base) or self.romanized_name())

    def romanized_name(self) -> str:
        return f"{self.given_name or ''} {self.family_name}".strip()

    def is_visible_to(self, user: Any) -> bool:
        return Person.objects.visible_to(user).filter(pk=self.pk).exists()

    @property
    def national_id(self) -> str | None:
        return self.national_id_encrypted

    @property
    def passport_number(self) -> str | None:
        return self.passport_number_encrypted

    def account(self) -> Any:
        """The login account (``users.person_id``), if any."""
        from ninefruits.security.models import User

        return User.objects.filter(person_id=self.pk).first()


class Guardian(TimeStampedModel):
    """Guardian or family contact of a person (legacy SRFAMILY and the SR_PT* columns)."""

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="guardians")
    relationship = models.CharField(_("Relationship"), max_length=32, choices=GuardianRelationship.choices)
    full_name = models.CharField(pgettext_lazy("people", "Name"), max_length=255)
    phone = models.CharField(_("Phone"), max_length=32, null=True, blank=True)
    email = models.CharField(_("Contact email"), max_length=255, null=True, blank=True)
    address = models.TextField(_("Address"), null=True, blank=True)
    is_primary_contact = models.BooleanField(_("Primary contact"), default=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "guardians"
        ordering = ["-is_primary_contact", "id"]
        verbose_name = _("guardian")
        verbose_name_plural = _("guardians")

    def __str__(self) -> str:
        return self.full_name

    def __repr__(self) -> str:
        return f"<Guardian {self.pk} person={self.person_id}>"
