-- Row level security for certificate issues
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Students see their own issued certificates. Staff see the issues of student records they
-- can see, and certificates.issue writes them. Types and templates are configuration.

ALTER TABLE certificate_issues ENABLE ROW LEVEL SECURITY;

CREATE POLICY certificate_issues_record_select ON certificate_issues FOR SELECT
    USING (EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id));

CREATE POLICY certificate_issues_staff_write ON certificate_issues FOR ALL
    USING (
        (SELECT util.has_permission('certificates.issue'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    )
    WITH CHECK (
        (SELECT util.has_permission('certificates.issue'))
        AND EXISTS (SELECT 1 FROM student_records AS sr WHERE sr.id = student_record_id)
    );

CREATE POLICY certificate_issues_system_all ON certificate_issues FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
