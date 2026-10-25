"""Finds the account for what was typed in the sign-in field: the personal email, or a
student number when the institution allows it (original ``LoginIdentifierResolver``,
porting-plan 7.1). Student numbers are looked up with ``util.user_id_for_student_number``
(SECURITY DEFINER, so row level security does not hide records from the anonymous sign-in)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import connection

from ninefruits.security.enums import StudentNumberLogin

if TYPE_CHECKING:
    from ninefruits.security.models import User
    from ninefruits.settings.groups.authentication import AuthenticationSettings


class LoginIdentifierResolver:
    def __init__(self, settings: AuthenticationSettings | None = None) -> None:
        if settings is None:
            from ninefruits.settings.groups.authentication import AuthenticationSettings

            settings = AuthenticationSettings.load()
        self.settings = settings

    def resolve(self, identifier: str | None) -> User | None:
        from ninefruits.security.models import User

        identifier = (identifier or "").strip()
        if not identifier:
            return None
        if "@" in identifier:
            return User.objects.filter(email=identifier.lower()).first()
        if self.settings.student_number_login == StudentNumberLogin.DISABLED:
            return None
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT util.user_id_for_student_number(%s, %s)",
                [identifier, self.settings.student_number_login == StudentNumberLogin.ALL_RECORDS],
            )
            row = cursor.fetchone()
        user_id = row[0] if row else None
        return None if user_id is None else User.objects.filter(pk=user_id).first()

    def allows_student_numbers(self) -> bool:
        return self.settings.student_number_login != StudentNumberLogin.DISABLED
