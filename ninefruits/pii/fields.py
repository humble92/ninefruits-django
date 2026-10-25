"""Encrypted personal data columns (original EncryptedPii cast + HasEncryptedPii trait).

For each encrypted attribute the table has ``<name>_encrypted`` (text, ciphertext) and
``<name>_hash`` (char 64, HMAC search index)::

    class Person(EncryptedPiiModel, models.Model):
        national_id_encrypted = EncryptedPiiField(PiiType.NATIONAL_ID, hash_field="national_id_hash")
        national_id_hash = PiiHashField()

    person.national_id_encrypted = "900101-1234567"   # plaintext in Python, ciphertext in the DB
    Person.objects.where_pii("national_id", "9001011234567")
    person.masked_pii("national_id")                  # "**********4567"

The attribute holds the plaintext; it is decrypted lazily on first access and encrypted on
save only when it was assigned (an unchanged value keeps its ciphertext, so saving a row does
not produce a spurious data audit entry). The hash column follows the value on every save.

Screens show :meth:`EncryptedPiiModel.masked_pii`. Showing the value requires the
``*.view_sensitive`` permission and goes through ``ninefruits.pii.actions.RevealSensitiveValue``
(security log). The field is not editable in model forms, is serialized as ciphertext and must
never appear in ``__repr__``, logs, serializers or admin lists (original H1)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from ninefruits.pii.cipher import cipher
from ninefruits.pii.hasher import pii_hash
from ninefruits.pii.types import PiiType

ENCRYPTED_SUFFIX = "_encrypted"


# Both fields are nullable by default (null=True below), so the attribute is ``str | None``.
# Django fields are not subscriptable at run time; the parameters are for django-stubs only.
if TYPE_CHECKING:
    _NullableTextField = models.TextField[str | None, str | None]
    _NullableCharField = models.CharField[str | None, str | None]
else:
    _NullableTextField = models.TextField
    _NullableCharField = models.CharField


class _Undecrypted:
    """Marker: the ciphertext is loaded but not decrypted yet (a class, so it survives pickling)."""


class _Dirty:
    """Marker: a plaintext was assigned and will be encrypted on save."""


class Ciphertext(str):
    """A value already encrypted (read from the database or encrypted on save)."""

    __slots__ = ()


def _cipher_key(attname: str) -> str:
    return f"_{attname}_ciphertext"


class EncryptedPiiDescriptor(DeferredAttribute):
    """Keeps the plaintext and the stored ciphertext apart on the instance."""

    def __get__(self, instance: Any, cls: Any = None) -> Any:
        if instance is None:
            return self
        attname = self.field.attname
        if attname not in instance.__dict__:
            return super().__get__(instance, cls)  # deferred: loads through __set__
        value = instance.__dict__[attname]
        if value is _Undecrypted:
            stored = instance.__dict__.get(_cipher_key(attname))
            value = None if stored is None else cipher().decrypt(str(stored))
            instance.__dict__[attname] = value
        return value

    def __set__(self, instance: Any, value: Any) -> None:
        attname = self.field.attname
        if isinstance(value, Ciphertext):
            instance.__dict__[attname] = _Undecrypted
            instance.__dict__[_cipher_key(attname)] = value
        else:
            instance.__dict__[attname] = None if value in (None, "") else str(value)
            instance.__dict__[_cipher_key(attname)] = None if value in (None, "") else _Dirty


class EncryptedPiiField(_NullableTextField):
    """Text column holding the PII ciphertext (see the module docstring)."""

    descriptor_class = EncryptedPiiDescriptor

    def __init__(
        self, pii_type: PiiType | str = PiiType.GENERIC, *args: Any, hash_field: str | None = None, **kwargs: Any
    ):
        self.pii_type = PiiType(pii_type)
        self.hash_field = hash_field
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("editable", False)
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        kwargs["pii_type"] = self.pii_type.value
        if self.hash_field:
            kwargs["hash_field"] = self.hash_field
        for key, default in (("null", True), ("blank", True), ("editable", False)):
            if kwargs.get(key, not default) == default:
                kwargs.pop(key, None)
        return name, path, args, kwargs

    @property
    def pii_name(self) -> str:
        """``national_id`` for ``national_id_encrypted``."""
        return self.name.removesuffix(ENCRYPTED_SUFFIX)

    def contribute_to_class(self, cls: type[models.Model], name: str, private_only: bool = False) -> None:
        super().contribute_to_class(cls, name, private_only)
        if self.hash_field and not cls._meta.abstract:
            models.signals.pre_save.connect(self._sync_hash, sender=cls, weak=False)

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        return None if value is None else Ciphertext(value)

    def to_python(self, value: Any) -> Any:
        return value

    def pre_save(self, model_instance: models.Model, add: bool) -> Any:
        state = model_instance.__dict__.get(_cipher_key(self.attname))
        if isinstance(state, Ciphertext):
            return state
        plaintext = getattr(model_instance, self.attname)
        if plaintext in (None, ""):
            return None
        encrypted = Ciphertext(cipher().encrypt(str(plaintext)))
        model_instance.__dict__[_cipher_key(self.attname)] = encrypted
        return encrypted

    def get_prep_value(self, value: Any) -> Any:
        if value is None or value == "":
            return None
        if isinstance(value, Ciphertext):
            return str(value)
        if hasattr(value, "resolve_expression"):
            return value
        return cipher().encrypt(str(value))

    def value_to_string(self, obj: models.Model) -> str:
        """Serializers (dumpdata) get the ciphertext, never the plaintext."""
        stored = self.pre_save(obj, False)
        return "" if stored is None else str(stored)

    def ciphertext(self, instance: models.Model) -> str | None:
        """The stored payload (``None`` when empty or not yet saved)."""
        state = instance.__dict__.get(_cipher_key(self.attname))
        return str(state) if isinstance(state, Ciphertext) else None

    def _sync_hash(self, sender: type[models.Model], instance: models.Model, **kwargs: Any) -> None:
        if self.attname not in instance.__dict__ or not self.hash_field:
            return
        state = instance.__dict__.get(_cipher_key(self.attname))
        if isinstance(state, Ciphertext):
            return  # unchanged since loaded or last saved
        value = getattr(instance, self.attname)
        setattr(instance, self.hash_field, None if value is None else pii_hash(value, self.pii_type))


class PiiHashField(_NullableCharField):
    """``<name>_hash`` char(64): HMAC-SHA256 search index of an encrypted value."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 64)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("editable", False)
        super().__init__(*args, **kwargs)


class EncryptedPiiQuerySet(models.QuerySet[Any]):
    def where_pii(self, name: str, value: str) -> Self:
        """Exact match on an encrypted attribute through its hash."""
        field = encrypted_pii_fields(self.model)[name]
        if not field.hash_field:
            raise ValueError(f"[{name}] has no search hash.")
        return self.filter(**{field.hash_field: pii_hash(value, field.pii_type)})


class EncryptedPiiModel(models.Model):
    """Mixin for models with encrypted personal data (original EncryptsPersonalData)."""

    objects: ClassVar[Any] = EncryptedPiiQuerySet.as_manager()

    class Meta:
        abstract = True

    @classmethod
    def encrypted_pii_attributes(cls) -> dict[str, PiiType]:
        """Attribute names (without ``_encrypted``) and their type."""
        return {name: field.pii_type for name, field in encrypted_pii_fields(cls).items()}

    def masked_pii(self, name: str) -> str | None:
        field = encrypted_pii_fields(type(self))[name]
        value = getattr(self, field.attname)
        return None if value is None else field.pii_type.mask(value)


def encrypted_pii_fields(model: type[models.Model]) -> dict[str, EncryptedPiiField]:
    return {field.pii_name: field for field in model._meta.concrete_fields if isinstance(field, EncryptedPiiField)}


def has_encrypted_pii(model: type[models.Model]) -> bool:
    return bool(encrypted_pii_fields(model))
