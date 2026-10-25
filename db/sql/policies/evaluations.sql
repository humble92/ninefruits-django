-- Row level security for course evaluation
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Answers are written only by the application in the system context, after it checked the
-- student's enrollment: they carry no student to check here. Students see their own
-- completions, never answers. Answers are read by staff with evaluations.view (or
-- evaluations.manage) for the offering unit, and by the section's instructors once the
-- term's results are published; the minimum response rules are applied by the
-- application on top.

ALTER TABLE evaluation_completions ENABLE ROW LEVEL SECURITY;

CREATE POLICY evaluation_completions_owner_select ON evaluation_completions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM enrollments AS e JOIN student_records AS sr ON sr.id = e.student_record_id
        WHERE e.id = enrollment_id AND sr.person_id = (SELECT util.current_person_id())
    ));

CREATE POLICY evaluation_completions_staff_select ON evaluation_completions FOR SELECT
    USING (
        (SELECT util.has_permission('evaluations.view')) OR (SELECT util.has_permission('evaluations.manage'))
        OR EXISTS (
            SELECT 1 FROM enrollments AS e JOIN sections AS s ON s.id = e.section_id
            WHERE e.id = enrollment_id
              AND (s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('evaluations.view'))::bigint[])
                OR s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('evaluations.manage'))::bigint[]))
        )
    );

CREATE POLICY evaluation_completions_system_all ON evaluation_completions FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE evaluation_responses ENABLE ROW LEVEL SECURITY;

CREATE POLICY evaluation_responses_staff_select ON evaluation_responses FOR SELECT
    USING (
        (SELECT util.has_permission('evaluations.view')) OR (SELECT util.has_permission('evaluations.manage'))
        OR EXISTS (
            SELECT 1 FROM sections AS s WHERE s.id = section_id
              AND (s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('evaluations.view'))::bigint[])
                OR s.org_unit_id = ANY ((SELECT util.permission_org_unit_ids('evaluations.manage'))::bigint[]))
        )
    );

CREATE POLICY evaluation_responses_instructor_select ON evaluation_responses FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM term_evaluations AS te WHERE te.term_id = evaluation_responses.term_id AND te.results_published_at IS NOT NULL)
        AND EXISTS (
            SELECT 1 FROM section_instructors AS si JOIN instructors AS i ON i.id = si.instructor_id
            WHERE si.section_id = evaluation_responses.section_id AND i.person_id = (SELECT util.current_person_id())
        )
    );

CREATE POLICY evaluation_responses_system_all ON evaluation_responses FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE evaluation_answers ENABLE ROW LEVEL SECURITY;

-- Whoever sees the response sees its answers.
CREATE POLICY evaluation_answers_select ON evaluation_answers FOR SELECT
    USING (EXISTS (SELECT 1 FROM evaluation_responses AS r WHERE r.id = evaluation_response_id));

CREATE POLICY evaluation_answers_system_all ON evaluation_answers FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
