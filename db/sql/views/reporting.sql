-- Reporting views (porting/decisions/0016-graduation-and-reporting.md).
--
-- security_invoker: the row level security of whoever queries applies. Translated columns
-- follow the session locale (SET app.locale = 'ko'); the jsonb originals are kept alongside.
-- Read by the standard reports page and by BI tools through the app_reporting role.

CREATE OR REPLACE VIEW reporting.students WITH (security_invoker = true) AS
SELECT sr.id AS student_record_id,
       sr.student_number,
       sr.person_id,
       COALESCE(util.i18n(p.name_variants), p.family_name || COALESCE(' ' || p.given_name, '')) AS student_name,
       p.family_name,
       p.given_name,
       p.name_variants,
       p.gender,
       p.birth_date,
       sr.program_id,
       pr.code AS program_code,
       util.i18n(pr.name) AS program_name,
       pr.name AS program_name_i18n,
       sr.org_unit_id,
       ou.code AS org_unit_code,
       util.i18n(ou.name) AS org_unit_name,
       ou.name AS org_unit_name_i18n,
       sr.admission_date,
       sr.catalog_year,
       sr.year_level,
       sr.status,
       sr.academic_standing,
       sr.graduation_date,
       sr.degree_number,
       sr.institutional_email
FROM student_records AS sr
JOIN people AS p ON p.id = sr.person_id
JOIN programs AS pr ON pr.id = sr.program_id
JOIN org_units AS ou ON ou.id = sr.org_unit_id;

CREATE OR REPLACE VIEW reporting.headcount WITH (security_invoker = true) AS
SELECT ou.id AS org_unit_id,
       ou.code AS org_unit_code,
       util.i18n(ou.name) AS org_unit_name,
       pr.id AS program_id,
       pr.code AS program_code,
       util.i18n(pr.name) AS program_name,
       sr.year_level,
       sr.status,
       count(*) AS students
FROM student_records AS sr
JOIN programs AS pr ON pr.id = sr.program_id
JOIN org_units AS ou ON ou.id = sr.org_unit_id
GROUP BY ou.id, ou.code, ou.name, pr.id, pr.code, pr.name, sr.year_level, sr.status;

CREATE OR REPLACE VIEW reporting.term_records WITH (security_invoker = true) AS
SELECT tr.id AS term_record_id,
       tr.student_record_id,
       sr.student_number,
       t.id AS term_id,
       t.code AS term_code,
       util.i18n(t.name) AS term_name,
       tr.attempted_credits,
       tr.earned_credits,
       tr.term_gpa,
       tr.cumulative_earned_credits,
       tr.cumulative_gpa,
       tr.academic_standing,
       tr.warning_count,
       tr.is_honors,
       tr.honors_rank,
       tr.closed_at
FROM term_records AS tr
JOIN student_records AS sr ON sr.id = tr.student_record_id
JOIN terms AS t ON t.id = tr.term_id;

CREATE OR REPLACE VIEW reporting.course_grades WITH (security_invoker = true) AS
SELECT e.id AS enrollment_id,
       e.student_record_id,
       sr.student_number,
       t.code AS term_code,
       util.i18n(t.name) AS term_name,
       c.code AS course_code,
       util.i18n(cv.title) AS course_title,
       cv.title AS course_title_i18n,
       s.section_code,
       e.credits,
       e.course_category_id,
       util.i18n(cc.name) AS course_category,
       e.status,
       e.grade_status,
       e.grade_code,
       e.is_passed,
       e.is_retake
FROM enrollments AS e
JOIN student_records AS sr ON sr.id = e.student_record_id
JOIN terms AS t ON t.id = e.term_id
JOIN courses AS c ON c.id = e.course_id
JOIN course_versions AS cv ON cv.id = e.course_version_id
JOIN sections AS s ON s.id = e.section_id
LEFT JOIN course_categories AS cc ON cc.id = e.course_category_id;

CREATE OR REPLACE VIEW reporting.section_enrollments WITH (security_invoker = true) AS
SELECT s.id AS section_id,
       t.code AS term_code,
       util.i18n(t.name) AS term_name,
       c.code AS course_code,
       util.i18n(cv.title) AS course_title,
       s.section_code,
       ou.code AS org_unit_code,
       util.i18n(ou.name) AS org_unit_name,
       s.status,
       s.capacity,
       (SELECT count(*) FROM enrollments AS e WHERE e.section_id = s.id AND e.status IN ('enrolled', 'completed')) AS enrolled,
       (SELECT count(*) FROM waitlist_entries AS w WHERE w.section_id = s.id AND w.status = 'waiting') AS waiting,
       (SELECT string_agg(COALESCE(util.i18n(ip.name_variants), ip.family_name || COALESCE(' ' || ip.given_name, '')), ', ' ORDER BY si.role)
          FROM section_instructors AS si JOIN instructors AS i ON i.id = si.instructor_id JOIN people AS ip ON ip.id = i.person_id
         WHERE si.section_id = s.id) AS instructors
FROM sections AS s
JOIN terms AS t ON t.id = s.term_id
JOIN courses AS c ON c.id = s.course_id
JOIN course_versions AS cv ON cv.id = s.course_version_id
JOIN org_units AS ou ON ou.id = s.org_unit_id;

CREATE OR REPLACE VIEW reporting.section_meetings WITH (security_invoker = true) AS
SELECT m.id AS section_meeting_id,
       s.id AS section_id,
       t.code AS term_code,
       c.code AS course_code,
       util.i18n(cv.title) AS course_title,
       s.section_code,
       m.weekday,
       m.start_time,
       m.end_time,
       m.start_date,
       m.end_date,
       b.code AS building_code,
       r.code AS room_code,
       m.is_active
FROM section_meetings AS m
JOIN sections AS s ON s.id = m.section_id
JOIN terms AS t ON t.id = s.term_id
JOIN courses AS c ON c.id = s.course_id
JOIN course_versions AS cv ON cv.id = s.course_version_id
LEFT JOIN rooms AS r ON r.id = m.room_id
LEFT JOIN buildings AS b ON b.id = r.building_id;

CREATE OR REPLACE VIEW reporting.status_changes WITH (security_invoker = true) AS
SELECT sc.id AS status_change_id,
       sc.student_record_id,
       sr.student_number,
       sct.code AS type_code,
       util.i18n(sct.name) AS type_name,
       sc.from_status,
       sc.to_status,
       sc.effective_date,
       t.code AS term_code,
       sc.status,
       sc.requested_at,
       sc.decided_at
FROM student_status_changes AS sc
JOIN student_records AS sr ON sr.id = sc.student_record_id
JOIN student_status_change_types AS sct ON sct.id = sc.status_change_type_id
LEFT JOIN terms AS t ON t.id = sc.term_id;

CREATE OR REPLACE VIEW reporting.degree_audits WITH (security_invoker = true) AS
SELECT da.id AS degree_audit_id,
       da.student_record_id,
       sr.student_number,
       da.program_role,
       pr.code AS program_code,
       util.i18n(pr.name) AS program_name,
       da.is_satisfied,
       da.earned_credits,
       da.required_credits,
       da.cumulative_gpa,
       da.audited_at,
       t.code AS term_code
FROM degree_audits AS da
JOIN student_records AS sr ON sr.id = da.student_record_id
JOIN programs AS pr ON pr.id = da.program_id
LEFT JOIN terms AS t ON t.id = da.term_id
WHERE da.id IN (SELECT max(id) FROM degree_audits GROUP BY student_record_id, program_role);
