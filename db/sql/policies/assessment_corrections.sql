-- Row level security for examination result corrections
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Whoever sees the result sees its corrections (staff, the student). Staff who record
-- results request them; the decision is authorized by the application (assessments.manage,
-- not the requester).

ALTER TABLE assessment_result_corrections ENABLE ROW LEVEL SECURITY;

CREATE POLICY assessment_result_corrections_result_select ON assessment_result_corrections FOR SELECT
    USING (EXISTS (SELECT 1 FROM assessment_results AS r WHERE r.id = assessment_result_id));

CREATE POLICY assessment_result_corrections_staff_write ON assessment_result_corrections FOR ALL
    USING (
        ((SELECT util.has_permission('assessments.record')) OR (SELECT util.has_permission('assessments.manage')))
        AND EXISTS (SELECT 1 FROM assessment_results AS r WHERE r.id = assessment_result_id)
    )
    WITH CHECK (
        ((SELECT util.has_permission('assessments.record')) OR (SELECT util.has_permission('assessments.manage')))
        AND EXISTS (SELECT 1 FROM assessment_results AS r WHERE r.id = assessment_result_id)
    );

CREATE POLICY assessment_result_corrections_system_all ON assessment_result_corrections FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
