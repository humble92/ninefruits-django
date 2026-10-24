-- Row level security for people and guardians.
-- A person is visible to: themselves, their creator, holders of people.view, anyone who
-- can see one of their student records, and (name only matters there) any signed-in user
-- for instructors. Sensitive columns are encrypted in addition (HasEncryptedPii).

ALTER TABLE people ENABLE ROW LEVEL SECURITY;

CREATE POLICY people_owner_select ON people FOR SELECT
    USING (id = (SELECT util.current_person_id()));

CREATE POLICY people_owner_update ON people FOR UPDATE
    USING (id = (SELECT util.current_person_id()))
    WITH CHECK (id = (SELECT util.current_person_id()));

-- Lets INSERT ... RETURNING work before the person has a student record.
CREATE POLICY people_creator_select ON people FOR SELECT
    USING (created_by_id = (SELECT util.current_user_id()));

CREATE POLICY people_viewer_select ON people FOR SELECT
    USING ((SELECT util.has_permission('people.view')));

CREATE POLICY people_via_student_records_select ON people FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.person_id = people.id));

CREATE POLICY people_instructors_select ON people FOR SELECT
    USING ((SELECT util.current_user_id()) IS NOT NULL AND EXISTS (SELECT 1 FROM instructors AS i WHERE i.person_id = people.id));

CREATE POLICY people_manager_all ON people FOR ALL
    USING ((SELECT util.has_permission('people.manage')))
    WITH CHECK ((SELECT util.has_permission('people.manage')));

-- Staff who manage student records (in any scope) may register people and update the
-- people whose records they manage.
CREATE POLICY people_record_manager_insert ON people FOR INSERT
    WITH CHECK (
        (SELECT util.has_permission('student_records.manage'))
        OR cardinality((SELECT util.permission_org_unit_ids('student_records.manage'))) > 0
        OR cardinality((SELECT util.permission_scope_ids('student_records.manage', 'program'))) > 0
    );

CREATE POLICY people_record_manager_update ON people FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM student_records AS sr
        WHERE sr.person_id = people.id
          AND (
              (SELECT util.has_permission('student_records.manage'))
              OR sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.manage'))::bigint[])
              OR sr.program_id = ANY ((SELECT util.permission_scope_ids('student_records.manage', 'program'))::bigint[])
          )
    ) OR created_by_id = (SELECT util.current_user_id()));

CREATE POLICY people_system_all ON people FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Guardians: visible with the person; changed by the person or by staff who may change
-- the person (same rules as people updates).
ALTER TABLE guardians ENABLE ROW LEVEL SECURITY;

CREATE POLICY guardians_person_select ON guardians FOR SELECT
    USING (EXISTS (SELECT 1 FROM people AS p WHERE p.id = person_id));

CREATE POLICY guardians_owner_all ON guardians FOR ALL
    USING (person_id = (SELECT util.current_person_id()))
    WITH CHECK (person_id = (SELECT util.current_person_id()));

CREATE POLICY guardians_staff_all ON guardians FOR ALL
    USING (
        (SELECT util.has_permission('people.manage'))
        OR EXISTS (
            SELECT 1 FROM student_records AS sr
            WHERE sr.person_id = guardians.person_id
              AND (
                  (SELECT util.has_permission('student_records.manage'))
                  OR sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.manage'))::bigint[])
                  OR sr.program_id = ANY ((SELECT util.permission_scope_ids('student_records.manage', 'program'))::bigint[])
              )
        )
    )
    WITH CHECK (
        (SELECT util.has_permission('people.manage'))
        OR EXISTS (
            SELECT 1 FROM student_records AS sr
            WHERE sr.person_id = guardians.person_id
              AND (
                  (SELECT util.has_permission('student_records.manage'))
                  OR sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.manage'))::bigint[])
                  OR sr.program_id = ANY ((SELECT util.permission_scope_ids('student_records.manage', 'program'))::bigint[])
              )
        )
    );

CREATE POLICY guardians_system_all ON guardians FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
