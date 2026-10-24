-- Row level security for attendance
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Class meetings are schedule information: anyone signed in reads them; the section's
-- instructors and sections.manage staff in scope write them. Attendance records: the
-- student sees their own, the instructors and staff who see the section see all of its
-- records, and the instructors and sections.manage staff write them.
--
-- Also: a section's instructors see the student records (and so the people) of the
-- students enrolled in it, for the roster, attendance and grade entry.

CREATE POLICY student_records_instructor_select ON student_records FOR SELECT
    USING (id IN (SELECT util.taught_student_record_ids()));

ALTER TABLE class_meetings ENABLE ROW LEVEL SECURITY;

CREATE POLICY class_meetings_select ON class_meetings FOR SELECT
    USING ((SELECT util.current_user_id()) IS NOT NULL);

CREATE POLICY class_meetings_instructor_write ON class_meetings FOR ALL
    USING (EXISTS (
        SELECT 1 FROM section_instructors AS si JOIN instructors AS i ON i.id = si.instructor_id
        WHERE si.section_id = class_meetings.section_id AND i.person_id = (SELECT util.current_person_id())
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM section_instructors AS si JOIN instructors AS i ON i.id = si.instructor_id
        WHERE si.section_id = class_meetings.section_id AND i.person_id = (SELECT util.current_person_id())
    ));

CREATE POLICY class_meetings_staff_write ON class_meetings FOR ALL
    USING (
        (SELECT util.has_permission('sections.manage'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('sections.manage'))::bigint[]))
    )
    WITH CHECK (
        (SELECT util.has_permission('sections.manage'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('sections.manage'))::bigint[]))
    );

CREATE POLICY class_meetings_system_all ON class_meetings FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;

-- Whoever sees the enrollment (the student, the instructors, staff in scope) sees the record.
CREATE POLICY attendance_records_enrollment_select ON attendance_records FOR SELECT
    USING (EXISTS (SELECT 1 FROM enrollments AS e WHERE e.id = enrollment_id));

CREATE POLICY attendance_records_instructor_write ON attendance_records FOR ALL
    USING (EXISTS (
        SELECT 1 FROM class_meetings AS m
        JOIN section_instructors AS si ON si.section_id = m.section_id
        JOIN instructors AS i ON i.id = si.instructor_id
        WHERE m.id = class_meeting_id AND i.person_id = (SELECT util.current_person_id())
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM class_meetings AS m
        JOIN section_instructors AS si ON si.section_id = m.section_id
        JOIN instructors AS i ON i.id = si.instructor_id
        WHERE m.id = class_meeting_id AND i.person_id = (SELECT util.current_person_id())
    ));

CREATE POLICY attendance_records_staff_write ON attendance_records FOR ALL
    USING (
        (SELECT util.has_permission('sections.manage'))
        OR EXISTS (
            SELECT 1 FROM class_meetings AS m JOIN sections AS s ON s.id = m.section_id
            WHERE m.id = class_meeting_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('sections.manage'))::bigint[])
        )
    )
    WITH CHECK (
        (SELECT util.has_permission('sections.manage'))
        OR EXISTS (
            SELECT 1 FROM class_meetings AS m JOIN sections AS s ON s.id = m.section_id
            WHERE m.id = class_meeting_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('sections.manage'))::bigint[])
        )
    );

CREATE POLICY attendance_records_system_all ON attendance_records FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
