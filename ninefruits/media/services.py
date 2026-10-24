"""Private file storage for records (original spatie/laravel-medialibrary usage: ``addMedia``,
``addMediaFromString``, ``toMediaCollection``, ``singleFile``, ``acceptsMimeTypes``,
``clearMediaCollection``, ``getFirstMedia``; ``media:prune-orphans``).

    class Application(HasMedia, models.Model):
        media_collections = {"documents": MediaCollection("documents", accepts=PDF_AND_IMAGES)}

    media = add_media(application, upload, "documents", custom_properties={"document_type_id": 3})

Every stored file records its SHA-256 in ``custom_properties["sha256"]``. The MIME type is
sniffed from the content (libmagic, like spatie's finfo), never taken from the client."""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import re
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import IO, Any, ClassVar

import magic
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile, File
from django.core.files.storage import Storage, storages
from django.db import models, transaction
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from ninefruits.core import morph
from ninefruits.media.models import Media

DEFAULT_DISK = "default"
# Disk names of restored original rows (Laravel filesystem disks) and the storage serving them.
LEGACY_DISKS = {"local": DEFAULT_DISK, "public": DEFAULT_DISK}
# spatie media-library max_file_size default (10 MB). Collections may set a lower limit.
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024
# spatie FileAdder::$defaultDisallowedExtensions: refused anywhere in the name (shell.php.jpg).
DISALLOWED_EXTENSIONS = frozenset(
    {
        "php", "php3", "php4", "php5", "php6", "php7", "php8", "phtml", "phtm", "pht", "phps", "phar",
        "shtml", "shtm", "stm", "htaccess", "htpasswd", "cgi", "pl", "asp", "aspx", "jsp", "jspx",
    }
)  # fmt: skip
SNIFF_BYTES = 8192

PDF = ("application/pdf",)
IMAGES = ("image/jpeg", "image/png", "image/webp")
PDF_AND_IMAGES = ("application/pdf", "image/jpeg", "image/png")

logger = logging.getLogger(__name__)


class MediaError(ValidationError):
    """Base of the upload errors (spatie FileCannotBeAdded); a ValidationError so forms show it."""


class FileTooBig(MediaError):
    pass


class FileUnacceptableForCollection(MediaError):
    pass


class FileNameNotAllowed(MediaError):
    pass


@dataclass(frozen=True, slots=True)
class MediaCollection:
    name: str
    single_file: bool = False
    accepts: tuple[str, ...] = ()
    disk: str = DEFAULT_DISK
    max_size: int | None = None

    def accepts_mime(self, mime_type: str | None) -> bool:
        return not self.accepts or (mime_type or "") in self.accepts


@dataclass(slots=True)
class PruneSummary:
    rows: int = 0
    directories: int = 0
    orphan_rows: list[str] = field(default_factory=list)
    orphan_directories: list[str] = field(default_factory=list)


class HasMedia:
    """Mixin for owner models (original HasMedia/InteractsWithMedia)."""

    media_collections: ClassVar[dict[str, MediaCollection]] = {}

    def get_media(self, collection: str = "default") -> models.QuerySet[Media]:
        return Media.objects.for_owner(self, collection).order_by("order_column", "id")  # type: ignore[arg-type]

    def get_first_media(self, collection: str = "default") -> Media | None:
        return self.get_media(collection).first()


def storage_for(disk: str) -> Storage:
    """The storage of a disk name; original disk names map to the private storage."""
    alias = LEGACY_DISKS.get(disk, disk)
    if alias not in settings.STORAGES:
        alias = DEFAULT_DISK
    return storages[alias]


def collection_for(owner: models.Model, name: str) -> MediaCollection:
    collections: dict[str, MediaCollection] = getattr(owner, "media_collections", {}) or {}
    return collections.get(name) or MediaCollection(name)


def sanitize_file_name(file_name: str) -> str:
    """spatie defaultSanitizer: removes control characters, turns spaces into ``-`` and path
    separators and ``#`` into ``-``; refuses dangerous extensions anywhere in the name."""
    name = "".join(ch for ch in file_name if unicodedata.category(ch)[0] != "C")
    name = "".join("-" if unicodedata.category(ch).startswith("Z") else ch for ch in name)
    name = re.sub(r"[#/\\]", "-", name)
    extensions = [part.lower() for part in name.split(".")[1:]]
    offending = [ext for ext in extensions if ext in DISALLOWED_EXTENSIONS]
    if offending or name in ("", ".", ".."):
        raise FileNameNotAllowed(
            _("The file name %(name)s is not allowed.") % {"name": file_name}, code="file_name_not_allowed"
        )
    return name


def header_safe_file_name(file_name: str) -> str:
    """For Content-Disposition: no quotes or line breaks (original security review L5)."""
    return re.sub(r"[\"\r\n]", "", file_name) or "download"


def sniff_mime_type(head: bytes) -> str:
    return str(magic.from_buffer(head, mime=True))


def _read_head(source: IO[bytes]) -> bytes:
    position = source.tell() if source.seekable() else None
    head = source.read(SNIFF_BYTES)
    if position is not None:
        source.seek(position)
    return head


def _checksum_and_size(source: IO[bytes]) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    if source.seekable():
        source.seek(0)
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
        size += len(chunk)
    if source.seekable():
        source.seek(0)
    return digest.hexdigest(), size


def add_media(
    owner: models.Model,
    file: File[Any] | IO[bytes],
    collection: str = "default",
    *,
    file_name: str | None = None,
    name: str | None = None,
    custom_properties: dict[str, Any] | None = None,
) -> Media:
    """Stores ``file`` for ``owner`` in ``collection`` and returns the media row.

    Checks size (collection limit or 10 MB), file name and the sniffed MIME type against the
    collection; a single file collection keeps only the new file."""
    if owner.pk is None:
        raise ValueError("The owner must be saved before files are attached.")
    definition = collection_for(owner, collection)
    original_name = file_name or PurePosixPath(str(getattr(file, "name", "") or "file")).name
    clean_name = sanitize_file_name(original_name)
    source: IO[bytes] = file.file if isinstance(file, File) and file.file is not None else file

    checksum, size = _checksum_and_size(source)
    limit: int = definition.max_size or int(getattr(settings, "MEDIA_MAX_FILE_SIZE", DEFAULT_MAX_FILE_SIZE))
    if size > limit:
        raise FileTooBig(
            _("The file is too big (%(size)s bytes, at most %(limit)s).") % {"size": size, "limit": limit},
            code="file_too_big",
        )
    mime_type = sniff_mime_type(_read_head(source))
    if not definition.accepts_mime(mime_type):
        raise FileUnacceptableForCollection(
            _("This type of file (%(mime)s) is not accepted here.") % {"mime": mime_type}, code="file_type_not_accepted"
        )

    storage = storage_for(definition.disk)
    with transaction.atomic():
        order = (Media.objects.aggregate(top=Max("order_column"))["top"] or 0) + 1
        media = Media.objects.create(
            model_type=morph.morph_type(owner),
            model_id=owner.pk,
            collection_name=collection,
            name=name if name is not None else PurePosixPath(original_name).stem,
            file_name=clean_name,
            mime_type=mime_type,
            disk=definition.disk,
            conversions_disk=definition.disk,
            size=size,
            manipulations=[],
            custom_properties={**(custom_properties or {}), "sha256": checksum},
            generated_conversions=[],
            responsive_images=[],
            order_column=order,
        )
        if storage.exists(media.path):
            # The row is new, so no media row of this database owns the file: it is an orphan
            # left by an earlier database on the same storage (e.g. a re-created demo). Spatie
            # overwrote such files; replace it the same way.
            logger.warning("Replacing orphaned file at %s", media.path)
            storage.delete(media.path)
        stored = storage.save(media.path, File(source, name=clean_name))
        if stored != media.path:  # the storage renamed it (should not happen in a fresh directory)
            storage.delete(stored)
            raise RuntimeError("Media path is already taken.")
        if definition.single_file:
            for previous in Media.objects.for_owner(owner, collection).exclude(pk=media.pk):
                delete_media(previous)
    return media


def add_media_from_bytes(
    owner: models.Model, content: bytes, file_name: str, collection: str = "default", **kwargs: Any
) -> Media:
    """``addMediaFromString`` (generated files such as certificate PDFs)."""
    return add_media(owner, ContentFile(content, name=file_name), collection, file_name=file_name, **kwargs)


def open_media(media: Media) -> IO[bytes]:
    handle: IO[bytes] = storage_for(media.disk).open(media.path, "rb")
    return handle


def delete_media(media: Media) -> None:
    """Deletes the row and its directory (spatie removes the whole ``<id>/`` directory)."""
    storage = storage_for(media.disk)
    directory = media.directory
    media.delete()
    _delete_directory(storage, directory)


def clear_collection(owner: models.Model, collection: str = "default") -> int:
    count = 0
    for media in Media.objects.for_owner(owner, collection):
        delete_media(media)
        count += 1
    return count


def _delete_directory(storage: Storage, directory: str) -> None:
    try:
        subdirectories, files = storage.listdir(directory)
    except FileNotFoundError, NotADirectoryError:
        return
    for name in files:
        storage.delete(f"{directory}/{name}")
    for name in subdirectories:
        _delete_directory(storage, f"{directory}/{name}")
    path = getattr(storage, "path", None)
    if path is not None:
        with contextlib.suppress(OSError):
            os.rmdir(path(directory))


def _owner_exists(media: Media) -> bool:
    type_name = media.model_type
    if "\\" in type_name:
        return False  # an original PHP class name without a mapping
    try:
        model = apps.get_model(type_name)
    except LookupError, ValueError:
        return False
    return bool(model._default_manager.filter(pk=media.model_id).exists())


def iter_orphan_rows() -> Iterator[Media]:
    for media in Media.objects.order_by("id").iterator(chunk_size=500):
        if not _owner_exists(media):
            yield media


def prune_orphans(*, dry_run: bool = False, disks: Iterable[str] = (DEFAULT_DISK,)) -> PruneSummary:
    """Removes media rows whose owner no longer exists and directories on the media storage that
    no row refers to (original ``media:prune-orphans``)."""
    summary = PruneSummary()
    for media in list(iter_orphan_rows()):
        summary.rows += 1
        summary.orphan_rows.append(f"media #{media.pk} ({media.model_type} #{media.model_id})")
        if not dry_run:
            delete_media(media)

    ids = set(Media.objects.values_list("id", flat=True))
    for disk in disks:
        storage = storage_for(disk)
        try:
            directories, _files = storage.listdir("")
        except FileNotFoundError:
            continue
        for directory in sorted(directories):
            if not directory.isdigit() or int(directory) in ids:
                continue
            summary.directories += 1
            summary.orphan_directories.append(directory)
            if not dry_run:
                _delete_directory(storage, directory)
    return summary
