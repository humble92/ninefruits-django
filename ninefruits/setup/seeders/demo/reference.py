from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from django.utils import timezone

from ninefruits.core.targeting import TargetCriteria
from ninefruits.facility.models import Building, Room
from ninefruits.institution.models import LookupValue
from ninefruits.organization.enums import DegreeLevel, OrgUnitChangeType
from ninefruits.organization.models import OrgUnit, OrgUnitSuccession, OrgUnitType, Program
from ninefruits.setup.seeders.base import Seeder
from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import AcademicYear, Term, TermType, TermWindow

from .options import current_options

Names = dict[str, str]


class DemoReferenceSeeder(Seeder):
    """Org units, programs, buildings, rooms, academic years and terms around today: the last
    term has closed grades, the current one is in session, the next one has registration
    opening by year level (porting-plan 13.4). Runs once per database."""

    def run(self) -> None:
        if OrgUnit.objects.filter(code="DEMO").exists():
            return
        self.call(KoreanUniversityProfileSeeder)
        self.organization()
        self.facilities()
        self.terms()

    # -- organization -----------------------------------------------------------------------------
    def organization(self) -> None:
        types = dict(OrgUnitType.objects.values_list("code", "id"))

        def unit(
            code: str,
            name: Names,
            type_code: str,
            parent: OrgUnit | None = None,
            start: str = "1990-03-01",
            end: str | None = None,
        ) -> OrgUnit:
            return OrgUnit.objects.create(
                code=code,
                name=name,
                org_unit_type_id=types[type_code],
                parent=parent,
                effective_start_date=date.fromisoformat(start),
                effective_end_date=date.fromisoformat(end) if end else None,
            )

        university = unit("DEMO", {"en": "Demo University", "ko": "데모대학교", "zh-hans": "演示大学"}, "university")
        structure: dict[str, tuple[Names, dict[str, Names]]] = {
            "ENG": (
                {"en": "College of Engineering", "ko": "공과대학", "zh-hans": "工学院"},
                {
                    "CSE": {"en": "Computer Science and Engineering", "ko": "컴퓨터공학과", "zh-hans": "计算机工程系"},
                    "EE": {"en": "Electrical Engineering", "ko": "전기공학과", "zh-hans": "电气工程系"},
                },
            ),
            "HUM": (
                {"en": "College of Humanities", "ko": "인문대학", "zh-hans": "人文学院"},
                {
                    "KOR": {"en": "Korean Language and Literature", "ko": "국어국문학과", "zh-hans": "韩国语言文学系"},
                    "CHN": {"en": "Chinese Language and Literature", "ko": "중어중문학과", "zh-hans": "汉语言文学系"},
                },
            ),
            "NUR": (
                {"en": "College of Nursing", "ko": "간호대학", "zh-hans": "护理学院"},
                {"NURS": {"en": "Nursing", "ko": "간호학과", "zh-hans": "护理学系"}},
            ),
        }
        programs = []
        for college_code, (college_name, departments) in structure.items():
            college = unit(college_code, college_name, "college", university)
            for code, name in departments.items():
                department = unit(code, name, "department", college)
                programs.append(
                    Program(
                        code=f"B-{code}",
                        name={
                            "en": f"Bachelor of {name['en']}",
                            "ko": f"{name['ko']} 학사과정",
                            "zh-hans": f"{name['zh-hans']}本科",
                        },
                        degree_level=DegreeLevel.BACHELOR,
                        org_unit=department,
                        standard_duration_years=4,
                        effective_start_date=date(1990, 3, 1),
                    )
                )
        Program.objects.bulk_create(programs)

        # History example: an older department merged into Computer Science and Engineering.
        old = unit(
            "CS-OLD",
            {
                "en": "Computer Science (until 2015)",
                "ko": "전산학과 (2015년까지)",
                "zh-hans": "计算机科学系 (至2015年)",
            },
            "department",
            OrgUnit.objects.get(code="ENG"),
            "1990-03-01",
            "2015-02-28",
        )
        OrgUnitSuccession.objects.create(
            predecessor=old,
            successor=OrgUnit.objects.get(code="CSE"),
            change_type=OrgUnitChangeType.MERGED,
            effective_date=date(2015, 3, 1),
            reason="Demo: department merger",
        )

    # -- facilities ---------------------------------------------------------------------------------
    def facilities(self) -> None:
        options = current_options()
        room_types = dict(LookupValue.objects.of_type(Room.ROOM_TYPE_LOOKUP).values_list("code", "id"))
        buildings = {
            "SCI": {"en": "Science Hall", "ko": "과학관", "zh-hans": "科学楼"},
            "HUM": {"en": "Humanities Hall", "ko": "인문관", "zh-hans": "人文楼"},
            "NUR": {"en": "Nursing Hall", "ko": "간호관", "zh-hans": "护理楼"},
        }
        rooms = []
        for code, name in buildings.items():
            building = Building.objects.create(code=code, name=name)
            for index in range(1, options.scale(8) + 1):
                floor = (index - 1) // 8 + 1
                room_type = "laboratory" if index % 5 == 0 else "lecture"
                rooms.append(
                    Room(
                        building=building,
                        code=f"{floor}{(index - 1) % 8 + 1:02d}",
                        room_type_id=room_types.get(room_type),
                        capacity=30 if room_type == "laboratory" else (40, 60, 80)[index % 3],
                    )
                )
        Room.objects.bulk_create(rooms, batch_size=1000)

    # -- terms --------------------------------------------------------------------------------------
    def terms(self) -> None:
        today = timezone.localdate()
        types = dict(TermType.objects.values_list("code", "id"))

        # Regular terms around today: spring Mar 2 - Jun 20, fall Sep 1 - Dec 20.
        candidates: list[tuple[str, date, date]] = []
        for year in range(today.year - 1, today.year + 2):
            candidates.append(("spring", date(year, 3, 2), date(year, 6, 20)))
            candidates.append(("fall", date(year, 9, 1), date(year, 12, 20)))
        current_index = max(index for index, candidate in enumerate(candidates) if candidate[1] <= today)
        chosen = {
            "past": candidates[current_index - 1],
            "current": candidates[current_index],
            "next": candidates[current_index + 1],
        }

        terms: dict[str, Term] = {}
        for role, (type_code, start, end) in chosen.items():
            year = start.year if start.month >= 3 else start.year - 1
            academic_year, _created = AcademicYear.objects.get_or_create(
                code=str(year),
                defaults={
                    "name": {"en": f"{year} academic year", "ko": f"{year}학년도", "zh-hans": f"{year}学年"},
                    "start_date": date(year, 3, 1),
                    "end_date": date(year + 1, 3, 1) - timedelta(days=1),
                },
            )
            label = (
                {"en": "Spring", "ko": "1학기", "zh-hans": "春季学期"}
                if type_code == "spring"
                else {"en": "Fall", "ko": "2학기", "zh-hans": "秋季学期"}
            )
            term = Term.objects.create(
                academic_year=academic_year,
                term_type_id=types[type_code],
                code=f"{year}-{'SP' if type_code == 'spring' else 'FA'}",
                name={
                    "en": f"{label['en']} {year}",
                    "ko": f"{year}학년도 {label['ko']}",
                    "zh-hans": f"{year}学年{label['zh-hans']}",
                },
                start_date=start,
                end_date=end,
            )
            term.status = TermStatus.GRADES_CLOSED if role == "past" else TermStatus.PUBLISHED
            term.save(update_fields=["status", "updated_at"])
            terms[role] = term

        now = timezone.now().replace(minute=0, second=0, microsecond=0)

        def at(day: date, hour: int) -> datetime:
            return datetime.combine(day, time(hour), tzinfo=timezone.get_default_timezone())

        def window(
            term: Term,
            window_type: TermWindowType,
            opens: datetime,
            closes: datetime,
            criteria: TargetCriteria | None = None,
            name: Names | None = None,
        ) -> Any:
            return TermWindow.objects.create(
                term=term,
                window_type=window_type,
                name=name,
                opens_at=opens,
                closes_at=closes,
                eligibility=criteria or TargetCriteria.everyone(),
            )

        past = terms["past"]
        window(
            past,
            TermWindowType.GRADE_ENTRY,
            at(past.end_date - timedelta(days=7), 9),
            at(past.end_date + timedelta(days=7), 18),
        )

        current = terms["current"]
        window(
            current,
            TermWindowType.ADD_DROP,
            at(current.start_date, 9),
            at(current.start_date + timedelta(days=7), 18),
        )
        window(
            current,
            TermWindowType.COURSE_EVALUATION,
            at(current.end_date - timedelta(days=21), 9),
            at(current.end_date, 18),
        )
        window(
            current,
            TermWindowType.GRADE_ENTRY,
            at(current.end_date - timedelta(days=7), 9),
            at(current.end_date + timedelta(days=7), 18),
        )

        upcoming = terms["next"]
        window(upcoming, TermWindowType.REGISTRATION_CART, now - timedelta(days=3), now + timedelta(days=7))
        window(
            upcoming,
            TermWindowType.REGISTRATION,
            now - timedelta(days=1),
            now + timedelta(days=5),
            TargetCriteria(year_levels=[4]),
            {"en": "Fourth year", "ko": "4학년", "zh-hans": "四年级"},
        )
        window(
            upcoming,
            TermWindowType.REGISTRATION,
            now + timedelta(days=1),
            now + timedelta(days=5),
            TargetCriteria(year_levels=[3]),
            {"en": "Third year", "ko": "3학년", "zh-hans": "三年级"},
        )
        window(
            upcoming,
            TermWindowType.REGISTRATION,
            now + timedelta(days=2),
            now + timedelta(days=5),
            TargetCriteria(year_levels=[1, 2]),
            {"en": "First and second year", "ko": "1, 2학년", "zh-hans": "一、二年级"},
        )
