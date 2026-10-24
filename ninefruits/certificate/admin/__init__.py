"""Certificate admin screens (original Filament ``Resources/Certificate`` and
``ManageCertificateSettings``)."""

from ninefruits.certificate import settings_pages  # noqa: F401  (registers the settings page)

from .issues import CertificateIssueAdmin
from .student_record import IssueCertificateActionMixin
from .types import CertificateTypeAdmin

__all__ = ["CertificateIssueAdmin", "CertificateTypeAdmin", "IssueCertificateActionMixin"]
