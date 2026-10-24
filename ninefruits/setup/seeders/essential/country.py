from __future__ import annotations

import pycountry
from babel import Locale
from django.utils.translation import to_locale

from ninefruits.institution.models import Country
from ninefruits.setup.seeders.base import Seeder, installed_languages, seed_rows


class CountrySeeder(Seeder):
    """ISO 3166-1 countries (pycountry) with names in every installed language (CLDR data
    through Babel; the original used symfony/intl, also CLDR)."""

    def run(self) -> None:
        locales = {code: Locale.parse(to_locale(code)) for code in installed_languages()}
        rows = []
        for country in sorted(pycountry.countries, key=lambda item: item.alpha_2):
            names = {
                code: locale.territories.get(country.alpha_2) or str(getattr(country, "name", country.alpha_2))
                for code, locale in locales.items()
            }
            rows.append(
                (country.alpha_2, {"name": names}, {"alpha3_code": country.alpha_3, "numeric_code": country.numeric})
            )
        seed_rows(Country, "code", rows)
