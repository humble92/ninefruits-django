-- Row level security for degree audits and waivers
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Audits and waivers belong to a student record: whoever sees the record (staff in scope,
-- the student) reads them. graduation.audit writes audits, graduation.process writes waivers.

ALTER TABLE degree_audits ENABLE ROW LEVEL SECURITY;

CREATE POLICY degree_audits_record_select ON degree_audits FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY degree_audits_staff_write ON degree_audits FOR ALL
    USING (
        (SELECT util.has_permission('graduation.audit'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    )
    WITH CHECK (
        (SELECT util.has_permission('graduation.audit'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    );

CREATE POLICY degree_audits_system_all ON degree_audits FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE degree_requirement_waivers ENABLE ROW LEVEL SECURITY;

CREATE POLICY degree_requirement_waivers_record_select ON degree_requirement_waivers FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY degree_requirement_waivers_staff_write ON degree_requirement_waivers FOR ALL
    USING (
        (SELECT util.has_permission('graduation.process'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    )
    WITH CHECK (
        (SELECT util.has_permission('graduation.process'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    );

CREATE POLICY degree_requirement_waivers_system_all ON degree_requirement_waivers FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
