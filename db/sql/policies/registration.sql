-- Row level security for registration
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Students see and change their own registration (status only: grades are not theirs to
-- write). Staff see what belongs to student records they can see, and the enrollments of
-- sections in their scope; registration.manage in scope changes them. The section's
-- instructors see its enrollments.

-- Enrollments ---------------------------------------------------------------------------
ALTER TABLE enrollments ENABLE ROW LEVEL SECURITY;

CREATE POLICY enrollments_record_select ON enrollments FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY enrollments_section_staff_select ON enrollments FOR SELECT
    USING (
        (SELECT util.has_permission('enrollments.view'))
        OR (SELECT util.has_permission('registration.manage'))
        OR EXISTS (
            SELECT 1 FROM sections AS s WHERE s.id = section_id
              AND (s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('enrollments.view'))::bigint[])
                OR s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration.manage'))::bigint[]))
        )
    );

CREATE POLICY enrollments_instructor_select ON enrollments FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM section_instructors AS si JOIN instructors AS i ON i.id = si.instructor_id
        WHERE si.section_id = enrollments.section_id AND i.person_id = (SELECT util.current_person_id())
    ));

CREATE POLICY enrollments_owner_insert ON enrollments FOR INSERT
    WITH CHECK (
        status = 'enrolled' AND grade_status = 'none'
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id()))
    );

CREATE POLICY enrollments_owner_update ON enrollments FOR UPDATE
    USING (
        status = 'enrolled'
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id()))
    )
    WITH CHECK (status IN ('enrolled', 'dropped', 'withdrawn') AND grade_status = 'none' AND grade_code IS NULL AND is_passed IS NULL);

CREATE POLICY enrollments_staff_all ON enrollments FOR ALL
    USING (
        (SELECT util.has_permission('registration.manage'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration.manage'))::bigint[]))
    )
    WITH CHECK (
        (SELECT util.has_permission('registration.manage'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration.manage'))::bigint[]))
    );

CREATE POLICY enrollments_system_all ON enrollments FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Waitlist entries ----------------------------------------------------------------------
ALTER TABLE waitlist_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY waitlist_entries_record_select ON waitlist_entries FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY waitlist_entries_owner_insert ON waitlist_entries FOR INSERT
    WITH CHECK (
        status = 'waiting'
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id()))
    );

-- Students may only leave the list.
CREATE POLICY waitlist_entries_owner_update ON waitlist_entries FOR UPDATE
    USING (
        status = 'waiting'
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id()))
    )
    WITH CHECK (status IN ('waiting', 'removed'));

CREATE POLICY waitlist_entries_staff_all ON waitlist_entries FOR ALL
    USING (
        (SELECT util.has_permission('registration.manage'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration.manage'))::bigint[]))
    )
    WITH CHECK (
        (SELECT util.has_permission('registration.manage'))
        OR EXISTS (SELECT 1 FROM sections AS s WHERE s.id = section_id AND s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration.manage'))::bigint[]))
    );

CREATE POLICY waitlist_entries_system_all ON waitlist_entries FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Cart ----------------------------------------------------------------------------------
ALTER TABLE cart_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY cart_items_record_select ON cart_items FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY cart_items_owner_all ON cart_items FOR ALL
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id())))
    WITH CHECK (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id())));

CREATE POLICY cart_items_system_all ON cart_items FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Holds and overrides -------------------------------------------------------------------
ALTER TABLE registration_holds ENABLE ROW LEVEL SECURITY;

CREATE POLICY registration_holds_record_select ON registration_holds FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY registration_holds_staff_all ON registration_holds FOR ALL
    USING (
        (SELECT util.has_permission('registration_holds.manage'))
        OR EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration_holds.manage'))::bigint[]))
    )
    WITH CHECK (
        (SELECT util.has_permission('registration_holds.manage'))
        OR EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration_holds.manage'))::bigint[]))
    );

CREATE POLICY registration_holds_system_all ON registration_holds FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE registration_overrides ENABLE ROW LEVEL SECURITY;

CREATE POLICY registration_overrides_record_select ON registration_overrides FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY registration_overrides_staff_all ON registration_overrides FOR ALL
    USING (
        (SELECT util.has_permission('registration_holds.manage'))
        OR EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration_holds.manage'))::bigint[]))
    )
    WITH CHECK (
        (SELECT util.has_permission('registration_holds.manage'))
        OR EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('registration_holds.manage'))::bigint[]))
    );

CREATE POLICY registration_overrides_system_all ON registration_overrides FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Attempt log: append only --------------------------------------------------------------
ALTER TABLE registration_attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY registration_attempts_record_select ON registration_attempts FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY registration_attempts_insert ON registration_attempts FOR INSERT
    WITH CHECK (
        actor_id IS NOT DISTINCT FROM (SELECT util.current_user_id())
        OR (SELECT util.is_system_context())
    );
