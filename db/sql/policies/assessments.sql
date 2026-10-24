-- Row level security for examinations
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Kinds, areas and sessions are configuration (no RLS). Registrations and results belong to
-- a student record: staff see those of the records they can see and write them with
-- assessments.record; students see their own registrations, and their own results once the
-- session's results are published (external results at once). Students register through
-- the application in the system context, after it checked the window and the capacity.

ALTER TABLE assessment_registrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY assessment_registrations_record_select ON assessment_registrations FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY assessment_registrations_staff_write ON assessment_registrations FOR ALL
    USING (
        (SELECT util.has_permission('assessments.record'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    )
    WITH CHECK (
        (SELECT util.has_permission('assessments.record'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    );

CREATE POLICY assessment_registrations_system_all ON assessment_registrations FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE assessment_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY assessment_results_owner_select ON assessment_results FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id AND sr.person_id = (SELECT util.current_person_id()))
        AND (
            assessment_session_id IS NULL
            OR EXISTS (SELECT 1 FROM assessment_sessions AS s WHERE s.id = assessment_session_id AND s.results_published_at IS NOT NULL)
        )
    );

CREATE POLICY assessment_results_staff_select ON assessment_results FOR SELECT
    USING (
        ((SELECT util.has_permission('assessments.record')) OR (SELECT util.has_permission('assessments.manage')))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    );

CREATE POLICY assessment_results_staff_write ON assessment_results FOR ALL
    USING (
        (SELECT util.has_permission('assessments.record'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    )
    WITH CHECK (
        (SELECT util.has_permission('assessments.record'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    );

CREATE POLICY assessment_results_system_all ON assessment_results FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE assessment_component_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY assessment_component_scores_result_select ON assessment_component_scores FOR SELECT
    USING (EXISTS (SELECT 1 FROM assessment_results AS r WHERE r.id = assessment_result_id));

CREATE POLICY assessment_component_scores_staff_write ON assessment_component_scores FOR ALL
    USING (
        (SELECT util.has_permission('assessments.record'))
        AND EXISTS (SELECT 1 FROM assessment_results AS r WHERE r.id = assessment_result_id)
    )
    WITH CHECK (
        (SELECT util.has_permission('assessments.record'))
        AND EXISTS (SELECT 1 FROM assessment_results AS r WHERE r.id = assessment_result_id)
    );

CREATE POLICY assessment_component_scores_system_all ON assessment_component_scores FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
