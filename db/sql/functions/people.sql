-- Person of the signed-in user (users.person_id), for "own record" policies.
CREATE OR REPLACE FUNCTION util.current_person_id() RETURNS bigint
    LANGUAGE sql STABLE PARALLEL SAFE
AS $$
    SELECT u.person_id FROM public.users AS u WHERE u.id = util.current_user_id()
$$;

-- Whether a student number is taken, across all records regardless of row level security.
-- Reveals only existence, which the unique index would reveal anyway.
CREATE OR REPLACE FUNCTION util.student_number_exists(candidate text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT EXISTS (SELECT 1 FROM public.student_records WHERE student_number = candidate)
$$;

-- Account of the person who holds the student number, for student number sign-in (before
-- authentication, when row level security would hide every record). Only active records
-- (enrolled, on leave) unless include_ended. Returns NULL when there is no such account.
CREATE OR REPLACE FUNCTION util.user_id_for_student_number(candidate text, include_ended boolean) RETURNS bigint
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT u.id
    FROM public.student_records AS sr
    JOIN public.users AS u ON u.person_id = sr.person_id
    WHERE sr.student_number = candidate
      AND (include_ended OR sr.status IN ('enrolled', 'on_leave'))
    LIMIT 1
$$;

-- Account of the person whose student record has this institutional email, for linking a
-- school SSO account on its first sign-in.
CREATE OR REPLACE FUNCTION util.user_id_for_institutional_email(candidate text) RETURNS bigint
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT u.id
    FROM public.student_records AS sr
    JOIN public.users AS u ON u.person_id = sr.person_id
    WHERE lower(sr.institutional_email) = lower(candidate)
    ORDER BY sr.admission_date DESC
    LIMIT 1
$$;
