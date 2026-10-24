-- Finalized grades (porting/porting-plan.md section 8): once a grade is finalized, the grade
-- and the facts it rests on change only through an approved grade change request. The
-- application applies an approved request with
--   SELECT set_config('app.grade_change_request_id', '<id>', true)
-- in the same transaction; anything else (a direct UPDATE, a bug, a console session) is
-- refused here. SECURITY DEFINER: the check must see the request whatever the caller's
-- row level security allows.

CREATE OR REPLACE FUNCTION util.guard_finalized_grade() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    request_id bigint;
BEGIN
    IF OLD.grade_status <> 'finalized' THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    IF TG_OP = 'UPDATE' AND (
        NEW.grade_status, NEW.grade_code, NEW.score, NEW.grade_points, NEW.counts_in_gpa, NEW.is_passed, NEW.grade_scale_id,
        NEW.status, NEW.credits, NEW.student_record_id, NEW.section_id, NEW.term_id, NEW.course_id, NEW.course_version_id
    ) IS NOT DISTINCT FROM (
        OLD.grade_status, OLD.grade_code, OLD.score, OLD.grade_points, OLD.counts_in_gpa, OLD.is_passed, OLD.grade_scale_id,
        OLD.status, OLD.credits, OLD.student_record_id, OLD.section_id, OLD.term_id, OLD.course_id, OLD.course_version_id
    ) THEN
        RETURN NEW;
    END IF;

    request_id := NULLIF(current_setting('app.grade_change_request_id', true), '')::bigint;

    IF TG_OP = 'UPDATE' AND request_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM public.grade_change_requests AS r
        WHERE r.id = request_id AND r.enrollment_id = OLD.id AND r.status = 'approved' AND r.applied_at IS NULL
    ) AND NEW.grade_status = 'finalized' THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'The finalized grade of enrollment % changes only through an approved grade change request.', OLD.id
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

DROP TRIGGER IF EXISTS enrollments_guard_finalized_grade ON enrollments;
CREATE TRIGGER enrollments_guard_finalized_grade
    BEFORE UPDATE OR DELETE ON enrollments
    FOR EACH ROW EXECUTE FUNCTION util.guard_finalized_grade();
