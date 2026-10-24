"""Original tests/Unit/Targeting/TargetCriteriaTest.php."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from ninefruits.core.targeting import TargetCriteria


@dataclass
class Subject:
    programs: list[int] = field(default_factory=lambda: [10])
    org_units: list[int] = field(default_factory=lambda: [3, 2, 1])
    admission_year: int | None = 2023
    year_level: int | None = 3
    status: str | None = "enrolled"
    standing: str | None = "good"
    tags: list[str] = field(default_factory=lambda: ["exchange"])

    def target_program_ids(self) -> list[int]:
        return self.programs

    def target_org_unit_ids(self) -> list[int]:
        return self.org_units

    def target_admission_year(self) -> int | None:
        return self.admission_year

    def target_year_level(self) -> int | None:
        return self.year_level

    def target_student_status(self) -> str | None:
        return self.status

    def target_academic_standing(self) -> str | None:
        return self.standing

    def target_tags(self) -> list[str]:
        return self.tags


def test_matches_everyone_when_empty() -> None:
    assert TargetCriteria.everyone().matches(Subject())
    assert TargetCriteria.everyone().is_everyone()


@pytest.mark.parametrize(
    ("criteria", "expected"),
    [
        pytest.param(TargetCriteria(year_levels=[3, 4]), True, id="year level in list"),
        pytest.param(TargetCriteria(year_levels=[4]), False, id="year level not in list"),
        pytest.param(TargetCriteria(org_unit_ids=[1]), True, id="college matches through ancestors"),
        pytest.param(TargetCriteria(org_unit_ids=[99]), False, id="other org unit"),
        pytest.param(
            TargetCriteria(admission_year_from=2020, admission_year_to=2023), True, id="admission year inside range"
        ),
        pytest.param(TargetCriteria(admission_year_from=2024), False, id="admission year before range"),
        pytest.param(TargetCriteria(program_ids=[10], year_levels=[3]), True, id="program and level both match"),
        pytest.param(TargetCriteria(program_ids=[10], year_levels=[1]), False, id="program matches, level does not"),
        pytest.param(TargetCriteria(student_statuses=["on_leave"]), False, id="status"),
        pytest.param(TargetCriteria(tags=["exchange", "veteran"]), True, id="tag"),
    ],
)
def test_requires_every_non_empty_criterion_to_match(criteria: TargetCriteria, expected: bool) -> None:
    assert criteria.matches(Subject()) is expected


def test_does_not_match_a_year_range_when_the_subject_has_no_admission_year() -> None:
    assert not TargetCriteria(admission_year_to=2030).matches(Subject(admission_year=None))


def test_round_trips_through_dicts_and_stores_only_non_empty_criteria() -> None:
    criteria = TargetCriteria.from_dict({"year_levels": ["1", "2"], "admission_year_from": "2020", "program_ids": []})

    assert criteria.year_levels == [1, 2]
    assert criteria.to_dict() == {"admission_year_from": 2020, "year_levels": [1, 2]}
    assert list(criteria.to_dict()) == ["admission_year_from", "year_levels"]


def test_rejects_an_inverted_admission_year_range() -> None:
    with pytest.raises(ValueError):
        TargetCriteria(admission_year_from=2025, admission_year_to=2020)
