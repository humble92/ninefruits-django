-- Row level security for student records and their status changes
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Staff scope for a permission P on a record:
--   (SELECT util.has_permission(P))                                         global
--   OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids(P))::bigint[])        org unit and below
--   OR program_id = ANY ((SELECT util.permission_scope_ids(P, 'program'))::bigint[]) program

ALTER TABLE student_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY student_records_owner_select ON student_records FOR SELECT
    USING (person_id = (SELECT util.current_person_id()));

CREATE POLICY student_records_staff_select ON student_records FOR SELECT
    USING (
        (SELECT util.has_permission('student_records.view'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.view'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('student_records.view', 'program'))::bigint[])
    );

-- Advisors see the records of students they currently advise.
CREATE POLICY student_records_advisor_select ON student_records FOR SELECT
    USING (id IN (
        SELECT aa.student_record_id
        FROM advisor_assignments AS aa
        JOIN instructors AS i ON i.id = aa.instructor_id
        WHERE i.person_id = (SELECT util.current_person_id())
          AND aa.start_date <= current_date
          AND (aa.end_date IS NULL OR aa.end_date >= current_date)
    ));

CREATE POLICY student_records_staff_all ON student_records FOR ALL
    USING (
        (SELECT util.has_permission('student_records.manage'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.manage'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('student_records.manage', 'program'))::bigint[])
    )
    WITH CHECK (
        (SELECT util.has_permission('student_records.manage'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.manage'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('student_records.manage', 'program'))::bigint[])
    );

CREATE POLICY student_records_system_all ON student_records FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Status changes follow the visibility of their student record. Students may file a
-- request for their own record; staff who manage or approve may decide.
ALTER TABLE student_status_changes ENABLE ROW LEVEL SECURITY;

CREATE POLICY student_status_changes_record_select ON student_status_changes FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY student_status_changes_owner_insert ON student_status_changes FOR INSERT
    WITH CHECK (
        requested_by_id = (SELECT util.current_user_id())
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id()))
    );

-- The requester may cancel their own pending request.
CREATE POLICY student_status_changes_owner_update ON student_status_changes FOR UPDATE
    USING (requested_by_id = (SELECT util.current_user_id()) AND status = 'requested')
    WITH CHECK (requested_by_id = (SELECT util.current_user_id()));

CREATE POLICY student_status_changes_staff_all ON student_status_changes FOR ALL
    USING (EXISTS (
        SELECT 1 FROM student_records AS sr
        WHERE sr.id = student_record_id
          AND (
              (SELECT util.has_permission('student_status_changes.approve'))
              OR sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_status_changes.approve'))::bigint[])
              OR sr.program_id = ANY ((SELECT util.permission_scope_ids('student_status_changes.approve', 'program'))::bigint[])
          )
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM student_records AS sr
        WHERE sr.id = student_record_id
          AND (
              (SELECT util.has_permission('student_status_changes.approve'))
              OR sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_status_changes.approve'))::bigint[])
              OR sr.program_id = ANY ((SELECT util.permission_scope_ids('student_status_changes.approve', 'program'))::bigint[])
          )
    ));

CREATE POLICY student_status_changes_system_all ON student_status_changes FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
