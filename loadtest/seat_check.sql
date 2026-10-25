-- Over-enrollment check after a load test (operations manual, load testing).
--
--   psql -h 127.0.0.1 -U postgres -d <database> -v term=<term id> -f loadtest/seat_check.sql
--
-- Run it as a role that sees every row (the schema owner or a superuser; row level security
-- hides other students' enrollments from app_runtime). Every query must return no rows.

\echo 'Sections with more enrolled students than seats:'
SELECT s.id, s.section_code, s.capacity, count(e.id) AS enrolled
FROM sections s
JOIN enrollments e ON e.section_id = s.id AND e.status = 'enrolled'
WHERE s.term_id = :term
GROUP BY s.id
HAVING count(e.id) > s.capacity;

\echo 'Sections whose seat counter differs from their enrollments:'
SELECT s.id, s.section_code, s.enrolled_count, count(e.id) AS enrolled
FROM sections s
LEFT JOIN enrollments e ON e.section_id = s.id AND e.status = 'enrolled'
WHERE s.term_id = :term
GROUP BY s.id
HAVING count(e.id) <> s.enrolled_count;

\echo 'Seat groups with more students than seats, or a counter that differs:'
SELECT g.id, g.section_id, g.capacity, g.enrolled_count, count(e.id) AS enrolled
FROM section_seat_groups g
JOIN sections s ON s.id = g.section_id AND s.term_id = :term
LEFT JOIN enrollments e ON e.seat_group_id = g.id AND e.status = 'enrolled'
GROUP BY g.id
HAVING count(e.id) > g.capacity OR count(e.id) <> g.enrolled_count;

\echo 'Students enrolled twice in one section:'
SELECT section_id, student_record_id, count(*)
FROM enrollments
WHERE term_id = :term AND status = 'enrolled'
GROUP BY section_id, student_record_id
HAVING count(*) > 1;
