"""Demo certificates (original ``DemoCertificateSeeder``): enrollment certificates for current
students (the demo student among them), graduation certificates for alumni (the demo alumnus
first), one transcript of a student with grades, and one revoked issue. They go through
``IssueCertificate`` as the demo certificate officer, so every issue has its PDF rendered by
Gotenberg and stored with its checksum.

Rendering needs the PDF service, so the count stays small: 4 enrollment and 2 graduation
certificates at ``--size=small`` (the original's counts), at most 8 and 4 at larger sizes (the
original scaled them, hundreds of PDFs at ``large``). Without a reachable PDF service the seeder
stops with a warning and issues nothing; the rest of the demo is unaffected."""

from __future__ import annotations

import logging
from typing import Any

from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder

from .options import current_options

logger = logging.getLogger(__name__)

PURPOSES = ["Scholarship application", "장학금 신청", "Visa extension", "취업 제출용", "奖学金申请"]
ENROLLMENT_LOCALES = ["ko", "en", "zh-hans"]
GRADUATION_LOCALES = ["en", "ko"]
MAX_ENROLLED = 8
MAX_GRADUATED = 4


def _account_record(email: str, status: str) -> Any:
    from ninefruits.person.models import StudentRecord

    return StudentRecord.objects.filter(person__user__email=email, status=status).order_by("-admission_date").first()


class DemoCertificateSeeder(Seeder):
    def run(self) -> None:
        from ninefruits.certificate.actions import IssueCertificate
        from ninefruits.certificate.models import CertificateIssue, CertificateType
        from ninefruits.grading.enums import GradeStatus
        from ninefruits.pdf import PdfRenderingError
        from ninefruits.person.enums import StudentStatus
        from ninefruits.person.models import StudentRecord
        from ninefruits.registration.models import Enrollment
        from ninefruits.security.models import User

        options = current_options()
        domain = conf.DEMO_EMAIL_DOMAIN
        officer = User.objects.filter(email=f"certificate-officer@{domain}").first()
        types = {kind.code: kind for kind in CertificateType.objects.filter(is_active=True)}
        if officer is None or not types or CertificateIssue.objects.exists():
            return

        enrolled = self._pick(
            StudentRecord.objects.filter(status=StudentStatus.ENROLLED),
            min(options.scale(4), MAX_ENROLLED),
            _account_record(f"student@{domain}", StudentStatus.ENROLLED),
        )
        graduated = self._pick(
            StudentRecord.objects.filter(status=StudentStatus.GRADUATED),
            min(options.scale(2), MAX_GRADUATED),
            _account_record(f"alumni@{domain}", StudentStatus.GRADUATED),
        )
        with_grades = (
            StudentRecord.objects.filter(
                status=StudentStatus.ENROLLED,
                pk__in=Enrollment.objects.filter(grade_status=GradeStatus.FINALIZED).values("student_record_id"),
            )
            .order_by("pk")
            .first()
        )

        action = IssueCertificate()
        plan: list[tuple[Any, str, str, str | None, int]] = []
        if "ENR" in types:
            for index, record in enumerate(enrolled):
                plan.append(
                    (
                        record,
                        "ENR",
                        ENROLLMENT_LOCALES[index % len(ENROLLMENT_LOCALES)],
                        PURPOSES[index % len(PURPOSES)],
                        1 + index % 2,
                    )
                )
        if "GRD" in types:
            for index, record in enumerate(graduated):
                plan.append((record, "GRD", GRADUATION_LOCALES[index % len(GRADUATION_LOCALES)], "Employment", 1))
        transcript_for = with_grades or (graduated[0] if graduated else (enrolled[0] if enrolled else None))
        if "TRN" in types and transcript_for is not None:
            plan.append((transcript_for, "TRN", "en", "Graduate school application", 1))

        issued = []
        for record, code, locale, purpose, copies in plan:
            try:
                issued.append(action.handle(record, types[code], locale, officer, purpose, copies))
            except PdfRenderingError as error:
                logger.warning("Demo certificates skipped: the PDF service is not available (%s).", error)
                return
        if len(issued) > 2:
            action.revoke(issued[1], officer, "Issued with a wrong purpose; re-issued.")

    @staticmethod
    def _pick(queryset: Any, count: int, first: Any) -> list[Any]:
        """``count`` records chosen with the demo generator (``--seed``), ``first`` leading."""
        ids = list(queryset.order_by("pk").values_list("pk", flat=True))
        if first is not None and first.pk in ids:
            ids.remove(first.pk)
        rng = current_options().rng
        chosen = rng.sample(ids, min(len(ids), max(0, count - (1 if first is not None else 0))))
        from ninefruits.person.models import StudentRecord

        records = {record.pk: record for record in StudentRecord.objects.filter(pk__in=chosen)}
        picked = [records[pk] for pk in chosen]
        return ([first] if first is not None else []) + picked
