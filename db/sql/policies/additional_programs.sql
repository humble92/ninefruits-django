-- Row level security for second major and minor requests
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Students see and file requests for their own records. Staff see requests of students
-- whose records they can see (home department) and those for programs in their
-- additional_programs.approve scope (target department), and decide the latter.

ALTER TABLE additional_program_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY additional_program_requests_record_select ON additional_program_requests FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY additional_program_requests_owner_insert ON additional_program_requests FOR INSERT
    WITH CHECK (
        status = 'requested'
        AND requested_by_id = (SELECT util.current_user_id())
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id()))
    );

-- Students may only cancel their pending requests.
CREATE POLICY additional_program_requests_owner_update ON additional_program_requests FOR UPDATE
    USING (
        status = 'requested'
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id()))
    )
    WITH CHECK (status IN ('requested', 'cancelled'));

CREATE POLICY additional_program_requests_approver_select ON additional_program_requests FOR SELECT
    USING (
        (SELECT util.has_permission('additional_programs.approve'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('additional_programs.approve'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('additional_programs.approve', 'program'))::bigint[])
    );

CREATE POLICY additional_program_requests_approver_update ON additional_program_requests FOR UPDATE
    USING (
        (SELECT util.has_permission('additional_programs.approve'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('additional_programs.approve'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('additional_programs.approve', 'program'))::bigint[])
    )
    WITH CHECK (
        (SELECT util.has_permission('additional_programs.approve'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('additional_programs.approve'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('additional_programs.approve', 'program'))::bigint[])
    );

CREATE POLICY additional_program_requests_system_all ON additional_program_requests FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Records behind pending requests the current user may decide. SECURITY DEFINER: reading
-- the requests under RLS here would recurse (their policies look at student_records).
CREATE OR REPLACE FUNCTION util.additional_program_request_record_ids() RETURNS bigint[]
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT COALESCE(array_agg(DISTINCT r.student_record_id), ARRAY[]::bigint[])
    FROM public.additional_program_requests AS r
    WHERE r.status = 'requested'
      AND (
          util.has_permission('additional_programs.approve')
          OR r.org_unit_id = ANY (util.permission_org_unit_ids('additional_programs.approve'))
          OR r.program_id = ANY (util.permission_scope_ids('additional_programs.approve', 'program'))
      )
$$;

CREATE POLICY student_records_requested_programs_select ON student_records FOR SELECT
    USING (id = ANY ((SELECT util.additional_program_request_record_ids())::bigint[]));

-- Departments see their second-major and minor students (student_records.view or
-- .manage in the additional program's scope), as in StudentRecord::constrainVisibleTo.
-- Seeing is all: changing the record still needs the record's own unit in scope.
CREATE POLICY student_records_additional_programs_select ON student_records FOR SELECT
    USING (id IN (
        SELECT srp.student_record_id
        FROM student_record_programs AS srp
        JOIN programs AS p ON p.id = srp.program_id
        WHERE srp.end_date IS NULL
          AND (
              p.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.view'))::bigint[])
              OR srp.program_id = ANY ((SELECT util.permission_scope_ids('student_records.view', 'program'))::bigint[])
              OR p.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.manage'))::bigint[])
              OR srp.program_id = ANY ((SELECT util.permission_scope_ids('student_records.manage', 'program'))::bigint[])
          )
    ));
