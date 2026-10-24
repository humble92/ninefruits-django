"""Factories for certificates (the original had none: kinds came from the profile seeder and
issues from ``IssueCertificate``). ``CertificateIssueFactory`` writes a ledger row without a PDF,
for access and listing tests; issuing with a PDF goes through the action."""

from __future__ import annotations

import factory
from django.utils import timezone

from ninefruits.certificate.actions import verification_code
from ninefruits.certificate.enums import CertificateAudience, CertificateIssueStatus
from ninefruits.certificate.models import CertificateIssue, CertificateTemplate, CertificateType
from tests.factories.person import StudentRecordFactory


class CertificateTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CertificateType
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"T{n:03d}")
    name = factory.LazyAttribute(lambda kind: {"en": f"Certificate {kind.code}", "ko": f"증명서 {kind.code}"})
    audience = CertificateAudience.ANY
    sort_order = factory.Sequence(lambda n: n * 10)


class CertificateTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CertificateTemplate

    certificate_type = factory.SubFactory(CertificateTypeFactory)
    locale = "en"
    title = "Certificate"
    body = "This is to certify that {student_name} ({student_number}) studies at {institution}."


class CertificateIssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CertificateIssue

    class Params:
        revoked = factory.Trait(
            status=CertificateIssueStatus.REVOKED,
            revoked_at=factory.LazyFunction(lambda: timezone.now().replace(microsecond=0)),
            revocation_reason="Test",
        )

    student_record = factory.SubFactory(StudentRecordFactory)
    certificate_type = factory.SubFactory(CertificateTypeFactory)
    locale = "en"
    serial_number = factory.Sequence(lambda n: f"TST-{n:06d}")
    verification_code = factory.LazyFunction(verification_code)
    issued_at = factory.LazyFunction(lambda: timezone.now().replace(microsecond=0))
