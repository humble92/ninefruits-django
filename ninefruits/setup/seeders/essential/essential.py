from __future__ import annotations

from ninefruits.setup.seeders.base import Seeder


class EssentialSeeder(Seeder):
    """Data the system needs to work. Runs in every environment, on every deployment, and must
    be idempotent: rows are found by code or name, and values administrators changed are kept
    (porting-plan 13.4). Later phases append their essential seeders to ``SEEDERS`` in
    dependency order (Phase 2: student status change types)."""

    SEEDERS: list[str] = [
        "ninefruits.setup.seeders.essential.role_template.RoleTemplateSeeder",
        "ninefruits.setup.seeders.essential.country.CountrySeeder",
        "ninefruits.setup.seeders.essential.language.LanguageSeeder",
        "ninefruits.setup.seeders.essential.lookup_type.LookupTypeSeeder",
        "ninefruits.setup.seeders.essential.org_unit_type.OrgUnitTypeSeeder",
        "ninefruits.setup.seeders.essential.status_change_type.StatusChangeTypeSeeder",
    ]

    def run(self) -> None:
        from django.utils.module_loading import import_string

        self.call(*(import_string(path) for path in self.SEEDERS))
