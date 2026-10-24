"""Seeder framework (original ``Illuminate\\Database\\Seeder`` + ``SeedsTranslatedRows``).

Three kinds (porting-plan 13.4):

- ``essential``: data the system needs to work. Runs in every environment on every deployment
  (``setup_install``) and is idempotent: rows are found by code, and values administrators
  changed are kept; only missing rows and missing translations are added.
- ``profiles``: optional rule bundles chosen at installation, idempotent too.
- ``demo``: a fictional university for development and training (``setup_demo``), never in
  production.

A seeder is a class with ``run()``; ``call()`` runs others in order.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from django.conf import settings
from django.db import models, transaction


class Seeder:
    def run(self) -> None:
        raise NotImplementedError

    def __call__(self) -> None:
        with transaction.atomic():
            self.run()

    def call(self, *seeders: type[Seeder] | Seeder) -> None:
        for seeder in seeders:
            instance = seeder() if isinstance(seeder, type) else seeder
            instance()


def installed_languages() -> list[str]:
    """Languages with a translation catalog (original: the ``lang/`` directories)."""
    from ninefruits.institution.services.supported_locales import has_catalog

    codes = [code for code, _name in settings.LANGUAGES if code == settings.LANGUAGE_CODE or has_catalog(code)]
    return sorted(dict.fromkeys(codes))


def seed_row[M: models.Model](
    model: type[M],
    keys: Mapping[str, Any],
    translations: Mapping[str, Mapping[str, str]],
    attributes: Mapping[str, Any] | None = None,
) -> M:
    """Creates the row when missing; for an existing row only adds translations for languages
    that have none yet. Values administrators edited stay."""
    instance = model._default_manager.filter(**keys).first()
    if instance is None:
        return model._default_manager.create(**{**keys, **(attributes or {}), **translations})
    if _add_missing_translations(instance, translations):
        instance.save()
    return instance


def seed_rows[M: models.Model](
    model: type[M],
    key: str,
    rows: Iterable[tuple[Any, Mapping[str, Mapping[str, str]], Mapping[str, Any]]],
) -> int:
    """``seed_row`` for many rows found by one key column (one query to read, bulk insert of the
    missing rows). Returns the number of rows created."""
    rows = list(rows)
    existing = {getattr(row, key): row for row in model._default_manager.filter(**{f"{key}__in": [r[0] for r in rows]})}
    missing = []
    for value, translations, attributes in rows:
        instance = existing.get(value)
        if instance is None:
            missing.append(model(**{key: value, **attributes, **translations}))
        elif _add_missing_translations(instance, translations):
            instance.save()
    model._default_manager.bulk_create(missing, batch_size=500)
    return len(missing)


def _add_missing_translations(instance: models.Model, translations: Mapping[str, Mapping[str, str]]) -> bool:
    changed = False
    for attribute, texts in translations.items():
        current = dict(getattr(instance, f"{attribute}_translations"))
        missing = {code: text for code, text in texts.items() if code not in current and text}
        if missing:
            setattr(instance, attribute, {**current, **missing})
            changed = True
    return changed
