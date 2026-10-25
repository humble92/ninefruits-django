-- The student records of the students enrolled (or completed) in the sections the current
-- person teaches. SECURITY DEFINER so that the student_records policy can read enrollments
-- without recursing into the enrollments policy, which itself reads student_records.
CREATE OR REPLACE FUNCTION util.taught_student_record_ids() RETURNS SETOF bigint
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT e.student_record_id
    FROM public.enrollments AS e
    JOIN public.section_instructors AS si ON si.section_id = e.section_id
    JOIN public.instructors AS i ON i.id = si.instructor_id
    WHERE i.person_id = util.current_person_id()
      AND e.status IN ('enrolled', 'completed')
$$;
