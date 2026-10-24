-- Row level security for applications
-- (porting/decisions/0003-row-level-security.md: function calls wrapped in SELECT).
--
-- Applicants see and edit their own applications. They can only leave an application in
-- a state an applicant may set (draft, submitted, confirmed, withdrawn); staff decisions
-- need applications.review in scope. Matriculation runs as a system actor
-- (DatabaseSessionContext::asSystem) after the application checks the permission.

ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY applications_owner_select ON applications FOR SELECT
    USING (person_id = (SELECT util.current_person_id()));

CREATE POLICY applications_owner_insert ON applications FOR INSERT
    WITH CHECK (person_id = (SELECT util.current_person_id()) AND status = 'draft');

CREATE POLICY applications_owner_update ON applications FOR UPDATE
    USING (
        person_id = (SELECT util.current_person_id())
        AND status IN ('draft', 'submitted', 'under_review', 'admitted')
    )
    WITH CHECK (
        person_id = (SELECT util.current_person_id())
        AND status IN ('draft', 'submitted', 'confirmed', 'withdrawn')
    );

-- Reviewers see what they may decide, as in Application::constrainVisibleTo.
CREATE POLICY applications_staff_select ON applications FOR SELECT
    USING (
        (SELECT util.has_permission('applications.view'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('applications.view'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('applications.view', 'program'))::bigint[])
        OR (SELECT util.has_permission('applications.review'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('applications.review'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('applications.review', 'program'))::bigint[])
    );

CREATE POLICY applications_staff_update ON applications FOR UPDATE
    USING (
        (SELECT util.has_permission('applications.review'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('applications.review'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('applications.review', 'program'))::bigint[])
    )
    WITH CHECK (
        (SELECT util.has_permission('applications.review'))
        OR org_unit_id = ANY ((SELECT util.permission_org_unit_ids('applications.review'))::bigint[])
        OR program_id = ANY ((SELECT util.permission_scope_ids('applications.review', 'program'))::bigint[])
    );

CREATE POLICY applications_system_all ON applications FOR ALL
    USING ((SELECT util.is_system_context()))
    WITH CHECK ((SELECT util.is_system_context()));

-- Staff who can see an application can see the applicant (the subquery is itself limited
-- by the application policies above).
CREATE POLICY people_via_applications_select ON people FOR SELECT
    USING (id IN (SELECT a.person_id FROM applications AS a));
