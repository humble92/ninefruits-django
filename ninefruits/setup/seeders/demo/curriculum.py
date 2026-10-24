"""Demo curriculum and sections (original ``Database\\Seeders\\Demo\\DemoCurriculumSeeder``).

Courses (with a revised course and an equivalency), requisites, graduation requirements per
program and role, first and second half sessions in the current term, sections with instructors,
rooms and syllabi, and the next term copied from the current one with ``CopySections``. Rows are
written with bulk inserts; the choices depend only on the data order, so every run gives the same
result. The second major and minor applications of the original seeder belong to the people
seeder (Phase 2 work)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.utils import timezone

from ninefruits.core.targeting import TargetCriteria
from ninefruits.curriculum.enums import ProgramRole, RequirementKind, RequisiteKind
from ninefruits.curriculum.models import (
    Course,
    CourseCategory,
    CourseEquivalency,
    CourseRequisite,
    CourseVersion,
    CurriculumRequirement,
    CurriculumRequirementCourse,
    CurriculumRequirementSet,
)
from ninefruits.facility.models import Room
from ninefruits.offering.enums import InstructorRole, SectionStatus
from ninefruits.offering.models import Section, SectionInstructor, SectionMeeting, SectionSeatGroup, Syllabus
from ninefruits.organization.models import OrgUnit, Program
from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder
from ninefruits.term.enums import TermStatus
from ninefruits.term.models import Term, TermSession

Names = dict[str, str]

#: Course titles per level: (en, ko, zh-hans) with {name} for the department.
TOPICS: dict[int, list[tuple[str, str, str]]] = {
    1: [
        ("Introduction to {name}", "{name} 개론", "{name}导论"),
        ("Foundations of {name}", "{name} 기초", "{name}基础"),
    ],
    2: [("Methods in {name}", "{name} 방법론", "{name}方法论"), ("{name} Laboratory", "{name} 실습", "{name}实验")],
    3: [("Topics in {name}", "{name} 특강", "{name}专题"), ("Seminar in {name}", "{name} 세미나", "{name}研讨")],
    4: [
        ("Advanced {name}", "고급 {name}", "高级{name}"),
        ("Capstone Project in {name}", "{name} 캡스톤 프로젝트", "{name}综合设计"),
    ],
}

GENERAL: list[tuple[str, str, Names]] = [
    ("GEN1001", "GE_REQ", {"en": "Academic Writing", "ko": "대학 글쓰기", "zh-hans": "学术写作"}),
    ("GEN1002", "GE_REQ", {"en": "English Communication", "ko": "영어 의사소통", "zh-hans": "英语交流"}),
    ("GEN1003", "GE_REQ", {"en": "Computing for Everyone", "ko": "모두를 위한 컴퓨팅", "zh-hans": "大众计算"}),
    ("GEN2001", "GE_ELEC", {"en": "Introduction to Statistics", "ko": "통계학 입문", "zh-hans": "统计学入门"}),
    ("GEN2002", "GE_ELEC", {"en": "History of Science", "ko": "과학사", "zh-hans": "科学史"}),
    ("GEN2003", "GE_ELEC", {"en": "Philosophy and Ethics", "ko": "철학과 윤리", "zh-hans": "哲学与伦理"}),
]

#: Meeting patterns (weekdays) and start times; 75 minutes each.
PATTERNS: list[list[int]] = [[1, 3], [2, 4], [1, 3], [2, 4], [5]]
STARTS: list[str] = ["09:00", "10:30", "13:00", "14:30", "16:00"]

ROLE_NAMES: dict[str, Names] = {
    ProgramRole.PRIMARY: {"en": "Primary program", "ko": "주전공"},
    ProgramRole.SECOND_MAJOR: {"en": "Second major", "ko": "복수전공"},
    ProgramRole.MINOR: {"en": "Minor", "ko": "부전공"},
}


def _clock(text: str) -> time:
    hours, minutes = (int(part) for part in text.split(":"))
    return time(hours, minutes)


class _Course:
    """A course being seeded with its versions (in memory, before the bulk insert)."""

    def __init__(self, course: Course, versions: list[CourseVersion]) -> None:
        self.course = course
        self.versions = versions

    def version_on(self, on: date) -> CourseVersion | None:
        for version in self.versions:
            if version.effective_start_date <= on and (
                version.effective_end_date is None or version.effective_end_date >= on
            ):
                return version
        return None


class DemoCurriculumSeeder(Seeder):
    def run(self) -> None:
        if Course.objects.filter(code="GEN1001").exists():
            return
        today = timezone.localdate()
        current = (
            Term.objects.filter(status=TermStatus.PUBLISHED, start_date__lte=today).order_by("-start_date").first()
        )
        upcoming = Term.objects.filter(status=TermStatus.PUBLISHED, start_date__gt=today).order_by("start_date").first()
        if current is None or upcoming is None:
            return

        self.taken: set[str] = set()
        categories = dict(CourseCategory.objects.values_list("code", "id"))
        courses = self.courses(categories, today)
        self.requirements(courses, categories)
        self.sessions(current)
        self.sections(current, courses)

        # The next term starts as a copy of the current one, as staff would do it.
        from ninefruits.offering.actions import CopySections
        from ninefruits.security.models import User

        planner = User.objects.filter(email=f"academic-affairs@{conf.DEMO_EMAIL_DOMAIN}").first()
        if planner is not None:
            CopySections()(current, upcoming, planner)
            Section.objects.filter(term=upcoming).update(status=SectionStatus.PUBLISHED)

    # -- courses ----------------------------------------------------------------------------------
    def courses(self, categories: dict[str, int], today: date) -> dict[str, list[_Course]]:
        """Courses by unit code ('GEN' for general education)."""
        university = OrgUnit.objects.get(code="DEMO")
        planned: list[tuple[str, OrgUnit, Names, int, int | None, date, date | None, bool]] = []
        for code, category, title in GENERAL:
            planned.append((code, university, title, 3, categories.get(category), date(2000, 3, 1), None, True))

        programs = list(Program.objects.effective_on(today).select_related("org_unit").order_by("code"))
        for program in programs:
            unit = program.org_unit
            names = unit.name_translations
            for level, topics in TOPICS.items():
                for index, (en, ko, zh) in enumerate(topics):
                    title = {
                        "en": en.replace("{name}", names.get("en") or unit.code),
                        "ko": ko.replace("{name}", names.get("ko") or unit.code),
                        "zh-hans": zh.replace("{name}", names.get("zh-hans") or unit.code),
                    }
                    category = "MAJ_FND" if level == 1 else ("MAJ_REQ" if level <= 2 else "MAJ_ELEC")
                    credits = 2 if index == 1 and level == 2 else 3
                    planned.append(
                        (
                            f"{unit.code}{level}{index + 1:03d}",
                            unit,
                            title,
                            credits,
                            categories.get(category),
                            date(2000, 3, 1),
                            None,
                            True,
                        )
                    )
            # Second majors and minors in every other program.
            Program.objects.filter(pk=program.pk).update(allows_second_major=program.pk % 2 == 0, allows_minor=True)

        # A revision: the first department course went from 3 to 4 credits two years ago, and an
        # older course it replaced counts as equivalent.
        first_department = next((row for row in planned if not row[0].startswith("GEN")), None)
        revised_from = date(today.year - 2, 3, 1)
        if first_department is not None:
            code, unit, title, _credits, category, *_rest = first_department
            planned.append(
                (
                    f"{code}X",
                    unit,
                    {"en": f"Old {title['en']}", "ko": f"(구) {title['ko']}"},
                    3,
                    category,
                    date(2010, 3, 1),
                    date(2019, 2, 28),
                    False,
                )
            )

        created = Course.objects.bulk_create(
            [Course(code=row[0], org_unit=row[1], is_active=row[7]) for row in planned], batch_size=500
        )
        versions: list[CourseVersion] = []
        by_code: dict[str, _Course] = {}
        for course, (code, _unit, title, credits, category, start, end, _active) in zip(created, planned, strict=True):
            course_versions = []
            if first_department is not None and code == first_department[0]:
                course_versions.append(
                    CourseVersion(
                        course=course,
                        effective_start_date=start,
                        effective_end_date=revised_from - timedelta(days=1),
                        title=title,
                        credits=Decimal(credits),
                        lecture_hours=Decimal(credits),
                        category_id=category,
                    )
                )
                course_versions.append(
                    CourseVersion(
                        course=course,
                        effective_start_date=revised_from,
                        title=title,
                        credits=Decimal(4),
                        lecture_hours=Decimal(credits),
                        category_id=category,
                    )
                )
            else:
                course_versions.append(
                    CourseVersion(
                        course=course,
                        effective_start_date=start,
                        effective_end_date=end,
                        title=title,
                        credits=Decimal(credits),
                        lecture_hours=Decimal(credits),
                        category_id=category,
                    )
                )
            versions.extend(course_versions)
            by_code[code] = _Course(course, course_versions)
        CourseVersion.objects.bulk_create(versions, batch_size=500)

        if first_department is not None:
            CourseEquivalency.objects.create(
                course=by_code[first_department[0]].course,
                equivalent_course=by_code[f"{first_department[0]}X"].course,
                effective_start_date=date(2019, 3, 1),
            )

        by_unit: dict[str, list[_Course]] = defaultdict(list)
        for code, unit, *_rest in planned:
            if code.endswith("X"):
                continue
            by_unit["GEN" if code.startswith("GEN") else unit.code].append(by_code[code])

        # Level 2 needs the first level 1 course; level 3 needs one of the level 2 courses.
        requisites = []
        for unit_code, unit_courses in by_unit.items():
            if unit_code == "GEN":
                continue
            for item in unit_courses:
                level = int(item.course.code[-4])
                required = {2: [unit_courses[0]], 3: [unit_courses[2], unit_courses[3]]}.get(level, [])
                for required_course in required:
                    for version in item.versions:
                        requisites.append(
                            CourseRequisite(
                                course_version=version,
                                kind=RequisiteKind.PREREQUISITE,
                                required_course=required_course.course,
                            )
                        )
        CourseRequisite.objects.bulk_create(requisites, batch_size=500)
        return dict(by_unit)

    # -- requirements -----------------------------------------------------------------------------
    def requirements(self, courses: dict[str, list[_Course]], categories: dict[str, int]) -> None:
        links: list[CurriculumRequirementCourse] = []
        for program in Program.objects.effective_on(timezone.localdate()).select_related("org_unit").order_by("code"):
            unit_courses = [item.course for item in courses.get(program.org_unit.code, [])]
            roles = [ProgramRole.PRIMARY]
            if program.allows_second_major:
                roles.append(ProgramRole.SECOND_MAJOR)
            if program.allows_minor:
                roles.append(ProgramRole.MINOR)
            for role in roles:
                names = ROLE_NAMES[role]
                requirement_set = CurriculumRequirementSet.objects.create(
                    program=program,
                    program_role=role,
                    catalog_year_from=2015,
                    name={"en": f"{names['en']} requirements from 2015", "ko": f"2015 이후 {names['ko']} 요건"},
                    total_credits=Decimal({ProgramRole.PRIMARY: 130, ProgramRole.SECOND_MAJOR: 36}.get(role, 21)),
                )

                def line(
                    kind: str,
                    attributes: dict[str, Any],
                    course_list: list[Course] | None = None,
                    requirement_set: CurriculumRequirementSet = requirement_set,
                ) -> None:
                    requirement = CurriculumRequirement.objects.create(
                        requirement_set=requirement_set, kind=kind, **attributes
                    )
                    links.extend(
                        CurriculumRequirementCourse(requirement=requirement, course=course)
                        for course in course_list or []
                    )

                if role == ProgramRole.PRIMARY:
                    line(
                        RequirementKind.CATEGORY_CREDITS,
                        {"category_id": categories.get("GE_REQ"), "min_credits": Decimal(9), "sort_order": 1},
                    )
                    line(
                        RequirementKind.CATEGORY_CREDITS,
                        {"category_id": categories.get("GE_ELEC"), "min_credits": Decimal(15), "sort_order": 2},
                    )
                if role != ProgramRole.MINOR:
                    line(RequirementKind.REQUIRED_COURSES, {"sort_order": 3}, unit_courses[:4])
                line(
                    RequirementKind.COURSE_GROUP,
                    {"min_credits": Decimal(21 if role == ProgramRole.MINOR else 12), "sort_order": 4},
                    unit_courses[0 if role == ProgramRole.MINOR else 4 :],
                )
        CurriculumRequirementCourse.objects.bulk_create(links, batch_size=500)

    # -- sessions ---------------------------------------------------------------------------------
    def sessions(self, term: Term) -> None:
        from ninefruits.security.models import User
        from ninefruits.term.actions import CopySessionWindows

        full = term.full_term_session()
        middle = term.start_date + timedelta(days=(term.end_date - term.start_date).days // 2)
        first = TermSession.objects.create(
            term=term,
            code="A",
            name={"en": "First half", "ko": "전반기", "zh-hans": "前半学期"},
            start_date=term.start_date,
            end_date=middle,
            sort_order=1,
        )
        second = TermSession.objects.create(
            term=term,
            code="B",
            name={"en": "Second half", "ko": "후반기", "zh-hans": "后半学期"},
            start_date=middle + timedelta(days=1),
            end_date=term.end_date,
            sort_order=2,
        )
        planner = User.objects.filter(email=f"academic-affairs@{conf.DEMO_EMAIL_DOMAIN}").first()
        if planner is not None and full.windows.exists():
            CopySessionWindows()(full, first, planner)
            CopySessionWindows()(full, second, planner)

    # -- sections ---------------------------------------------------------------------------------
    def sections(self, term: Term, courses: dict[str, list[_Course]]) -> None:
        sessions = {session.code: session for session in TermSession.objects.filter(term=term)}
        rooms = list(Room.objects.filter(is_active=True, is_schedulable=True).order_by("capacity", "id"))
        instructors_by_unit, all_instructors, demo_person_id = self._instructors()

        planned: list[tuple[Section, TermSession, Any, int, CourseVersion]] = []
        index = 0
        for unit_code, unit_courses in courses.items():
            for item in unit_courses:
                if not item.course.is_active:
                    continue
                for copy in range(1, (2 if unit_code == "GEN" else 1) + 1):
                    index += 1
                    # Every seventh department section runs in one half of the term.
                    if unit_code != "GEN" and index % 7 == 0:
                        session = sessions["A" if index % 2 == 0 else "B"]
                    else:
                        session = sessions["FULL"]
                    version = item.version_on(session.start_date)
                    if version is None:
                        continue
                    section = Section(
                        term=term,
                        session=session,
                        course=item.course,
                        version=version,
                        section_code=f"{copy:02d}",
                        org_unit_id=item.course.org_unit_id,
                        capacity=60 if unit_code == "GEN" else 40,
                        status=SectionStatus.PUBLISHED,
                    )
                    if unit_code == "GEN":
                        instructor = all_instructors[index % len(all_instructors)] if all_instructors else None
                    else:
                        unit_list = instructors_by_unit.get(item.course.org_unit_id, [])
                        instructor = unit_list[index % len(unit_list)] if unit_list else None
                    planned.append((section, session, instructor, index, version))

        Section.objects.bulk_create([row[0] for row in planned], batch_size=500)

        assignments: list[SectionInstructor] = []
        meetings: list[SectionMeeting] = []
        seat_groups: list[SectionSeatGroup] = []
        syllabi: list[Syllabus] = []
        releases_at = datetime.combine(
            term.start_date - timedelta(days=3), time(9, 0), tzinfo=timezone.get_default_timezone()
        )
        now = timezone.now().replace(microsecond=0)
        for section, session, instructor, seq, version in planned:
            unit_code = "GEN" if section.course.code.startswith("GEN") else ""
            scheduled = self._schedule(section, session, rooms, instructor, seq)
            if scheduled is not None:
                days, start, end, room = scheduled
                if instructor is not None:
                    assignments.append(
                        SectionInstructor(section=section, instructor=instructor, role=InstructorRole.PRIMARY)
                    )
                for day in days:
                    meetings.append(
                        SectionMeeting(
                            section=section,
                            weekday=day,
                            start_time=start,
                            end_time=end,
                            room=room,
                            start_date=session.start_date,
                            end_date=session.end_date,
                        )
                    )
            if unit_code != "GEN" and seq % 4 == 0:
                seat_groups.append(
                    SectionSeatGroup(
                        section=section,
                        name={"en": "Majors", "ko": "전공 학생", "zh-hans": "本专业学生"},
                        capacity=30,
                        eligibility=TargetCriteria(org_unit_ids=[section.org_unit_id]),
                        releases_at=releases_at,
                    )
                )
            if instructor is not None and (instructor.person_id == demo_person_id or seq % 3 == 0):
                syllabi.append(self._syllabus(section, version, now))

        SectionInstructor.objects.bulk_create(assignments, batch_size=500)
        SectionMeeting.objects.bulk_create(meetings, batch_size=500)
        SectionSeatGroup.objects.bulk_create(seat_groups, batch_size=500)
        Syllabus.objects.bulk_create(syllabi, batch_size=500)

    def _instructors(self) -> tuple[dict[int, list[Any]], list[Any], int | None]:
        try:
            from ninefruits.person.models import Instructor
        except ImportError:  # pragma: no cover - people app without instructors
            return {}, [], None
        from ninefruits.security.models import User

        instructors = list(Instructor.objects.current().order_by("id"))
        by_unit: dict[int, list[Any]] = defaultdict(list)
        for instructor in instructors:
            by_unit[instructor.org_unit_id].append(instructor)
        demo = (
            User.objects.filter(email=f"instructor@{conf.DEMO_EMAIL_DOMAIN}")
            .values_list("person_id", flat=True)
            .first()
        )
        return dict(by_unit), instructors, demo

    def _schedule(
        self, section: Section, session: TermSession, rooms: list[Room], instructor: Any, seed: int
    ) -> tuple[list[int], time, time, Room] | None:
        candidates = [(pattern, start) for pattern in PATTERNS for start in STARTS]
        offset = seed % len(candidates)
        candidates = candidates[offset:] + candidates[:offset]
        overlapping = ["FULL", "A", "B"] if session.is_full_term else [session.code, "FULL"]
        for days, start in candidates:
            if instructor is not None and self._is_taken(f"i{instructor.pk}", days, start, overlapping):
                continue
            room = next(
                (
                    room
                    for room in rooms
                    if (room.capacity or 0) >= section.capacity
                    and not self._is_taken(f"r{room.pk}", days, start, overlapping)
                ),
                None,
            )
            if room is None:
                continue
            for day in days:
                self.taken.add(f"r{room.pk}|{day}|{start}|{session.code}")
                if instructor is not None:
                    self.taken.add(f"i{instructor.pk}|{day}|{start}|{session.code}")
            begin = _clock(start)
            end_minutes = begin.hour * 60 + begin.minute + 75
            return days, begin, time(end_minutes // 60, end_minutes % 60), room
        return None

    def _is_taken(self, resource: str, days: list[int], start: str, sessions: list[str]) -> bool:
        return any(f"{resource}|{day}|{start}|{session}" in self.taken for day in days for session in sessions)

    @staticmethod
    def _syllabus(section: Section, version: CourseVersion, now: datetime) -> Syllabus:
        title = version.title_translations.get("ko") or str(version.title)
        weeks = [
            {"week": week, "topic": "중간고사" if week == 8 else ("기말고사" if week == 16 else f"{week}주차 주제")}
            for week in range(1, 17)
        ]
        return Syllabus(
            section=section,
            language="ko",
            content={
                "overview": f"{title} 과목의 핵심 개념을 다룬다.",
                "objectives": "기본 개념을 설명할 수 있다.\n과제를 통해 개념을 적용할 수 있다.",
                "materials": "강의 자료는 수업 중 배포한다.",
                "policies": "출석은 매 수업 확인한다.",
                "assessment": [
                    {"item": "중간고사", "weight": 30},
                    {"item": "기말고사", "weight": 40},
                    {"item": "과제", "weight": 20},
                    {"item": "출석", "weight": 10},
                ],
                "weekly_plan": weeks,
            },
            published_at=now,
        )
