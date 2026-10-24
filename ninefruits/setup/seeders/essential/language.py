from __future__ import annotations

import pycountry
from babel import Locale
from django.utils.translation import to_locale

from ninefruits.institution.models import Language
from ninefruits.setup.seeders.base import Seeder, installed_languages, seed_rows


class LanguageSeeder(Seeder):
    """ISO 639-1 languages (two-letter codes) with names in every installed language."""

    def run(self) -> None:
        locales = {code: Locale.parse(to_locale(code)) for code in installed_languages()}
        rows = []
        for language in sorted(
            (item for item in pycountry.languages if hasattr(item, "alpha_2")), key=lambda item: item.alpha_2
        ):
            names = {
                code: locale.languages.get(language.alpha_2) or str(language.name) for code, locale in locales.items()
            }
            rows.append((language.alpha_2, {"name": names}, {"alpha3_code": getattr(language, "alpha_3", None)}))
        seed_rows(Language, "code", rows)
