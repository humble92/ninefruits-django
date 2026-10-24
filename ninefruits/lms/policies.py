"""LMS policies (original ``LmsPolicy``): platforms, links and logs need ``lms.manage`` for
everything. Course links are also read by anyone signed in (the portal link) and user links by
their user, but only through ``visible_to``; the admin screens follow this policy. Registered
from ``LmsConfig.ready``."""

from __future__ import annotations

from typing import Any

from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class LmsPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.LMS_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def create(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def update(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def delete(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def resync(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)


class LmsSyncLogPolicy(LmsPolicy):
    """The log is a record: never created, changed or deleted on screen."""

    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


def register_policies() -> None:
    policy = LmsPolicy()
    register("lms.lmsplatform", policy)
    register("lms.lmscourselink", policy)
    register("lms.lmsuserlink", policy)
    register("lms.lmssynclog", LmsSyncLogPolicy())
