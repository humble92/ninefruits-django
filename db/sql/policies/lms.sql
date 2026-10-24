-- Row level security for LMS links and logs
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Platforms are configuration (no RLS; credentials are encrypted and never selected by
-- screens). Course links are read by anyone signed in (the portal shows the LMS course
-- link); user links by the user themselves; logs and all writes need lms.manage. Sync jobs
-- run in the system context.

ALTER TABLE lms_course_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY lms_course_links_select ON lms_course_links FOR SELECT
    USING ((SELECT util.current_user_id()) IS NOT NULL);

CREATE POLICY lms_course_links_manage ON lms_course_links FOR ALL
    USING ((SELECT util.has_permission('lms.manage')))
    WITH CHECK ((SELECT util.has_permission('lms.manage')));

CREATE POLICY lms_course_links_system_all ON lms_course_links FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE lms_user_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY lms_user_links_owner_select ON lms_user_links FOR SELECT
    USING (user_id = (SELECT util.current_user_id()));

CREATE POLICY lms_user_links_manage ON lms_user_links FOR ALL
    USING ((SELECT util.has_permission('lms.manage')))
    WITH CHECK ((SELECT util.has_permission('lms.manage')));

CREATE POLICY lms_user_links_system_all ON lms_user_links FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE lms_sync_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY lms_sync_logs_manage ON lms_sync_logs FOR ALL
    USING ((SELECT util.has_permission('lms.manage')))
    WITH CHECK ((SELECT util.has_permission('lms.manage')));

CREATE POLICY lms_sync_logs_system_all ON lms_sync_logs FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));
