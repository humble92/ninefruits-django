"""Factories for countries, languages and code lists (original ``Database\\Factories\\Institution``)."""

from __future__ import annotations

import factory

from ninefruits.institution.models import Country, Language, LookupType, LookupValue


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country

    code = factory.Sequence(lambda n: f"{chr(65 + n // 26 % 26)}{chr(65 + n % 26)}")
    alpha3_code = factory.Sequence(lambda n: f"X{chr(65 + n // 26 % 26)}{chr(65 + n % 26)}")
    name = factory.LazyAttribute(lambda country: {"en": f"Country {country.code}"})


class LanguageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Language

    code = factory.Sequence(lambda n: f"q{chr(97 + n // 26 % 26)}{chr(97 + n % 26)}")
    name = factory.LazyAttribute(lambda language: {"en": f"Language {language.code}"})


class LookupTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LookupType

    code = factory.Sequence(lambda n: f"list_{n}")
    name = factory.LazyAttribute(lambda lookup_type: {"en": lookup_type.code.replace("_", " ").title()})


class LookupValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LookupValue

    lookup_type = factory.SubFactory(LookupTypeFactory)
    code = factory.Sequence(lambda n: f"value_{n}")
    name = factory.LazyAttribute(lambda value: {"en": value.code.replace("_", " ").title()})
