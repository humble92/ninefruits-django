"""Certificate policies (original ``App\\Policies\\Certificate\\*``). Registered from
``CertificateConfig.ready``.

- Kinds and templates are configuration (``CertificateSetupPolicy``: reference data, managed with
  ``certificates.manage``).
- The ledger is written only through ``IssueCertificate``; rows are never edited or deleted
  (revoked instead). Staff who issue or manage certificates list it; the holder sees their own."""

from __future__ import annotations

from typing import Any

from ninefruits.institution.policies import ReferenceDataPolicy
from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class CertificateIssuePolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.CERTIFICATES_ISSUE) or user.has_perm(Permission.CERTIFICATES_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        """Staff, or the holder (checked by query: under RLS the record is hidden from anyone else)."""
        if self.view_any(user, obj):
            return True
        if obj is None or getattr(user, "person_id", None) is None:
            return False
        from ninefruits.person.models import StudentRecord

        return StudentRecord.objects.filter(pk=obj.student_record_id, person_id=user.person_id).exists()

    def download(self, user: Any, obj: Any) -> bool:
        """The stored PDF: whoever may view it; a revoked certificate only for staff who issue
        (they keep the file for the record), never for the holder."""
        if obj is None or not self.view(user, obj):
            return False
        return not obj.is_revoked or bool(user.has_perm(Permission.CERTIFICATES_ISSUE))  # any scope: reading only

    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


def register_policies() -> None:
    setup = ReferenceDataPolicy(Permission.CERTIFICATES_MANAGE)
    register("certificate.certificatetype", setup)
    register("certificate.certificatetemplate", setup)
    register("certificate.certificateissue", CertificateIssuePolicy())
