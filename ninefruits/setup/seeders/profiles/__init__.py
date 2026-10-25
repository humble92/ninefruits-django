"""Profile seeders (original ``database/seeders/Profiles``): optional bundles of rules applied
at installation with ``setup_install --profile=<key>``. Idempotent like essential seeders."""

from __future__ import annotations

from django.utils.module_loading import import_string

from ninefruits.setup.seeders.base import Seeder


class SetupProfile(Seeder):
    """A profile has a key (``--profile``), a label and a description."""

    key: str = ""
    label: str = ""
    description: str = ""


def available_profiles() -> list[type[SetupProfile]]:
    from ninefruits.setup.conf import PROFILES

    return [import_string(path) for path in PROFILES]
