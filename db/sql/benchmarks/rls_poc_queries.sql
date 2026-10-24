-- Run as app_runtime after rls_poc_setup.sql. Prints execution times.
\timing on
SET app.user_id = '1012345';
-- Student: own enrollments (portal grade view)
EXPLAIN (ANALYZE, COSTS OFF, SUMMARY ON) SELECT e.* FROM rls_bench_enrollments AS e JOIN rls_bench_student_records AS sr ON sr.id = e.student_record_id;
-- Student: own enrollments by record id (typical Eloquent query)
EXPLAIN (ANALYZE, COSTS OFF, SUMMARY ON) SELECT e.* FROM rls_bench_enrollments AS e WHERE e.student_record_id = 12345;
