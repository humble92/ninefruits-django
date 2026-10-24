from __future__ import annotations

from ninefruits.security.role_templates import sync_role_templates
from ninefruits.setup.seeders.base import Seeder


class RoleTemplateSeeder(Seeder):
    """Default roles based on the legacy Oracle roles (porting-plan 7.2). Safe to run
    repeatedly: existing roles keep the display names and permissions administrators gave them.
    System roles always get every permission."""

    def run(self) -> None:
        sync_role_templates()
