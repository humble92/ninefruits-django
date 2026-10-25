-- Row level security for grades
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Instructors enter and submit grades of their own sections until they are submitted.
-- grades.manage (globally or for the offering org unit) finalizes and returns grades.
-- Finalized grades are further guarded by util.guard_finalized_grade().

-- Enrollments: grade entry ---------------------------------------------------------------
CREATE POLICY enrollments_grades_staff_select ON enrollments FOR SELECT
    USING (
        (SELECT util.has_permission('grades.view'))
        OR EXISTS (
            SELECT 1 FROM sections AS s WHERE s.id = section_id
              AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('grades.view'))::bigint[])
        )
    );

CREATE POLICY enrollments_instructor_grade_update ON enrollments FOR UPDATE
    USING (
        status = 'enrolled' AND grade_status IN ('none', 'draft')
        AND EXISTS (
            SELECT 1 FROM section_instructors AS si JOIN instructors AS i ON i.id = si.instructor_id
            WHERE si.section_id = enrollments.section_id AND i.person_id = (SELECT util.current_person_id())
        )
    )
    WITH CHECK (status = 'enrolled' AND grade_status IN ('none', 'draft', 'submitted'));

CREATE POLICY enrollments_grades_staff_update ON enrollments FOR UPDATE
    USING (
        (SELECT util.has_permission('grades.manage'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('grades.manage'))::bigint[]))
        OR (SELECT util.has_permission('grade_changes.approve'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('grade_changes.approve'))::bigint[]))
    )
    WITH CHECK (
        (SELECT util.has_permission('grades.manage'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('grades.manage'))::bigint[]))
        OR (SELECT util.has_permission('grade_changes.approve'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('grade_changes.approve'))::bigint[]))
    );

-- Grade change requests ------------------------------------------------------------------
ALTER TABLE grade_change_requests ENABLE ROW LEVEL SECURITY;

-- Anyone who can see the enrollment sees its requests (requester, instructors, staff, the
-- student through their own enrollment).
CREATE POLICY grade_change_requests_select ON grade_change_requests FOR SELECT
    USING (EXISTS (SELECT 1 FROM enrollments AS e WHERE e.id = enrollment_id));

CREATE POLICY grade_change_requests_insert ON grade_change_requests FOR INSERT
    WITH CHECK (
        requested_by_id = (SELECT util.current_user_id()) AND status = 'pending'
        AND EXISTS (
            SELECT 1 FROM enrollments AS e JOIN sections AS s ON s.id = e.section_id
            WHERE e.id = enrollment_id AND (
                (SELECT util.has_permission('grade_changes.request'))
                OR s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('grade_changes.request'))::bigint[])
                OR EXISTS (
                    SELECT 1 FROM section_instructors AS si JOIN instructors AS i ON i.id = si.instructor_id
                    WHERE si.section_id = s.id AND i.person_id = (SELECT util.current_person_id())
                )
            )
        )
    );

-- The requester cancels their own pending request; approvers decide and apply.
CREATE POLICY grade_change_requests_requester_update ON grade_change_requests FOR UPDATE
    USING (status = 'pending' AND requested_by_id = (SELECT util.current_user_id()))
    WITH CHECK (status IN ('pending', 'cancelled') AND requested_by_id = (SELECT util.current_user_id()));

CREATE POLICY grade_change_requests_approver_update ON grade_change_requests FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM enrollments AS e JOIN sections AS s ON s.id = e.section_id
        WHERE e.id = enrollment_id AND (
            (SELECT util.has_permission('grade_changes.approve'))
            OR s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('grade_changes.approve'))::bigint[])
        )
    ))
    WITH CHECK (decided_by_id IS NULL OR decided_by_id = (SELECT util.current_user_id()));

CREATE POLICY grade_change_requests_system_all ON grade_change_requests FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Term records -------------------------------------------------------------------------
ALTER TABLE term_records ENABLE ROW LEVEL SECURITY;

-- Whoever sees the student record (the student, advisors, staff in scope).
CREATE POLICY term_records_record_select ON term_records FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY term_records_staff_all ON term_records FOR ALL
    USING ((SELECT util.has_permission('grades.manage')))
    WITH CHECK ((SELECT util.has_permission('grades.manage')));

CREATE POLICY term_records_system_all ON term_records FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
