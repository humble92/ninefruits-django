"""List people who may be duplicates (original ``people:find-duplicates``): the same national ID
(search hash), or the same romanized name and birth date. Merged people are left out. Merging
is done on the person screen (merge action), after checking. Read only, so not audited."""

from __future__ import annotations

import io
from typing import Any

from django.core.management.base import CommandParser
from django.db import connection
from rich.console import Console
from rich.table import Table

from ninefruits.core.commands import StatusCommand
from ninefruits.core.db import session_context

_DUPLICATES_SQL = """
    SELECT 'national_id' AS reason, array_agg(id ORDER BY id) AS ids
    FROM people
    WHERE merged_into_person_id IS NULL AND national_id_hash IS NOT NULL
    GROUP BY national_id_hash
    HAVING count(*) > 1
    UNION ALL
    SELECT 'name_birth_date', array_agg(id ORDER BY id)
    FROM people
    WHERE merged_into_person_id IS NULL AND birth_date IS NOT NULL
    GROUP BY lower(family_name), lower(coalesce(given_name, '')), birth_date
    HAVING count(*) > 1
    ORDER BY 1, 2
    LIMIT %s
"""


class Command(StatusCommand):
    help = "List people who may be duplicates (same national id, or same name and birth date)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit", type=int, default=100, help="Maximum groups to list")

    def handle(self, *args: Any, **options: Any) -> int:
        limit = max(1, int(options["limit"]))
        # Every person, whatever the operator's account could see (row level security).
        with session_context().system("people_find_duplicates"):
            with connection.cursor() as cursor:
                cursor.execute(_DUPLICATES_SQL, [limit])
                groups = cursor.fetchall()

        if not groups:
            self.info("No likely duplicates.")
            return self.SUCCESS

        table = Table("Reason", "Person IDs")
        for reason, ids in groups:
            table.add_row(str(reason), ",".join(str(pk) for pk in ids))
        buffer = io.StringIO()
        Console(file=buffer, width=160, force_terminal=False, color_system=None).print(table)
        self.stdout.write(buffer.getvalue())
        self.warn(f"{len(groups)} group(s). Check each on the person screen and merge with the merge action.")
        return self.PROBLEMS_FOUND
