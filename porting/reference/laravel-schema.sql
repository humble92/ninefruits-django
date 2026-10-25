--
-- PostgreSQL database dump
--


-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: audit; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA audit;


--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: reporting; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA reporting;


--
-- Name: util; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA util;


--
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;


--
-- Name: EXTENSION btree_gist; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION btree_gist IS 'support for indexing common datatypes in GiST';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: prevent_modification(); Type: FUNCTION; Schema: audit; Owner: -
--

CREATE FUNCTION audit.prevent_modification() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF current_setting('app.audit_maintenance', true) = 'on' THEN
        RETURN NULL;
    END IF;

    RAISE EXCEPTION 'Audit records are append-only: %.%', TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END
$$;


--
-- Name: record_change(); Type: FUNCTION; Schema: audit; Owner: -
--

CREATE FUNCTION audit.record_change() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'pg_catalog', 'pg_temp'
    AS $$
DECLARE
    old_row jsonb;
    new_row jsonb;
    changed text[];
    redacted_column text;
BEGIN
    IF TG_LEVEL = 'STATEMENT' THEN
        INSERT INTO audit.record_changes (table_schema, table_name, operation, user_id, actor, request_id, database_user)
        VALUES (TG_TABLE_SCHEMA, TG_TABLE_NAME, TG_OP, util.current_user_id(), util.current_actor(), util.current_request_id(), session_user);

        RETURN NULL;
    END IF;

    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        old_row := to_jsonb(OLD);
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        new_row := to_jsonb(NEW);
    END IF;

    IF TG_OP = 'UPDATE' THEN
        SELECT array_agg(n.key ORDER BY n.key) INTO changed
        FROM jsonb_each(new_row) AS n
        WHERE n.value IS DISTINCT FROM old_row -> n.key;

        IF changed IS NULL THEN
            RETURN NULL;
        END IF;
    END IF;

    IF TG_NARGS > 0 THEN
        FOREACH redacted_column IN ARRAY TG_ARGV LOOP
            IF old_row IS NOT NULL AND jsonb_typeof(old_row -> redacted_column) <> 'null' THEN
                old_row := jsonb_set(old_row, ARRAY[redacted_column], '"[redacted]"');
            END IF;
            IF new_row IS NOT NULL AND jsonb_typeof(new_row -> redacted_column) <> 'null' THEN
                new_row := jsonb_set(new_row, ARRAY[redacted_column], '"[redacted]"');
            END IF;
        END LOOP;
    END IF;

    INSERT INTO audit.record_changes (
        table_schema, table_name, operation, record_id, old_values, new_values, changed_columns,
        user_id, actor, request_id, database_user
    ) VALUES (
        TG_TABLE_SCHEMA, TG_TABLE_NAME, TG_OP, COALESCE(new_row ->> 'id', old_row ->> 'id'), old_row, new_row, to_jsonb(changed),
        util.current_user_id(), util.current_actor(), util.current_request_id(), session_user
    );

    RETURN NULL;
END
$$;


--
-- Name: row_hash_of(jsonb); Type: FUNCTION; Schema: audit; Owner: -
--

CREATE FUNCTION audit.row_hash_of(content jsonb) RETURNS character
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$
    SELECT encode(sha256(convert_to((content - 'row_hash' - 'chain_hash' - 'sealed_at')::text, 'UTF8')), 'hex')
$$;


--
-- Name: seal(regclass); Type: FUNCTION; Schema: audit; Owner: -
--

CREATE FUNCTION audit.seal(target regclass) RETURNS bigint
    LANGUAGE plpgsql
    AS $_$
DECLARE
    previous text;
    sealed bigint := 0;
    r record;
BEGIN
    PERFORM set_config('app.audit_maintenance', 'on', true);
    EXECUTE format('SELECT chain_hash FROM %s WHERE chain_hash IS NOT NULL ORDER BY id DESC LIMIT 1', target) INTO previous;

    FOR r IN EXECUTE format('SELECT id, row_hash FROM %s WHERE chain_hash IS NULL ORDER BY id', target) LOOP
        previous := encode(sha256(convert_to(coalesce(previous, '') || r.row_hash, 'UTF8')), 'hex');
        EXECUTE format('UPDATE %s SET chain_hash = $1, sealed_at = now() WHERE id = $2', target) USING previous, r.id;
        sealed := sealed + 1;
    END LOOP;

    RETURN sealed;
END
$_$;


--
-- Name: set_row_hash(); Type: FUNCTION; Schema: audit; Owner: -
--

CREATE FUNCTION audit.set_row_hash() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.chain_hash := NULL;
    NEW.sealed_at := NULL;
    NEW.row_hash := audit.row_hash_of(to_jsonb(NEW));
    RETURN NEW;
END
$$;


--
-- Name: verify_chain(regclass); Type: FUNCTION; Schema: audit; Owner: -
--

CREATE FUNCTION audit.verify_chain(target regclass, OUT checked bigint, OUT sealed bigint, OUT row_mismatches bigint, OUT chain_mismatches bigint, OUT first_bad_id bigint) RETURNS record
    LANGUAGE plpgsql
    AS $$
DECLARE
    previous text := NULL;
    first boolean := true;
    r record;
    expected text;
BEGIN
    checked := 0; sealed := 0; row_mismatches := 0; chain_mismatches := 0; first_bad_id := NULL;

    FOR r IN EXECUTE format('SELECT id, row_hash, chain_hash, audit.row_hash_of(to_jsonb(t)) AS actual FROM %s AS t ORDER BY id', target) LOOP
        checked := checked + 1;

        IF r.actual IS DISTINCT FROM r.row_hash THEN
            row_mismatches := row_mismatches + 1;
            first_bad_id := coalesce(first_bad_id, r.id);
        END IF;

        IF r.chain_hash IS NOT NULL THEN
            sealed := sealed + 1;

            IF NOT first THEN
                expected := encode(sha256(convert_to(coalesce(previous, '') || r.row_hash, 'UTF8')), 'hex');

                IF expected IS DISTINCT FROM r.chain_hash THEN
                    chain_mismatches := chain_mismatches + 1;
                    first_bad_id := coalesce(first_bad_id, r.id);
                END IF;
            END IF;

            previous := r.chain_hash;
            first := false;
        END IF;
    END LOOP;
END
$$;


--
-- Name: additional_program_request_record_ids(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.additional_program_request_record_ids() RETURNS bigint[]
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'pg_catalog', 'pg_temp'
    AS $$
    SELECT COALESCE(array_agg(DISTINCT r.student_record_id), ARRAY[]::bigint[])
    FROM public.additional_program_requests AS r
    WHERE r.status = 'requested'
      AND (
          util.has_permission('additional_programs.approve')
          OR r.org_unit_id = ANY (util.permission_org_unit_ids('additional_programs.approve'))
          OR r.program_id = ANY (util.permission_scope_ids('additional_programs.approve', 'program'))
      )
$$;


--
-- Name: current_actor(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.current_actor() RETURNS text
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT NULLIF(current_setting('app.actor', true), '')
$$;


--
-- Name: current_person_id(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.current_person_id() RETURNS bigint
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT u.person_id FROM public.users AS u WHERE u.id = util.current_user_id()
$$;


--
-- Name: current_request_id(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.current_request_id() RETURNS text
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT NULLIF(current_setting('app.request_id', true), '')
$$;


--
-- Name: current_user_id(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.current_user_id() RETURNS bigint
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT NULLIF(current_setting('app.user_id', true), '')::bigint
$$;


--
-- Name: enable_audit(regclass, text[], text[]); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.enable_audit(target regclass, redacted_columns text[] DEFAULT '{}'::text[], ignored_columns text[] DEFAULT '{}'::text[]) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    table_name text;
    arguments text;
    ignored text;
BEGIN
    SELECT c.relname INTO table_name FROM pg_class AS c WHERE c.oid = target;

    SELECT COALESCE(string_agg(quote_literal(c), ', '), '') INTO arguments FROM unnest(redacted_columns) AS c;

    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', table_name || '_after_write_audit', target);
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', table_name || '_after_update_audit', target);

    IF cardinality(ignored_columns) = 0 THEN
        EXECUTE format(
            'CREATE TRIGGER %I AFTER INSERT OR UPDATE OR DELETE ON %s FOR EACH ROW EXECUTE FUNCTION audit.record_change(%s)',
            table_name || '_after_write_audit', target, arguments
        );
    ELSE
        ignored := quote_literal(ignored_columns::text) || '::text[]';

        EXECUTE format(
            'CREATE TRIGGER %I AFTER INSERT OR DELETE ON %s FOR EACH ROW EXECUTE FUNCTION audit.record_change(%s)',
            table_name || '_after_write_audit', target, arguments
        );
        EXECUTE format(
            'CREATE TRIGGER %I AFTER UPDATE ON %s FOR EACH ROW WHEN ((to_jsonb(OLD) - %s) IS DISTINCT FROM (to_jsonb(NEW) - %s)) EXECUTE FUNCTION audit.record_change(%s)',
            table_name || '_after_update_audit', target, ignored, ignored, arguments
        );
    END IF;

    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', table_name || '_after_truncate_audit', target);
    EXECUTE format(
        'CREATE TRIGGER %I AFTER TRUNCATE ON %s FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change()',
        table_name || '_after_truncate_audit', target
    );
END
$$;


--
-- Name: guard_finalized_grade(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.guard_finalized_grade() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'pg_catalog', 'pg_temp'
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


--
-- Name: has_permission(text); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.has_permission(permission_name text) RETURNS boolean
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.role_assignments AS ra
        JOIN public.users AS u ON u.id = ra.user_id AND u.is_active
        JOIN public.role_has_permissions AS rhp ON rhp.role_id = ra.role_id
        JOIN public.permissions AS p ON p.id = rhp.permission_id
        WHERE ra.user_id = util.current_user_id()
          AND p.name = permission_name
          AND ra.scope_type = 'global'
          AND (ra.starts_at IS NULL OR ra.starts_at <= now())
          AND (ra.ends_at IS NULL OR ra.ends_at > now())
    )
$$;


--
-- Name: i18n(jsonb); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.i18n(value jsonb) RETURNS text
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT util.i18n(
        value,
        COALESCE(NULLIF(current_setting('app.locale', true), ''), 'en'),
        COALESCE(NULLIF(current_setting('app.fallback_locale', true), ''), 'en')
    )
$$;


--
-- Name: i18n(jsonb, text, text); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.i18n(value jsonb, locale text, fallback text DEFAULT 'en'::text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$
    SELECT CASE
        WHEN value IS NULL OR jsonb_typeof(value) <> 'object' THEN NULL
        ELSE COALESCE(
            NULLIF(value ->> locale, ''),
            NULLIF(value ->> split_part(replace(locale, '-', '_'), '_', 1), ''),
            NULLIF(value ->> fallback, ''),
            (SELECT e.v FROM jsonb_each_text(value) AS e(k, v) WHERE e.v <> '' ORDER BY e.k LIMIT 1)
        )
    END
$$;


--
-- Name: i18n_search_text(jsonb); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.i18n_search_text(value jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$
    SELECT COALESCE(string_agg(e.v, ' ' ORDER BY e.k), '')
    FROM jsonb_each_text(CASE WHEN jsonb_typeof(value) = 'object' THEN value ELSE '{}'::jsonb END) AS e(k, v)
$$;


--
-- Name: instructor_meeting_conflict(bigint, bigint, smallint, int4range, daterange); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.instructor_meeting_conflict(instructor bigint, meeting_section bigint, meeting_weekday smallint, meeting_times int4range, meeting_dates daterange) RETURNS bigint
    LANGUAGE sql STABLE
    AS $$
    SELECT other.section_id
    FROM section_meetings AS other
    JOIN section_instructors AS si ON si.section_id = other.section_id
    WHERE si.instructor_id = instructor
      AND other.section_id <> meeting_section
      AND other.is_active
      AND other.weekday = meeting_weekday
      AND other.time_range && meeting_times
      AND other.date_range && meeting_dates
    LIMIT 1
$$;


--
-- Name: is_system_context(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.is_system_context() RETURNS boolean
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT COALESCE(util.current_actor() LIKE 'system:%', false)
$$;


--
-- Name: org_unit_ancestor_ids(bigint); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.org_unit_ancestor_ids(start_id bigint) RETURNS bigint[]
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    WITH RECURSIVE chain (id, parent_id, depth) AS (
        SELECT o.id, o.parent_id, 0 FROM public.org_units AS o WHERE o.id = start_id
        UNION ALL
        SELECT parent.id, parent.parent_id, chain.depth + 1
        FROM public.org_units AS parent JOIN chain ON parent.id = chain.parent_id
        WHERE chain.depth < 100
    )
    SELECT COALESCE(array_agg(chain.id ORDER BY chain.depth), '{}') FROM chain
$$;


--
-- Name: org_unit_descendant_ids(bigint[]); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.org_unit_descendant_ids(root_ids bigint[]) RETURNS bigint[]
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    WITH RECURSIVE tree (id) AS (
        SELECT o.id FROM public.org_units AS o WHERE o.id = ANY (root_ids)
        UNION
        SELECT child.id FROM public.org_units AS child JOIN tree ON child.parent_id = tree.id
    )
    SELECT COALESCE(array_agg(tree.id), '{}') FROM tree
$$;


--
-- Name: org_units_prevent_cycle(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.org_units_prevent_cycle() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.parent_id IS NOT NULL AND NEW.parent_id = ANY (util.org_unit_descendant_ids(ARRAY[NEW.id])) THEN
        RAISE EXCEPTION 'Org unit % cannot be placed under itself or one of its descendants', NEW.id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END
$$;


--
-- Name: permission_org_unit_ids(text); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.permission_org_unit_ids(permission_name text) RETURNS bigint[]
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT util.org_unit_descendant_ids(util.permission_scope_ids(permission_name, 'org_unit'))
$$;


--
-- Name: permission_scope_ids(text, text); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.permission_scope_ids(permission_name text, scope_type text) RETURNS bigint[]
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$
    SELECT COALESCE(array_agg(DISTINCT ra.scope_id), '{}')
    FROM public.role_assignments AS ra
    JOIN public.users AS u ON u.id = ra.user_id AND u.is_active
    JOIN public.role_has_permissions AS rhp ON rhp.role_id = ra.role_id
    JOIN public.permissions AS p ON p.id = rhp.permission_id
    WHERE ra.user_id = util.current_user_id()
      AND p.name = permission_name
      AND ra.scope_type = permission_scope_ids.scope_type
      AND (ra.starts_at IS NULL OR ra.starts_at <= now())
      AND (ra.ends_at IS NULL OR ra.ends_at > now())
$$;


--
-- Name: section_instructors_check_meetings(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.section_instructors_check_meetings() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    meeting record;
    conflicting bigint;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('section_instructor:' || NEW.instructor_id, 0));

    FOR meeting IN SELECT * FROM section_meetings WHERE section_id = NEW.section_id AND is_active LOOP
        conflicting := util.instructor_meeting_conflict(NEW.instructor_id, NEW.section_id, meeting.weekday, meeting.time_range, meeting.date_range);

        IF conflicting IS NOT NULL THEN
            RAISE EXCEPTION 'instructor_conflict instructor=% section=% other_section=%', NEW.instructor_id, NEW.section_id, conflicting
                USING ERRCODE = 'exclusion_violation';
        END IF;
    END LOOP;

    RETURN NEW;
END
$$;


--
-- Name: section_meetings_check_instructors(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.section_meetings_check_instructors() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    instructor bigint;
    conflicting bigint;
BEGIN
    IF NOT NEW.is_active THEN
        RETURN NEW;
    END IF;

    FOR instructor IN SELECT instructor_id FROM section_instructors WHERE section_id = NEW.section_id ORDER BY instructor_id LOOP
        PERFORM pg_advisory_xact_lock(hashtextextended('section_instructor:' || instructor, 0));
        conflicting := util.instructor_meeting_conflict(instructor, NEW.section_id, NEW.weekday, NEW.time_range, NEW.date_range);

        IF conflicting IS NOT NULL THEN
            RAISE EXCEPTION 'instructor_conflict instructor=% section=% other_section=%', instructor, NEW.section_id, conflicting
                USING ERRCODE = 'exclusion_violation';
        END IF;
    END LOOP;

    RETURN NEW;
END
$$;


--
-- Name: sections_sync_meeting_activity(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.sections_sync_meeting_activity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE section_meetings SET is_active = (NEW.status <> 'cancelled') WHERE section_id = NEW.id;

    RETURN NEW;
END
$$;


--
-- Name: student_number_exists(text); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.student_number_exists(candidate text) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'pg_catalog', 'pg_temp'
    AS $$
    SELECT EXISTS (SELECT 1 FROM public.student_records WHERE student_number = candidate)
$$;


--
-- Name: taught_student_record_ids(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.taught_student_record_ids() RETURNS SETOF bigint
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'pg_catalog', 'pg_temp'
    AS $$
    SELECT e.student_record_id
    FROM public.enrollments AS e
    JOIN public.section_instructors AS si ON si.section_id = e.section_id
    JOIN public.instructors AS i ON i.id = si.instructor_id
    WHERE i.person_id = util.current_person_id()
      AND e.status IN ('enrolled', 'completed')
$$;


--
-- Name: term_sessions_within_term(); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.term_sessions_within_term() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    term_start date;
    term_end date;
BEGIN
    SELECT start_date, end_date INTO term_start, term_end FROM terms WHERE id = NEW.term_id;

    IF NEW.start_date < term_start OR NEW.end_date > term_end THEN
        RAISE EXCEPTION 'Term session % (% to %) must lie within its term (% to %)', NEW.code, NEW.start_date, NEW.end_date, term_start, term_end
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END
$$;


--
-- Name: user_id_for_institutional_email(text); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.user_id_for_institutional_email(candidate text) RETURNS bigint
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'pg_catalog', 'pg_temp'
    AS $$
    SELECT u.id
    FROM public.student_records AS sr
    JOIN public.users AS u ON u.person_id = sr.person_id
    WHERE lower(sr.institutional_email) = lower(candidate)
    ORDER BY sr.admission_date DESC
    LIMIT 1
$$;


--
-- Name: user_id_for_student_number(text, boolean); Type: FUNCTION; Schema: util; Owner: -
--

CREATE FUNCTION util.user_id_for_student_number(candidate text, include_ended boolean) RETURNS bigint
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'pg_catalog', 'pg_temp'
    AS $$
    SELECT u.id
    FROM public.student_records AS sr
    JOIN public.users AS u ON u.person_id = sr.person_id
    WHERE sr.student_number = candidate
      AND (include_ended OR sr.status IN ('enrolled', 'on_leave'))
    LIMIT 1
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity_log; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.activity_log (
    id bigint NOT NULL,
    log_name character varying(255),
    description text NOT NULL,
    subject_type character varying(255),
    subject_id bigint,
    event character varying(255),
    causer_type character varying(255),
    causer_id bigint,
    attribute_changes jsonb,
    properties jsonb,
    reason text,
    request_id character varying(255),
    ip_address character varying(45),
    user_agent text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    row_hash character(64),
    chain_hash character(64),
    sealed_at timestamp(0) with time zone
);


--
-- Name: activity_log_id_seq; Type: SEQUENCE; Schema: audit; Owner: -
--

CREATE SEQUENCE audit.activity_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: activity_log_id_seq; Type: SEQUENCE OWNED BY; Schema: audit; Owner: -
--

ALTER SEQUENCE audit.activity_log_id_seq OWNED BY audit.activity_log.id;


--
-- Name: record_changes; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.record_changes (
    id bigint NOT NULL,
    occurred_at timestamp(0) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    transaction_id bigint DEFAULT txid_current() NOT NULL,
    table_schema character varying(255) NOT NULL,
    table_name character varying(255) NOT NULL,
    operation character varying(16) NOT NULL,
    record_id character varying(255),
    old_values jsonb,
    new_values jsonb,
    changed_columns jsonb,
    user_id bigint,
    actor character varying(255),
    request_id character varying(255),
    database_user character varying(255) NOT NULL,
    row_hash character(64),
    chain_hash character(64),
    sealed_at timestamp(0) with time zone
);


--
-- Name: record_changes_id_seq; Type: SEQUENCE; Schema: audit; Owner: -
--

CREATE SEQUENCE audit.record_changes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: record_changes_id_seq; Type: SEQUENCE OWNED BY; Schema: audit; Owner: -
--

ALTER SEQUENCE audit.record_changes_id_seq OWNED BY audit.record_changes.id;


--
-- Name: security_events; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.security_events (
    id bigint NOT NULL,
    occurred_at timestamp(0) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    type character varying(255) NOT NULL,
    user_id bigint,
    identifier character varying(255),
    subject_type character varying(255),
    subject_id bigint,
    properties jsonb,
    request_id character varying(255),
    ip_address character varying(45),
    user_agent text,
    row_hash character(64),
    chain_hash character(64),
    sealed_at timestamp(0) with time zone
);


--
-- Name: security_events_id_seq; Type: SEQUENCE; Schema: audit; Owner: -
--

CREATE SEQUENCE audit.security_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: security_events_id_seq; Type: SEQUENCE OWNED BY; Schema: audit; Owner: -
--

ALTER SEQUENCE audit.security_events_id_seq OWNED BY audit.security_events.id;


--
-- Name: academic_years; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.academic_years (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    year_period daterange GENERATED ALWAYS AS (daterange(start_date, end_date, '[]'::text)) STORED,
    CONSTRAINT academic_years_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT academic_years_year_period_order_check CHECK (((end_date IS NULL) OR (end_date >= start_date)))
);


--
-- Name: academic_years_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.academic_years_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: academic_years_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.academic_years_id_seq OWNED BY public.academic_years.id;


--
-- Name: account_invitations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.account_invitations (
    id bigint NOT NULL,
    person_id bigint NOT NULL,
    email character varying(255) NOT NULL,
    token_hash character(64) NOT NULL,
    expires_at timestamp(0) with time zone NOT NULL,
    accepted_at timestamp(0) with time zone,
    invited_by_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: account_invitations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.account_invitations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: account_invitations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.account_invitations_id_seq OWNED BY public.account_invitations.id;


--
-- Name: additional_program_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.additional_program_requests (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    program_id bigint NOT NULL,
    org_unit_id bigint NOT NULL,
    role character varying(16) NOT NULL,
    term_id bigint NOT NULL,
    status character varying(16) DEFAULT 'requested'::character varying NOT NULL,
    statement text,
    requested_by_id bigint,
    requested_at timestamp(0) with time zone NOT NULL,
    decided_by_id bigint,
    decided_at timestamp(0) with time zone,
    decision_note text,
    student_record_program_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT additional_program_requests_role_check CHECK (((role)::text = ANY ((ARRAY['second_major'::character varying, 'minor'::character varying])::text[]))),
    CONSTRAINT additional_program_requests_status_check CHECK (((status)::text = ANY ((ARRAY['requested'::character varying, 'approved'::character varying, 'rejected'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: additional_program_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.additional_program_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: additional_program_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.additional_program_requests_id_seq OWNED BY public.additional_program_requests.id;


--
-- Name: admission_cycle_document_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admission_cycle_document_types (
    id bigint NOT NULL,
    admission_cycle_id bigint NOT NULL,
    document_type_id bigint NOT NULL,
    is_required boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: admission_cycle_document_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admission_cycle_document_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admission_cycle_document_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admission_cycle_document_types_id_seq OWNED BY public.admission_cycle_document_types.id;


--
-- Name: admission_cycle_programs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admission_cycle_programs (
    id bigint NOT NULL,
    admission_cycle_id bigint NOT NULL,
    program_id bigint NOT NULL,
    capacity integer,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT admission_cycle_programs_capacity_check CHECK (((capacity IS NULL) OR (capacity >= 0)))
);


--
-- Name: admission_cycle_programs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admission_cycle_programs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admission_cycle_programs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admission_cycle_programs_id_seq OWNED BY public.admission_cycle_programs.id;


--
-- Name: admission_cycles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admission_cycles (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name jsonb NOT NULL,
    description jsonb,
    opens_at timestamp(0) with time zone NOT NULL,
    closes_at timestamp(0) with time zone,
    is_published boolean DEFAULT false NOT NULL,
    should_release_decisions_immediately boolean DEFAULT false NOT NULL,
    offer_response_days smallint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT admission_cycles_description_object_check CHECK (((description IS NULL) OR (jsonb_typeof(description) = 'object'::text))),
    CONSTRAINT admission_cycles_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT admission_cycles_period_check CHECK (((closes_at IS NULL) OR (closes_at > opens_at)))
);


--
-- Name: admission_cycles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admission_cycles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admission_cycles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admission_cycles_id_seq OWNED BY public.admission_cycles.id;


--
-- Name: advisor_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.advisor_assignments (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    instructor_id bigint NOT NULL,
    role character varying(32) DEFAULT 'primary'::character varying NOT NULL,
    start_date date NOT NULL,
    end_date date,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT advisor_assignments_period_check CHECK (((end_date IS NULL) OR (end_date >= start_date)))
);


--
-- Name: advisor_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.advisor_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: advisor_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.advisor_assignments_id_seq OWNED BY public.advisor_assignments.id;


--
-- Name: application_number_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.application_number_sequences (
    admission_cycle_id bigint NOT NULL,
    last_value integer DEFAULT 0 NOT NULL
);


--
-- Name: applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.applications (
    id bigint NOT NULL,
    application_number character varying(80),
    admission_cycle_id bigint NOT NULL,
    person_id bigint NOT NULL,
    program_id bigint NOT NULL,
    org_unit_id bigint NOT NULL,
    admission_type_id bigint,
    status character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    previous_school_name character varying(255),
    previous_school_country_id bigint,
    previous_graduation_date date,
    personal_statement text,
    submitted_at timestamp(0) with time zone,
    review_started_at timestamp(0) with time zone,
    decided_by_id bigint,
    decided_at timestamp(0) with time zone,
    decision_note text,
    decision_released_at timestamp(0) with time zone,
    offer_expires_at timestamp(0) with time zone,
    responded_at timestamp(0) with time zone,
    withdrawn_at timestamp(0) with time zone,
    withdrawal_reason text,
    student_record_id bigint,
    matriculated_at timestamp(0) with time zone,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT applications_matriculated_check CHECK (((student_record_id IS NULL) OR ((status)::text = 'confirmed'::text))),
    CONSTRAINT applications_number_check CHECK (((submitted_at IS NULL) = (application_number IS NULL))),
    CONSTRAINT applications_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'submitted'::character varying, 'under_review'::character varying, 'admitted'::character varying, 'rejected'::character varying, 'confirmed'::character varying, 'withdrawn'::character varying, 'expired'::character varying])::text[]))),
    CONSTRAINT applications_submitted_check CHECK ((((status)::text = ANY ((ARRAY['draft'::character varying, 'expired'::character varying, 'withdrawn'::character varying])::text[])) OR (submitted_at IS NOT NULL)))
);


--
-- Name: applications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.applications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: applications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.applications_id_seq OWNED BY public.applications.id;


--
-- Name: assessment_component_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_component_scores (
    id bigint NOT NULL,
    assessment_result_id bigint NOT NULL,
    assessment_component_id bigint NOT NULL,
    score numeric(6,1) NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: assessment_component_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_component_scores_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_component_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_component_scores_id_seq OWNED BY public.assessment_component_scores.id;


--
-- Name: assessment_components; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_components (
    id bigint NOT NULL,
    assessment_type_id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    max_score numeric(6,1) NOT NULL,
    min_score numeric(6,1),
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT assessment_components_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: assessment_components_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_components_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_components_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_components_id_seq OWNED BY public.assessment_components.id;


--
-- Name: assessment_registrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_registrations (
    id bigint NOT NULL,
    assessment_session_id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    status character varying(16) DEFAULT 'registered'::character varying NOT NULL,
    registered_at timestamp(0) with time zone NOT NULL,
    registered_by_id bigint,
    cancelled_at timestamp(0) with time zone,
    cancel_reason text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT assessment_registrations_cancelled_check CHECK ((((status)::text = 'cancelled'::text) = (cancelled_at IS NOT NULL))),
    CONSTRAINT assessment_registrations_status_check CHECK (((status)::text = ANY ((ARRAY['registered'::character varying, 'cancelled'::character varying, 'absent'::character varying])::text[])))
);


--
-- Name: assessment_registrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_registrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_registrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_registrations_id_seq OWNED BY public.assessment_registrations.id;


--
-- Name: assessment_result_corrections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_result_corrections (
    id bigint NOT NULL,
    assessment_result_id bigint NOT NULL,
    proposed jsonb NOT NULL,
    previous jsonb NOT NULL,
    reason text NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    requested_by_id bigint NOT NULL,
    requested_at timestamp(0) with time zone NOT NULL,
    decided_by_id bigint,
    decided_at timestamp(0) with time zone,
    decision_note text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT assessment_result_corrections_decision_check CHECK ((((status)::text = 'pending'::text) = (decided_at IS NULL))),
    CONSTRAINT assessment_result_corrections_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: assessment_result_corrections_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_result_corrections_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_result_corrections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_result_corrections_id_seq OWNED BY public.assessment_result_corrections.id;


--
-- Name: assessment_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_results (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    assessment_type_id bigint NOT NULL,
    assessment_session_id bigint,
    assessment_registration_id bigint,
    source character varying(16) NOT NULL,
    taken_date date NOT NULL,
    total_score numeric(6,1),
    level character varying(32),
    is_passed boolean NOT NULL,
    certificate_number character varying(64),
    note text,
    entered_by_id bigint,
    entered_at timestamp(0) with time zone NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT assessment_results_session_check CHECK (((((source)::text = 'session'::text) = (assessment_session_id IS NOT NULL)) AND (((source)::text = 'session'::text) = (assessment_registration_id IS NOT NULL)))),
    CONSTRAINT assessment_results_source_check CHECK (((source)::text = ANY ((ARRAY['session'::character varying, 'external'::character varying])::text[])))
);


--
-- Name: assessment_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_results_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_results_id_seq OWNED BY public.assessment_results.id;


--
-- Name: assessment_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_sessions (
    id bigint NOT NULL,
    assessment_type_id bigint NOT NULL,
    held_date date NOT NULL,
    venue character varying(120),
    registration_opens_at timestamp(0) with time zone,
    registration_closes_at timestamp(0) with time zone,
    capacity integer,
    pass_score numeric(6,1),
    results_published_at timestamp(0) with time zone,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT assessment_sessions_capacity_check CHECK (((capacity IS NULL) OR (capacity > 0))),
    CONSTRAINT assessment_sessions_registration_check CHECK (((registration_opens_at IS NULL) OR (registration_closes_at IS NULL) OR (registration_opens_at < registration_closes_at)))
);


--
-- Name: assessment_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_sessions_id_seq OWNED BY public.assessment_sessions.id;


--
-- Name: assessment_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assessment_types (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    category character varying(16) DEFAULT 'comprehensive'::character varying NOT NULL,
    scoring character varying(16) DEFAULT 'score'::character varying NOT NULL,
    max_score numeric(6,1),
    pass_score numeric(6,1),
    allows_external boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT assessment_types_category_check CHECK (((category)::text = ANY ((ARRAY['language'::character varying, 'comprehensive'::character varying, 'thesis'::character varying, 'external'::character varying])::text[]))),
    CONSTRAINT assessment_types_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT assessment_types_scoring_check CHECK (((scoring)::text = ANY ((ARRAY['score'::character varying, 'pass_fail'::character varying])::text[])))
);


--
-- Name: assessment_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_types_id_seq OWNED BY public.assessment_types.id;


--
-- Name: attendance_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attendance_records (
    id bigint NOT NULL,
    class_meeting_id bigint NOT NULL,
    enrollment_id bigint NOT NULL,
    status character varying(16) NOT NULL,
    note character varying(200),
    recorded_by_id bigint,
    recorded_at timestamp(0) with time zone NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT attendance_records_status_check CHECK (((status)::text = ANY ((ARRAY['present'::character varying, 'late'::character varying, 'absent'::character varying, 'excused'::character varying])::text[])))
);


--
-- Name: attendance_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.attendance_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: attendance_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.attendance_records_id_seq OWNED BY public.attendance_records.id;


--
-- Name: buildings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.buildings (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    address text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT buildings_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: buildings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.buildings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: buildings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.buildings_id_seq OWNED BY public.buildings.id;


--
-- Name: cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cache (
    key character varying(255) NOT NULL,
    value text NOT NULL,
    expiration bigint NOT NULL
);


--
-- Name: cache_locks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cache_locks (
    key character varying(255) NOT NULL,
    owner character varying(255) NOT NULL,
    expiration bigint NOT NULL
);


--
-- Name: cart_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cart_items (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    term_id bigint NOT NULL,
    section_id bigint NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: cart_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cart_items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cart_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cart_items_id_seq OWNED BY public.cart_items.id;


--
-- Name: certificate_issues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.certificate_issues (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    certificate_type_id bigint NOT NULL,
    locale character varying(8) NOT NULL,
    serial_number character varying(64) NOT NULL,
    verification_code character varying(40) NOT NULL,
    purpose character varying(200),
    copies smallint DEFAULT '1'::smallint NOT NULL,
    status character varying(16) DEFAULT 'issued'::character varying NOT NULL,
    issued_at timestamp(0) with time zone NOT NULL,
    issued_by_id bigint,
    pdf_checksum character varying(64),
    revoked_at timestamp(0) with time zone,
    revoked_by_id bigint,
    revocation_reason text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT certificate_issues_copies_check CHECK (((copies >= 1) AND (copies <= 20))),
    CONSTRAINT certificate_issues_revoked_check CHECK ((((status)::text = 'revoked'::text) = (revoked_at IS NOT NULL))),
    CONSTRAINT certificate_issues_status_check CHECK (((status)::text = ANY ((ARRAY['issued'::character varying, 'revoked'::character varying])::text[])))
);


--
-- Name: certificate_issues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.certificate_issues_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: certificate_issues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.certificate_issues_id_seq OWNED BY public.certificate_issues.id;


--
-- Name: certificate_number_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.certificate_number_sequences (
    prefix character varying(64) NOT NULL,
    last_value bigint DEFAULT '0'::bigint NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: certificate_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.certificate_templates (
    id bigint NOT NULL,
    certificate_type_id bigint NOT NULL,
    locale character varying(8) NOT NULL,
    title character varying(160) NOT NULL,
    body text NOT NULL,
    footer text,
    signer character varying(160),
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: certificate_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.certificate_templates_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: certificate_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.certificate_templates_id_seq OWNED BY public.certificate_templates.id;


--
-- Name: certificate_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.certificate_types (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    audience character varying(16) DEFAULT 'any'::character varying NOT NULL,
    has_grades boolean DEFAULT false NOT NULL,
    has_photo boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT certificate_types_audience_check CHECK (((audience)::text = ANY ((ARRAY['any'::character varying, 'enrolled'::character varying, 'graduated'::character varying])::text[]))),
    CONSTRAINT certificate_types_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: certificate_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.certificate_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: certificate_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.certificate_types_id_seq OWNED BY public.certificate_types.id;


--
-- Name: class_meetings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.class_meetings (
    id bigint NOT NULL,
    section_id bigint NOT NULL,
    section_meeting_id bigint,
    meeting_date date NOT NULL,
    start_time time(0) without time zone NOT NULL,
    end_time time(0) without time zone NOT NULL,
    room_id bigint,
    status character varying(16) DEFAULT 'scheduled'::character varying NOT NULL,
    topic character varying(200),
    cancel_reason text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT class_meetings_cancel_check CHECK ((((status)::text = 'cancelled'::text) = (cancel_reason IS NOT NULL))),
    CONSTRAINT class_meetings_status_check CHECK (((status)::text = ANY ((ARRAY['scheduled'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT class_meetings_time_check CHECK ((start_time < end_time))
);


--
-- Name: class_meetings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.class_meetings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: class_meetings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.class_meetings_id_seq OWNED BY public.class_meetings.id;


--
-- Name: countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.countries (
    id bigint NOT NULL,
    code character(2) NOT NULL,
    alpha3_code character(3) NOT NULL,
    numeric_code character(3),
    name jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT countries_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: countries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.countries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: countries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.countries_id_seq OWNED BY public.countries.id;


--
-- Name: course_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_categories (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    parent_id bigint,
    sort_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT course_categories_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT course_categories_not_own_parent_check CHECK (((parent_id IS NULL) OR (parent_id <> id)))
);


--
-- Name: course_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_categories_id_seq OWNED BY public.course_categories.id;


--
-- Name: course_equivalencies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_equivalencies (
    id bigint NOT NULL,
    course_id bigint NOT NULL,
    equivalent_course_id bigint NOT NULL,
    is_mutual boolean DEFAULT true NOT NULL,
    effective_start_date date NOT NULL,
    effective_end_date date,
    note jsonb,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    effective_period daterange GENERATED ALWAYS AS (daterange(effective_start_date, effective_end_date, '[]'::text)) STORED,
    CONSTRAINT course_equivalencies_distinct_check CHECK ((course_id <> equivalent_course_id)),
    CONSTRAINT course_equivalencies_effective_period_order_check CHECK (((effective_end_date IS NULL) OR (effective_end_date >= effective_start_date))),
    CONSTRAINT course_equivalencies_note_object_check CHECK (((note IS NULL) OR (jsonb_typeof(note) = 'object'::text)))
);


--
-- Name: course_equivalencies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_equivalencies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_equivalencies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_equivalencies_id_seq OWNED BY public.course_equivalencies.id;


--
-- Name: course_requisites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_requisites (
    id bigint NOT NULL,
    course_version_id bigint NOT NULL,
    kind character varying(16) NOT NULL,
    group_number smallint DEFAULT '1'::smallint NOT NULL,
    required_course_id bigint NOT NULL,
    minimum_grade character varying(8),
    allows_concurrent boolean DEFAULT false NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT course_requisites_group_check CHECK ((group_number >= 1)),
    CONSTRAINT course_requisites_kind_check CHECK (((kind)::text = ANY ((ARRAY['prerequisite'::character varying, 'corequisite'::character varying])::text[])))
);


--
-- Name: course_requisites_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_requisites_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_requisites_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_requisites_id_seq OWNED BY public.course_requisites.id;


--
-- Name: course_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_versions (
    id bigint NOT NULL,
    course_id bigint NOT NULL,
    effective_start_date date NOT NULL,
    effective_end_date date,
    title jsonb NOT NULL,
    description jsonb,
    credits numeric(4,1) NOT NULL,
    lecture_hours numeric(4,1) DEFAULT '0'::numeric NOT NULL,
    lab_hours numeric(4,1) DEFAULT '0'::numeric NOT NULL,
    course_category_id bigint,
    grading_basis character varying(16) DEFAULT 'graded'::character varying NOT NULL,
    counts_toward_credit_limit boolean DEFAULT true NOT NULL,
    is_repeatable boolean DEFAULT false NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    effective_period daterange GENERATED ALWAYS AS (daterange(effective_start_date, effective_end_date, '[]'::text)) STORED,
    requires_evaluation boolean DEFAULT true NOT NULL,
    CONSTRAINT course_versions_credits_check CHECK (((credits >= (0)::numeric) AND (lecture_hours >= (0)::numeric) AND (lab_hours >= (0)::numeric))),
    CONSTRAINT course_versions_description_object_check CHECK (((description IS NULL) OR (jsonb_typeof(description) = 'object'::text))),
    CONSTRAINT course_versions_effective_period_order_check CHECK (((effective_end_date IS NULL) OR (effective_end_date >= effective_start_date))),
    CONSTRAINT course_versions_grading_basis_check CHECK (((grading_basis)::text = ANY ((ARRAY['graded'::character varying, 'pass_fail'::character varying])::text[]))),
    CONSTRAINT course_versions_title_object_check CHECK ((jsonb_typeof(title) = 'object'::text))
);


--
-- Name: course_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_versions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_versions_id_seq OWNED BY public.course_versions.id;


--
-- Name: courses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.courses (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    org_unit_id bigint NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: courses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.courses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: courses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.courses_id_seq OWNED BY public.courses.id;


--
-- Name: credit_limit_policies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credit_limit_policies (
    id bigint NOT NULL,
    name jsonb NOT NULL,
    term_type_id bigint,
    eligibility jsonb,
    min_credits numeric(4,1),
    max_credits numeric(4,1) NOT NULL,
    priority integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT credit_limit_policies_credits_check CHECK (((max_credits >= (0)::numeric) AND ((min_credits IS NULL) OR (min_credits <= max_credits)))),
    CONSTRAINT credit_limit_policies_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: credit_limit_policies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.credit_limit_policies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: credit_limit_policies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.credit_limit_policies_id_seq OWNED BY public.credit_limit_policies.id;


--
-- Name: curriculum_requirement_courses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.curriculum_requirement_courses (
    id bigint NOT NULL,
    curriculum_requirement_id bigint CONSTRAINT curriculum_requirement_cours_curriculum_requirement_id_not_null NOT NULL,
    course_id bigint NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: curriculum_requirement_courses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.curriculum_requirement_courses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: curriculum_requirement_courses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.curriculum_requirement_courses_id_seq OWNED BY public.curriculum_requirement_courses.id;


--
-- Name: curriculum_requirement_sets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.curriculum_requirement_sets (
    id bigint NOT NULL,
    program_id bigint NOT NULL,
    program_role character varying(16) NOT NULL,
    catalog_year_from smallint NOT NULL,
    catalog_year_to smallint,
    name jsonb NOT NULL,
    total_credits numeric(5,1),
    note jsonb,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    catalog_years int4range GENERATED ALWAYS AS (int4range((catalog_year_from)::integer, (catalog_year_to)::integer, '[]'::text)) STORED,
    CONSTRAINT curriculum_requirement_sets_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT curriculum_requirement_sets_note_object_check CHECK (((note IS NULL) OR (jsonb_typeof(note) = 'object'::text))),
    CONSTRAINT curriculum_requirement_sets_role_check CHECK (((program_role)::text = ANY ((ARRAY['primary'::character varying, 'second_major'::character varying, 'minor'::character varying])::text[]))),
    CONSTRAINT curriculum_requirement_sets_years_check CHECK (((catalog_year_to IS NULL) OR (catalog_year_to >= catalog_year_from)))
);


--
-- Name: curriculum_requirement_sets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.curriculum_requirement_sets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: curriculum_requirement_sets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.curriculum_requirement_sets_id_seq OWNED BY public.curriculum_requirement_sets.id;


--
-- Name: curriculum_requirements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.curriculum_requirements (
    id bigint NOT NULL,
    curriculum_requirement_set_id bigint NOT NULL,
    kind character varying(32) NOT NULL,
    name jsonb,
    course_category_id bigint,
    min_credits numeric(5,1),
    min_courses smallint,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    assessment_type_id bigint,
    CONSTRAINT curriculum_requirements_kind_check CHECK (((((kind)::text = 'category_credits'::text) AND (course_category_id IS NOT NULL) AND (min_credits IS NOT NULL) AND (assessment_type_id IS NULL)) OR (((kind)::text = 'required_courses'::text) AND (course_category_id IS NULL) AND (assessment_type_id IS NULL)) OR (((kind)::text = 'course_group'::text) AND (course_category_id IS NULL) AND (assessment_type_id IS NULL) AND ((min_credits IS NOT NULL) OR (min_courses IS NOT NULL))) OR (((kind)::text = 'assessment_pass'::text) AND (assessment_type_id IS NOT NULL) AND (course_category_id IS NULL) AND (min_credits IS NULL) AND (min_courses IS NULL)))),
    CONSTRAINT curriculum_requirements_name_object_check CHECK (((name IS NULL) OR (jsonb_typeof(name) = 'object'::text)))
);


--
-- Name: curriculum_requirements_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.curriculum_requirements_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: curriculum_requirements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.curriculum_requirements_id_seq OWNED BY public.curriculum_requirements.id;


--
-- Name: degree_audits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.degree_audits (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    curriculum_requirement_set_id bigint,
    program_role character varying(16) NOT NULL,
    program_id bigint NOT NULL,
    term_id bigint,
    is_satisfied boolean NOT NULL,
    earned_credits numeric(5,1) NOT NULL,
    required_credits numeric(5,1),
    cumulative_gpa numeric(4,2),
    result jsonb NOT NULL,
    audited_at timestamp(0) with time zone NOT NULL,
    audited_by_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT degree_audits_role_check CHECK (((program_role)::text = ANY ((ARRAY['primary'::character varying, 'second_major'::character varying, 'minor'::character varying])::text[])))
);


--
-- Name: degree_audits_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.degree_audits_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: degree_audits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.degree_audits_id_seq OWNED BY public.degree_audits.id;


--
-- Name: degree_number_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.degree_number_sequences (
    prefix character varying(64) NOT NULL,
    last_value bigint DEFAULT '0'::bigint NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: degree_requirement_waivers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.degree_requirement_waivers (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    curriculum_requirement_id bigint NOT NULL,
    reason text NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    requested_by_id bigint,
    requested_at timestamp(0) with time zone NOT NULL,
    decided_by_id bigint,
    decided_at timestamp(0) with time zone,
    decision_note text,
    lifted_by_id bigint,
    lifted_at timestamp(0) with time zone,
    lift_reason text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT degree_requirement_waivers_decision_check CHECK ((((status)::text = 'pending'::text) = (decided_at IS NULL))),
    CONSTRAINT degree_requirement_waivers_lift_check CHECK ((((status)::text = 'lifted'::text) = (lifted_at IS NOT NULL))),
    CONSTRAINT degree_requirement_waivers_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying, 'lifted'::character varying])::text[])))
);


--
-- Name: degree_requirement_waivers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.degree_requirement_waivers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: degree_requirement_waivers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.degree_requirement_waivers_id_seq OWNED BY public.degree_requirement_waivers.id;


--
-- Name: enrollments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollments (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    section_id bigint NOT NULL,
    term_id bigint NOT NULL,
    course_id bigint NOT NULL,
    course_version_id bigint NOT NULL,
    credits numeric(4,1) NOT NULL,
    course_category_id bigint,
    counts_toward_credit_limit boolean DEFAULT true NOT NULL,
    status character varying(16) DEFAULT 'enrolled'::character varying NOT NULL,
    seat_group_id bigint,
    is_retake boolean DEFAULT false NOT NULL,
    repeats_enrollment_id bigint,
    source character varying(16) DEFAULT 'student'::character varying NOT NULL,
    enrolled_at timestamp(0) with time zone NOT NULL,
    dropped_at timestamp(0) with time zone,
    withdrawn_at timestamp(0) with time zone,
    changed_by_id bigint,
    grade_status character varying(16) DEFAULT 'none'::character varying NOT NULL,
    grade_code character varying(8),
    is_passed boolean,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    grade_scale_id bigint,
    score numeric(5,2),
    grade_points numeric(4,2),
    counts_in_gpa boolean,
    grade_entered_at timestamp(0) with time zone,
    grade_entered_by_id bigint,
    grade_submitted_at timestamp(0) with time zone,
    grade_submitted_by_id bigint,
    grade_finalized_at timestamp(0) with time zone,
    grade_finalized_by_id bigint,
    CONSTRAINT enrollments_finalized_check CHECK ((((grade_status)::text = 'finalized'::text) = ((status)::text = 'completed'::text))),
    CONSTRAINT enrollments_grade_check CHECK (((((grade_status)::text = 'none'::text) AND (grade_code IS NULL)) OR ((grade_status)::text = 'draft'::text) OR (((grade_status)::text = ANY ((ARRAY['submitted'::character varying, 'finalized'::character varying])::text[])) AND (grade_code IS NOT NULL) AND (grade_scale_id IS NOT NULL)))),
    CONSTRAINT enrollments_grade_status_check CHECK (((grade_status)::text = ANY ((ARRAY['none'::character varying, 'draft'::character varying, 'submitted'::character varying, 'finalized'::character varying])::text[]))),
    CONSTRAINT enrollments_score_check CHECK (((score IS NULL) OR ((score >= (0)::numeric) AND (score <= (100)::numeric)))),
    CONSTRAINT enrollments_source_check CHECK (((source)::text = ANY ((ARRAY['student'::character varying, 'staff'::character varying, 'waitlist'::character varying, 'import'::character varying])::text[]))),
    CONSTRAINT enrollments_status_check CHECK (((status)::text = ANY ((ARRAY['enrolled'::character varying, 'dropped'::character varying, 'withdrawn'::character varying, 'completed'::character varying])::text[])))
);


--
-- Name: enrollments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.enrollments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: enrollments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.enrollments_id_seq OWNED BY public.enrollments.id;


--
-- Name: evaluation_answers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_answers (
    evaluation_response_id uuid NOT NULL,
    evaluation_question_id bigint NOT NULL,
    value smallint,
    comment text,
    CONSTRAINT evaluation_answers_value_check CHECK ((((value IS NULL) OR ((value >= 1) AND (value <= 10))) AND ((value IS NOT NULL) OR (comment IS NOT NULL))))
);


--
-- Name: evaluation_completions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_completions (
    id bigint NOT NULL,
    enrollment_id bigint NOT NULL,
    completed_at timestamp(0) with time zone NOT NULL
);


--
-- Name: evaluation_completions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evaluation_completions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evaluation_completions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evaluation_completions_id_seq OWNED BY public.evaluation_completions.id;


--
-- Name: evaluation_forms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_forms (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    description jsonb,
    scale_points smallint DEFAULT '5'::smallint NOT NULL,
    scale_low_label jsonb,
    scale_high_label jsonb,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT evaluation_forms_description_object_check CHECK (((description IS NULL) OR (jsonb_typeof(description) = 'object'::text))),
    CONSTRAINT evaluation_forms_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT evaluation_forms_scale_high_label_object_check CHECK (((scale_high_label IS NULL) OR (jsonb_typeof(scale_high_label) = 'object'::text))),
    CONSTRAINT evaluation_forms_scale_low_label_object_check CHECK (((scale_low_label IS NULL) OR (jsonb_typeof(scale_low_label) = 'object'::text))),
    CONSTRAINT evaluation_forms_scale_points_check CHECK (((scale_points >= 2) AND (scale_points <= 10)))
);


--
-- Name: evaluation_forms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evaluation_forms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evaluation_forms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evaluation_forms_id_seq OWNED BY public.evaluation_forms.id;


--
-- Name: evaluation_method_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_method_requests (
    id bigint NOT NULL,
    section_id bigint NOT NULL,
    requested_method character varying(16) NOT NULL,
    reason text NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    requested_by_id bigint NOT NULL,
    requested_at timestamp(0) with time zone NOT NULL,
    decided_by_id bigint,
    decided_at timestamp(0) with time zone,
    decision_note text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT evaluation_method_requests_decision_check CHECK ((((status)::text = 'pending'::text) = (decided_at IS NULL))),
    CONSTRAINT evaluation_method_requests_method_check CHECK (((requested_method)::text = ANY ((ARRAY['absolute'::character varying, 'relative'::character varying])::text[]))),
    CONSTRAINT evaluation_method_requests_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: evaluation_method_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evaluation_method_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evaluation_method_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evaluation_method_requests_id_seq OWNED BY public.evaluation_method_requests.id;


--
-- Name: evaluation_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_questions (
    id bigint NOT NULL,
    evaluation_form_id bigint NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    category jsonb,
    text jsonb NOT NULL,
    question_type character varying(16) DEFAULT 'scale'::character varying NOT NULL,
    is_required boolean DEFAULT true NOT NULL,
    is_reversed boolean DEFAULT false NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT evaluation_questions_category_object_check CHECK (((category IS NULL) OR (jsonb_typeof(category) = 'object'::text))),
    CONSTRAINT evaluation_questions_text_object_check CHECK ((jsonb_typeof(text) = 'object'::text)),
    CONSTRAINT evaluation_questions_type_check CHECK (((question_type)::text = ANY ((ARRAY['scale'::character varying, 'text'::character varying])::text[])))
);


--
-- Name: evaluation_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evaluation_questions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evaluation_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evaluation_questions_id_seq OWNED BY public.evaluation_questions.id;


--
-- Name: evaluation_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_responses (
    id uuid NOT NULL,
    term_id bigint NOT NULL,
    section_id bigint NOT NULL,
    evaluation_form_id bigint NOT NULL
);


--
-- Name: exports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exports (
    id bigint NOT NULL,
    completed_at timestamp(0) with time zone,
    file_disk character varying(255) NOT NULL,
    file_name character varying(255),
    exporter character varying(255) NOT NULL,
    processed_rows integer DEFAULT 0 NOT NULL,
    total_rows integer NOT NULL,
    successful_rows integer DEFAULT 0 NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: exports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.exports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.exports_id_seq OWNED BY public.exports.id;


--
-- Name: failed_import_rows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.failed_import_rows (
    id bigint NOT NULL,
    data jsonb NOT NULL,
    import_id bigint NOT NULL,
    validation_error text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: failed_import_rows_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.failed_import_rows_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: failed_import_rows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.failed_import_rows_id_seq OWNED BY public.failed_import_rows.id;


--
-- Name: failed_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.failed_jobs (
    id bigint NOT NULL,
    uuid character varying(255) NOT NULL,
    connection character varying(255) NOT NULL,
    queue character varying(255) NOT NULL,
    payload text NOT NULL,
    exception text NOT NULL,
    failed_at timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: failed_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.failed_jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: failed_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.failed_jobs_id_seq OWNED BY public.failed_jobs.id;


--
-- Name: features; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.features (
    id bigint NOT NULL,
    name character varying(255) NOT NULL,
    scope character varying(255) NOT NULL,
    value text NOT NULL,
    created_at timestamp(0) without time zone,
    updated_at timestamp(0) without time zone
);


--
-- Name: features_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.features_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: features_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.features_id_seq OWNED BY public.features.id;


--
-- Name: grade_change_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grade_change_requests (
    id bigint NOT NULL,
    enrollment_id bigint NOT NULL,
    from_grade_code character varying(8),
    to_grade_code character varying(8) NOT NULL,
    to_score numeric(5,2),
    reason text NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    requested_by_id bigint NOT NULL,
    requested_at timestamp(0) with time zone NOT NULL,
    decided_by_id bigint,
    decided_at timestamp(0) with time zone,
    decision_note text,
    applied_at timestamp(0) with time zone,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT grade_change_requests_applied_check CHECK (((applied_at IS NULL) OR ((status)::text = 'approved'::text))),
    CONSTRAINT grade_change_requests_decision_check CHECK ((((status)::text = 'pending'::text) = (decided_at IS NULL))),
    CONSTRAINT grade_change_requests_score_check CHECK (((to_score IS NULL) OR ((to_score >= (0)::numeric) AND (to_score <= (100)::numeric)))),
    CONSTRAINT grade_change_requests_second_person_check CHECK (((decided_by_id IS NULL) OR (decided_by_id <> requested_by_id))),
    CONSTRAINT grade_change_requests_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: grade_change_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grade_change_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grade_change_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grade_change_requests_id_seq OWNED BY public.grade_change_requests.id;


--
-- Name: grade_scale_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grade_scale_items (
    id bigint NOT NULL,
    grade_scale_id bigint NOT NULL,
    code character varying(16) NOT NULL,
    name jsonb,
    grade_points numeric(4,2),
    min_percentage numeric(5,2),
    max_percentage numeric(5,2),
    counts_in_gpa boolean DEFAULT true NOT NULL,
    is_passing boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    applies_to character varying(16) DEFAULT 'graded'::character varying NOT NULL,
    CONSTRAINT grade_scale_items_applies_to_check CHECK (((applies_to)::text = ANY ((ARRAY['graded'::character varying, 'pass_fail'::character varying, 'both'::character varying])::text[]))),
    CONSTRAINT grade_scale_items_gpa_points_check CHECK (((NOT counts_in_gpa) OR (grade_points IS NOT NULL))),
    CONSTRAINT grade_scale_items_name_object_check CHECK (((name IS NULL) OR (jsonb_typeof(name) = 'object'::text))),
    CONSTRAINT grade_scale_items_percentage_check CHECK ((((min_percentage IS NULL) OR ((min_percentage >= (0)::numeric) AND (min_percentage <= (100)::numeric))) AND ((max_percentage IS NULL) OR ((max_percentage >= (0)::numeric) AND (max_percentage <= (100)::numeric))) AND ((min_percentage IS NULL) OR (max_percentage IS NULL) OR (min_percentage <= max_percentage)))),
    CONSTRAINT grade_scale_items_points_check CHECK (((grade_points IS NULL) OR (grade_points >= (0)::numeric)))
);


--
-- Name: grade_scale_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grade_scale_items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grade_scale_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grade_scale_items_id_seq OWNED BY public.grade_scale_items.id;


--
-- Name: grade_scales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grade_scales (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    max_grade_points numeric(4,2) NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT grade_scales_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: grade_scales_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grade_scales_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grade_scales_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grade_scales_id_seq OWNED BY public.grade_scales.id;


--
-- Name: guardians; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.guardians (
    id bigint NOT NULL,
    person_id bigint NOT NULL,
    relationship character varying(32) NOT NULL,
    full_name character varying(255) NOT NULL,
    phone character varying(32),
    email character varying(255),
    address text,
    is_primary_contact boolean DEFAULT false NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: guardians_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.guardians_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: guardians_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.guardians_id_seq OWNED BY public.guardians.id;


--
-- Name: imports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.imports (
    id bigint NOT NULL,
    completed_at timestamp(0) with time zone,
    file_name character varying(255) NOT NULL,
    file_path character varying(255) NOT NULL,
    importer character varying(255) NOT NULL,
    processed_rows integer DEFAULT 0 NOT NULL,
    total_rows integer NOT NULL,
    successful_rows integer DEFAULT 0 NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: imports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.imports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: imports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.imports_id_seq OWNED BY public.imports.id;


--
-- Name: instructors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instructors (
    id bigint NOT NULL,
    person_id bigint NOT NULL,
    employee_number character varying(32) NOT NULL,
    org_unit_id bigint NOT NULL,
    employment_type character varying(32) NOT NULL,
    academic_title jsonb,
    hire_date date,
    end_date date,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT instructors_academic_title_object_check CHECK (((academic_title IS NULL) OR (jsonb_typeof(academic_title) = 'object'::text))),
    CONSTRAINT instructors_period_check CHECK (((end_date IS NULL) OR (hire_date IS NULL) OR (end_date >= hire_date)))
);


--
-- Name: instructors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instructors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instructors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instructors_id_seq OWNED BY public.instructors.id;


--
-- Name: job_batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_batches (
    id character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    total_jobs integer NOT NULL,
    pending_jobs integer NOT NULL,
    failed_jobs integer NOT NULL,
    failed_job_ids text NOT NULL,
    options text,
    cancelled_at integer,
    created_at integer NOT NULL,
    finished_at integer
);


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jobs (
    id bigint NOT NULL,
    queue character varying(255) NOT NULL,
    payload text NOT NULL,
    attempts smallint NOT NULL,
    reserved_at integer,
    available_at integer NOT NULL,
    created_at integer NOT NULL
);


--
-- Name: jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.jobs_id_seq OWNED BY public.jobs.id;


--
-- Name: languages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.languages (
    id bigint NOT NULL,
    code character varying(3) NOT NULL,
    alpha3_code character(3),
    name jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT languages_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: languages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.languages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: languages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.languages_id_seq OWNED BY public.languages.id;


--
-- Name: lms_course_links; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lms_course_links (
    id bigint NOT NULL,
    lms_platform_id bigint NOT NULL,
    section_id bigint NOT NULL,
    external_course_id character varying(128),
    external_url character varying(512),
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    last_synced_at timestamp(0) with time zone,
    last_error text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT lms_course_links_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'linked'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: lms_course_links_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lms_course_links_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lms_course_links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lms_course_links_id_seq OWNED BY public.lms_course_links.id;


--
-- Name: lms_platforms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lms_platforms (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    driver character varying(32) DEFAULT 'null'::character varying NOT NULL,
    base_url character varying(255),
    credentials text,
    options jsonb NOT NULL,
    is_active boolean DEFAULT false NOT NULL,
    should_sync_enrollments boolean DEFAULT true NOT NULL,
    should_pull_grades boolean DEFAULT false NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT lms_platforms_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: lms_platforms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lms_platforms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lms_platforms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lms_platforms_id_seq OWNED BY public.lms_platforms.id;


--
-- Name: lms_sync_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lms_sync_logs (
    id bigint NOT NULL,
    lms_platform_id bigint NOT NULL,
    section_id bigint,
    enrollment_id bigint,
    user_id bigint,
    operation character varying(32) NOT NULL,
    status character varying(16) NOT NULL,
    message text,
    payload jsonb,
    started_at timestamp(0) with time zone NOT NULL,
    finished_at timestamp(0) with time zone,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT lms_sync_logs_status_check CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'succeeded'::character varying, 'failed'::character varying, 'skipped'::character varying])::text[])))
);


--
-- Name: lms_sync_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lms_sync_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lms_sync_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lms_sync_logs_id_seq OWNED BY public.lms_sync_logs.id;


--
-- Name: lms_user_links; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lms_user_links (
    id bigint NOT NULL,
    lms_platform_id bigint NOT NULL,
    user_id bigint NOT NULL,
    external_user_id character varying(128) NOT NULL,
    last_synced_at timestamp(0) with time zone,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: lms_user_links_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lms_user_links_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lms_user_links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lms_user_links_id_seq OWNED BY public.lms_user_links.id;


--
-- Name: lookup_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lookup_types (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name jsonb NOT NULL,
    description jsonb,
    is_system boolean DEFAULT false NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT lookup_types_description_object_check CHECK (((description IS NULL) OR (jsonb_typeof(description) = 'object'::text))),
    CONSTRAINT lookup_types_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: lookup_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lookup_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lookup_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lookup_types_id_seq OWNED BY public.lookup_types.id;


--
-- Name: lookup_values; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lookup_values (
    id bigint NOT NULL,
    lookup_type_id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name jsonb NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT lookup_values_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: lookup_values_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lookup_values_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lookup_values_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lookup_values_id_seq OWNED BY public.lookup_values.id;


--
-- Name: media; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.media (
    id bigint NOT NULL,
    model_type character varying(255) NOT NULL,
    model_id bigint NOT NULL,
    uuid uuid,
    collection_name character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    file_name character varying(255) NOT NULL,
    mime_type character varying(255),
    disk character varying(255) NOT NULL,
    conversions_disk character varying(255),
    size bigint NOT NULL,
    manipulations json NOT NULL,
    custom_properties json NOT NULL,
    generated_conversions json NOT NULL,
    responsive_images json NOT NULL,
    order_column integer,
    created_at timestamp(0) without time zone,
    updated_at timestamp(0) without time zone
);


--
-- Name: media_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.media_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: media_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.media_id_seq OWNED BY public.media.id;


--
-- Name: migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.migrations (
    id integer NOT NULL,
    migration character varying(255) NOT NULL,
    batch integer NOT NULL
);


--
-- Name: migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.migrations_id_seq OWNED BY public.migrations.id;


--
-- Name: model_has_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_has_permissions (
    permission_id bigint NOT NULL,
    model_type character varying(255) NOT NULL,
    model_id bigint NOT NULL
);


--
-- Name: model_has_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_has_roles (
    role_id bigint NOT NULL,
    model_type character varying(255) NOT NULL,
    model_id bigint NOT NULL
);


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id uuid NOT NULL,
    type character varying(255) NOT NULL,
    notifiable_type character varying(255) NOT NULL,
    notifiable_id bigint NOT NULL,
    data text NOT NULL,
    read_at timestamp(0) with time zone,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: org_unit_successions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_unit_successions (
    id bigint NOT NULL,
    predecessor_org_unit_id bigint NOT NULL,
    successor_org_unit_id bigint NOT NULL,
    change_type character varying(32) NOT NULL,
    effective_date date NOT NULL,
    reason text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT org_unit_successions_distinct_check CHECK ((predecessor_org_unit_id <> successor_org_unit_id))
);


--
-- Name: org_unit_successions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.org_unit_successions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: org_unit_successions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.org_unit_successions_id_seq OWNED BY public.org_unit_successions.id;


--
-- Name: org_unit_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_unit_types (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name jsonb NOT NULL,
    is_academic boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT org_unit_types_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: org_unit_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.org_unit_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: org_unit_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.org_unit_types_id_seq OWNED BY public.org_unit_types.id;


--
-- Name: org_units; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.org_units (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name jsonb NOT NULL,
    short_name jsonb,
    org_unit_type_id bigint NOT NULL,
    parent_id bigint,
    effective_start_date date NOT NULL,
    effective_end_date date,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    effective_period daterange GENERATED ALWAYS AS (daterange(effective_start_date, effective_end_date, '[]'::text)) STORED,
    CONSTRAINT org_units_effective_period_order_check CHECK (((effective_end_date IS NULL) OR (effective_end_date >= effective_start_date))),
    CONSTRAINT org_units_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT org_units_not_own_parent_check CHECK (((parent_id IS NULL) OR (parent_id <> id))),
    CONSTRAINT org_units_short_name_object_check CHECK (((short_name IS NULL) OR (jsonb_typeof(short_name) = 'object'::text)))
);


--
-- Name: org_units_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.org_units_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: org_units_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.org_units_id_seq OWNED BY public.org_units.id;


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_tokens (
    email character varying(255) NOT NULL,
    token character varying(255) NOT NULL,
    created_at timestamp(0) with time zone
);


--
-- Name: people; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.people (
    id bigint NOT NULL,
    family_name character varying(255) NOT NULL,
    given_name character varying(255),
    name_variants jsonb,
    birth_date date,
    gender character varying(16),
    nationality_country_id bigint,
    ethnicity_id bigint,
    email character varying(255),
    phone character varying(32),
    address text,
    postal_code character varying(16),
    national_id_encrypted text,
    national_id_hash character(64),
    passport_number_encrypted text,
    passport_number_hash character(64),
    merged_into_person_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    created_by_id bigint DEFAULT util.current_user_id(),
    CONSTRAINT people_name_variants_object_check CHECK (((name_variants IS NULL) OR (jsonb_typeof(name_variants) = 'object'::text))),
    CONSTRAINT people_not_merged_into_self_check CHECK (((merged_into_person_id IS NULL) OR (merged_into_person_id <> id)))
);


--
-- Name: people_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.people_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: people_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.people_id_seq OWNED BY public.people.id;


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    id bigint NOT NULL,
    name character varying(255) NOT NULL,
    guard_name character varying(255) NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: programs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.programs (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name jsonb NOT NULL,
    degree_title jsonb,
    degree_level character varying(32) NOT NULL,
    org_unit_id bigint NOT NULL,
    standard_duration_years numeric(3,1),
    effective_start_date date NOT NULL,
    effective_end_date date,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    effective_period daterange GENERATED ALWAYS AS (daterange(effective_start_date, effective_end_date, '[]'::text)) STORED,
    allows_second_major boolean DEFAULT false NOT NULL,
    allows_minor boolean DEFAULT false NOT NULL,
    CONSTRAINT programs_degree_title_object_check CHECK (((degree_title IS NULL) OR (jsonb_typeof(degree_title) = 'object'::text))),
    CONSTRAINT programs_effective_period_order_check CHECK (((effective_end_date IS NULL) OR (effective_end_date >= effective_start_date))),
    CONSTRAINT programs_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: programs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.programs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: programs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.programs_id_seq OWNED BY public.programs.id;


--
-- Name: registration_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.registration_attempts (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    term_id bigint,
    section_id bigint,
    action character varying(16) NOT NULL,
    outcome character varying(16) NOT NULL,
    results jsonb NOT NULL,
    actor_id bigint,
    request_id character varying(255),
    attempted_at timestamp(0) with time zone NOT NULL,
    CONSTRAINT registration_attempts_action_check CHECK (((action)::text = ANY ((ARRAY['enroll'::character varying, 'drop'::character varying, 'withdraw'::character varying, 'waitlist'::character varying, 'promote'::character varying, 'cart'::character varying])::text[]))),
    CONSTRAINT registration_attempts_outcome_check CHECK (((outcome)::text = ANY ((ARRAY['succeeded'::character varying, 'waitlisted'::character varying, 'refused'::character varying])::text[])))
);


--
-- Name: registration_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.registration_attempts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: registration_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.registration_attempts_id_seq OWNED BY public.registration_attempts.id;


--
-- Name: registration_holds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.registration_holds (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    hold_type character varying(32) NOT NULL,
    blocks_registration boolean DEFAULT true NOT NULL,
    blocks_grades boolean DEFAULT false NOT NULL,
    blocks_certificates boolean DEFAULT false NOT NULL,
    starts_at timestamp(0) with time zone NOT NULL,
    ends_at timestamp(0) with time zone,
    reason text NOT NULL,
    source character varying(16) DEFAULT 'manual'::character varying NOT NULL,
    created_by_id bigint,
    released_at timestamp(0) with time zone,
    released_by_id bigint,
    release_reason text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT registration_holds_period_check CHECK (((ends_at IS NULL) OR (ends_at > starts_at))),
    CONSTRAINT registration_holds_source_check CHECK (((source)::text = ANY ((ARRAY['manual'::character varying, 'import'::character varying, 'system'::character varying])::text[]))),
    CONSTRAINT registration_holds_type_check CHECK (((hold_type)::text = ANY ((ARRAY['unregistered'::character varying, 'financial'::character varying, 'academic'::character varying, 'administrative'::character varying, 'other'::character varying])::text[])))
);


--
-- Name: registration_holds_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.registration_holds_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: registration_holds_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.registration_holds_id_seq OWNED BY public.registration_holds.id;


--
-- Name: registration_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.registration_overrides (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    term_id bigint NOT NULL,
    rule_code character varying(64) NOT NULL,
    section_id bigint,
    course_id bigint,
    reason text NOT NULL,
    expires_at timestamp(0) with time zone,
    granted_by_id bigint,
    revoked_at timestamp(0) with time zone,
    revoked_by_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: registration_overrides_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.registration_overrides_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: registration_overrides_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.registration_overrides_id_seq OWNED BY public.registration_overrides.id;


--
-- Name: registration_rule_sets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.registration_rule_sets (
    id bigint NOT NULL,
    term_id bigint NOT NULL,
    copied_from_rule_set_id bigint,
    note text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: registration_rule_sets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.registration_rule_sets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: registration_rule_sets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.registration_rule_sets_id_seq OWNED BY public.registration_rule_sets.id;


--
-- Name: registration_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.registration_rules (
    id bigint NOT NULL,
    registration_rule_set_id bigint NOT NULL,
    rule_code character varying(64) NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    severity character varying(8) DEFAULT 'block'::character varying NOT NULL,
    allows_override boolean DEFAULT true NOT NULL,
    parameters jsonb,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT registration_rules_parameters_check CHECK (((parameters IS NULL) OR (jsonb_typeof(parameters) = 'object'::text))),
    CONSTRAINT registration_rules_severity_check CHECK (((severity)::text = ANY ((ARRAY['block'::character varying, 'warn'::character varying])::text[])))
);


--
-- Name: registration_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.registration_rules_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: registration_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.registration_rules_id_seq OWNED BY public.registration_rules.id;


--
-- Name: role_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_assignments (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    role_id bigint NOT NULL,
    scope_type character varying(32) NOT NULL,
    scope_id bigint,
    starts_at timestamp(0) with time zone,
    ends_at timestamp(0) with time zone,
    reason text,
    assigned_by_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT role_assignments_period_check CHECK (((starts_at IS NULL) OR (ends_at IS NULL) OR (starts_at < ends_at))),
    CONSTRAINT role_assignments_scope_check CHECK ((((scope_type)::text = 'global'::text) = (scope_id IS NULL)))
);


--
-- Name: role_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.role_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: role_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.role_assignments_id_seq OWNED BY public.role_assignments.id;


--
-- Name: role_has_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_has_permissions (
    permission_id bigint NOT NULL,
    role_id bigint NOT NULL
);


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id bigint NOT NULL,
    name character varying(255) NOT NULL,
    guard_name character varying(255) NOT NULL,
    display_name jsonb NOT NULL,
    description jsonb,
    persona character varying(255),
    is_system boolean DEFAULT false NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT roles_display_name_object_check CHECK ((jsonb_typeof(display_name) = 'object'::text))
);


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: rooms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rooms (
    id bigint NOT NULL,
    building_id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb,
    room_type_id bigint,
    org_unit_id bigint,
    capacity integer,
    is_schedulable boolean DEFAULT true NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    note text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT rooms_capacity_check CHECK (((capacity IS NULL) OR (capacity >= 0))),
    CONSTRAINT rooms_name_object_check CHECK (((name IS NULL) OR (jsonb_typeof(name) = 'object'::text)))
);


--
-- Name: rooms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rooms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rooms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rooms_id_seq OWNED BY public.rooms.id;


--
-- Name: section_instructors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.section_instructors (
    id bigint NOT NULL,
    section_id bigint NOT NULL,
    instructor_id bigint NOT NULL,
    role character varying(16) DEFAULT 'primary'::character varying NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT section_instructors_role_check CHECK (((role)::text = ANY ((ARRAY['primary'::character varying, 'co_instructor'::character varying, 'assistant'::character varying])::text[])))
);


--
-- Name: section_instructors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.section_instructors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: section_instructors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.section_instructors_id_seq OWNED BY public.section_instructors.id;


--
-- Name: section_meetings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.section_meetings (
    id bigint NOT NULL,
    section_id bigint NOT NULL,
    weekday smallint NOT NULL,
    start_time time(0) without time zone NOT NULL,
    end_time time(0) without time zone NOT NULL,
    room_id bigint,
    start_date date NOT NULL,
    end_date date NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    time_range int4range GENERATED ALWAYS AS (int4range((((EXTRACT(hour FROM start_time) * (60)::numeric) + EXTRACT(minute FROM start_time)))::integer, (((EXTRACT(hour FROM end_time) * (60)::numeric) + EXTRACT(minute FROM end_time)))::integer)) STORED,
    date_range daterange GENERATED ALWAYS AS (daterange(start_date, end_date, '[]'::text)) STORED,
    CONSTRAINT section_meetings_date_check CHECK ((end_date >= start_date)),
    CONSTRAINT section_meetings_time_check CHECK ((end_time > start_time)),
    CONSTRAINT section_meetings_weekday_check CHECK (((weekday >= 1) AND (weekday <= 7)))
);


--
-- Name: section_meetings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.section_meetings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: section_meetings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.section_meetings_id_seq OWNED BY public.section_meetings.id;


--
-- Name: section_seat_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.section_seat_groups (
    id bigint NOT NULL,
    section_id bigint NOT NULL,
    name jsonb NOT NULL,
    capacity integer NOT NULL,
    eligibility jsonb,
    releases_at timestamp(0) with time zone,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    enrolled_count integer DEFAULT 0 NOT NULL,
    release_processed_at timestamp(0) with time zone,
    CONSTRAINT section_seat_groups_capacity_check CHECK ((capacity >= 0)),
    CONSTRAINT section_seat_groups_enrolled_count_check CHECK (((enrolled_count >= 0) AND (enrolled_count <= capacity))),
    CONSTRAINT section_seat_groups_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: section_seat_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.section_seat_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: section_seat_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.section_seat_groups_id_seq OWNED BY public.section_seat_groups.id;


--
-- Name: sections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sections (
    id bigint NOT NULL,
    term_id bigint NOT NULL,
    term_session_id bigint NOT NULL,
    course_id bigint NOT NULL,
    course_version_id bigint NOT NULL,
    section_code character varying(16) NOT NULL,
    org_unit_id bigint NOT NULL,
    capacity integer NOT NULL,
    status character varying(16) DEFAULT 'draft'::character varying NOT NULL,
    eligibility jsonb,
    exclusion jsonb,
    instruction_language character varying(16),
    note jsonb,
    copied_from_section_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    enrolled_count integer DEFAULT 0 NOT NULL,
    waitlist_capacity integer DEFAULT 0 NOT NULL,
    evaluation_method character varying(16) DEFAULT 'absolute'::character varying NOT NULL,
    grade_exception_reason text,
    grade_exception_by_id bigint,
    grade_exception_at timestamp(0) with time zone,
    CONSTRAINT sections_capacity_check CHECK ((capacity >= 0)),
    CONSTRAINT sections_enrolled_count_check CHECK (((enrolled_count >= 0) AND (enrolled_count <= capacity))),
    CONSTRAINT sections_evaluation_method_check CHECK (((evaluation_method)::text = ANY ((ARRAY['absolute'::character varying, 'relative'::character varying])::text[]))),
    CONSTRAINT sections_grade_exception_check CHECK (((grade_exception_reason IS NULL) = (grade_exception_at IS NULL))),
    CONSTRAINT sections_note_object_check CHECK (((note IS NULL) OR (jsonb_typeof(note) = 'object'::text))),
    CONSTRAINT sections_status_check CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT sections_waitlist_capacity_check CHECK ((waitlist_capacity >= 0))
);


--
-- Name: sections_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sections_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sections_id_seq OWNED BY public.sections.id;


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sessions (
    id character varying(255) NOT NULL,
    user_id bigint,
    ip_address character varying(45),
    user_agent text,
    payload text NOT NULL,
    last_activity integer NOT NULL
);


--
-- Name: settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.settings (
    id bigint NOT NULL,
    "group" character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    locked boolean DEFAULT false NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.settings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.settings_id_seq OWNED BY public.settings.id;


--
-- Name: student_number_sequences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_number_sequences (
    prefix character varying(64) NOT NULL,
    last_value bigint DEFAULT '0'::bigint NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: student_record_programs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_record_programs (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    program_id bigint NOT NULL,
    role character varying(32) NOT NULL,
    start_date date NOT NULL,
    end_date date,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT student_record_programs_period_check CHECK (((end_date IS NULL) OR (end_date >= start_date))),
    CONSTRAINT student_record_programs_role_check CHECK (((role)::text = ANY ((ARRAY['second_major'::character varying, 'minor'::character varying])::text[])))
);


--
-- Name: student_record_programs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_record_programs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_record_programs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_record_programs_id_seq OWNED BY public.student_record_programs.id;


--
-- Name: student_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_records (
    id bigint NOT NULL,
    person_id bigint NOT NULL,
    student_number character varying(32) NOT NULL,
    program_id bigint NOT NULL,
    org_unit_id bigint NOT NULL,
    admission_term_id bigint,
    admission_type_id bigint,
    admission_date date NOT NULL,
    catalog_year smallint NOT NULL,
    year_level smallint DEFAULT '1'::smallint NOT NULL,
    status character varying(32) DEFAULT 'enrolled'::character varying NOT NULL,
    status_changed_at timestamp(0) with time zone,
    academic_standing character varying(32),
    graduation_date date,
    degree_number character varying(64),
    institutional_email character varying(255),
    tags jsonb,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT student_records_graduation_check CHECK ((((status)::text <> 'graduated'::text) OR (graduation_date IS NOT NULL))),
    CONSTRAINT student_records_tags_array_check CHECK (((tags IS NULL) OR (jsonb_typeof(tags) = 'array'::text))),
    CONSTRAINT student_records_year_level_check CHECK (((year_level >= 1) AND (year_level <= 10)))
);


--
-- Name: student_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_records_id_seq OWNED BY public.student_records.id;


--
-- Name: student_status_change_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_status_change_types (
    id bigint NOT NULL,
    code character varying(64) NOT NULL,
    name jsonb NOT NULL,
    to_status character varying(32) NOT NULL,
    from_statuses jsonb NOT NULL,
    can_student_request boolean DEFAULT false NOT NULL,
    is_system boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT student_status_change_types_from_statuses_array_check CHECK ((jsonb_typeof(from_statuses) = 'array'::text)),
    CONSTRAINT student_status_change_types_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: student_status_change_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_status_change_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_status_change_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_status_change_types_id_seq OWNED BY public.student_status_change_types.id;


--
-- Name: student_status_changes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_status_changes (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    status_change_type_id bigint NOT NULL,
    from_status character varying(32) NOT NULL,
    to_status character varying(32) NOT NULL,
    effective_date date NOT NULL,
    term_id bigint,
    reason text NOT NULL,
    status character varying(32) DEFAULT 'requested'::character varying NOT NULL,
    requested_by_id bigint,
    requested_at timestamp(0) with time zone NOT NULL,
    decided_by_id bigint,
    decided_at timestamp(0) with time zone,
    decision_note text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: student_status_changes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_status_changes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_status_changes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_status_changes_id_seq OWNED BY public.student_status_changes.id;


--
-- Name: syllabi; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.syllabi (
    id bigint NOT NULL,
    section_id bigint NOT NULL,
    language character varying(16) NOT NULL,
    content jsonb NOT NULL,
    published_at timestamp(0) with time zone,
    updated_by_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT syllabi_content_object_check CHECK ((jsonb_typeof(content) = 'object'::text))
);


--
-- Name: syllabi_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.syllabi_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: syllabi_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.syllabi_id_seq OWNED BY public.syllabi.id;


--
-- Name: term_evaluations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.term_evaluations (
    id bigint NOT NULL,
    term_id bigint NOT NULL,
    evaluation_form_id bigint NOT NULL,
    minimum_responses integer DEFAULT 5 NOT NULL,
    minimum_response_percent integer DEFAULT 25 NOT NULL,
    results_published_at timestamp(0) with time zone,
    published_by_id bigint,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT term_evaluations_minimum_check CHECK (((minimum_responses >= 0) AND ((minimum_response_percent >= 0) AND (minimum_response_percent <= 100))))
);


--
-- Name: term_evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.term_evaluations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: term_evaluations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.term_evaluations_id_seq OWNED BY public.term_evaluations.id;


--
-- Name: term_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.term_records (
    id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    term_id bigint NOT NULL,
    attempted_credits numeric(5,1) DEFAULT '0'::numeric NOT NULL,
    earned_credits numeric(5,1) DEFAULT '0'::numeric NOT NULL,
    gpa_credits numeric(5,1) DEFAULT '0'::numeric NOT NULL,
    grade_points_total numeric(8,2) DEFAULT '0'::numeric NOT NULL,
    term_gpa numeric,
    cumulative_attempted_credits numeric(6,1) DEFAULT '0'::numeric NOT NULL,
    cumulative_earned_credits numeric(6,1) DEFAULT '0'::numeric NOT NULL,
    cumulative_gpa_credits numeric(6,1) DEFAULT '0'::numeric NOT NULL,
    cumulative_grade_points_total numeric(9,2) DEFAULT '0'::numeric NOT NULL,
    cumulative_gpa numeric,
    academic_standing character varying(32),
    warning_count integer DEFAULT 0 NOT NULL,
    is_honors boolean DEFAULT false NOT NULL,
    honors_rank integer,
    calculated_at timestamp(0) with time zone NOT NULL,
    closed_at timestamp(0) with time zone,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT term_records_credits_check CHECK (((earned_credits <= attempted_credits) AND (gpa_credits <= attempted_credits))),
    CONSTRAINT term_records_gpa_check CHECK ((((term_gpa IS NULL) OR ((term_gpa >= (0)::numeric) AND (term_gpa <= (10)::numeric))) AND ((cumulative_gpa IS NULL) OR ((cumulative_gpa >= (0)::numeric) AND (cumulative_gpa <= (10)::numeric))))),
    CONSTRAINT term_records_standing_check CHECK (((academic_standing IS NULL) OR ((academic_standing)::text = ANY ((ARRAY['good'::character varying, 'warning'::character varying, 'dismissal_review'::character varying])::text[]))))
);


--
-- Name: term_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.term_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: term_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.term_records_id_seq OWNED BY public.term_records.id;


--
-- Name: term_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.term_sessions (
    id bigint NOT NULL,
    term_id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    is_full_term boolean DEFAULT false NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT term_sessions_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT term_sessions_order_check CHECK ((end_date >= start_date))
);


--
-- Name: term_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.term_sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: term_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.term_sessions_id_seq OWNED BY public.term_sessions.id;


--
-- Name: term_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.term_types (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    is_regular boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT term_types_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: term_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.term_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: term_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.term_types_id_seq OWNED BY public.term_types.id;


--
-- Name: term_windows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.term_windows (
    id bigint NOT NULL,
    term_id bigint NOT NULL,
    window_type character varying(64) NOT NULL,
    name jsonb,
    opens_at timestamp(0) with time zone NOT NULL,
    closes_at timestamp(0) with time zone NOT NULL,
    eligibility jsonb,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    term_session_id bigint,
    CONSTRAINT term_windows_name_object_check CHECK (((name IS NULL) OR (jsonb_typeof(name) = 'object'::text))),
    CONSTRAINT term_windows_order_check CHECK ((closes_at > opens_at)),
    CONSTRAINT term_windows_session_check CHECK ((((window_type)::text = ANY ((ARRAY['add_drop'::character varying, 'withdrawal'::character varying, 'grade_entry'::character varying, 'grade_appeal'::character varying, 'course_evaluation'::character varying])::text[])) = (term_session_id IS NOT NULL)))
);


--
-- Name: term_windows_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.term_windows_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: term_windows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.term_windows_id_seq OWNED BY public.term_windows.id;


--
-- Name: terms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.terms (
    id bigint NOT NULL,
    academic_year_id bigint NOT NULL,
    term_type_id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    status character varying(32) DEFAULT 'planned'::character varying NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    instruction_period daterange GENERATED ALWAYS AS (daterange(start_date, end_date, '[]'::text)) STORED,
    CONSTRAINT terms_instruction_period_order_check CHECK (((end_date IS NULL) OR (end_date >= start_date))),
    CONSTRAINT terms_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text))
);


--
-- Name: terms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.terms_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: terms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.terms_id_seq OWNED BY public.terms.id;


--
-- Name: time_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.time_slots (
    id bigint NOT NULL,
    code character varying(32) NOT NULL,
    name jsonb NOT NULL,
    start_time time(0) without time zone NOT NULL,
    end_time time(0) without time zone NOT NULL,
    weekdays jsonb NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT time_slots_name_object_check CHECK ((jsonb_typeof(name) = 'object'::text)),
    CONSTRAINT time_slots_order_check CHECK ((end_time > start_time)),
    CONSTRAINT time_slots_weekdays_array_check CHECK ((jsonb_typeof(weekdays) = 'array'::text))
);


--
-- Name: time_slots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.time_slots_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: time_slots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.time_slots_id_seq OWNED BY public.time_slots.id;


--
-- Name: user_identities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_identities (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    provider character varying(64) NOT NULL,
    subject character varying(255) NOT NULL,
    email character varying(255),
    linked_at timestamp(0) with time zone NOT NULL,
    last_used_at timestamp(0) with time zone,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone
);


--
-- Name: user_identities_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_identities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_identities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_identities_id_seq OWNED BY public.user_identities.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    name character varying(255),
    email character varying(255) NOT NULL,
    email_verified_at timestamp(0) with time zone,
    password character varying(255) NOT NULL,
    two_factor_secret text,
    two_factor_recovery_codes text,
    two_factor_confirmed_at timestamp(0) with time zone,
    email_mfa_enabled_at timestamp(0) with time zone,
    mfa_grace_started_at timestamp(0) with time zone,
    locale character varying(20),
    is_active boolean DEFAULT true NOT NULL,
    last_login_at timestamp(0) with time zone,
    remember_token character varying(100),
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    person_id bigint,
    failed_login_count integer DEFAULT 0 NOT NULL,
    locked_until timestamp(0) with time zone
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: waitlist_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.waitlist_entries (
    id bigint NOT NULL,
    section_id bigint NOT NULL,
    student_record_id bigint NOT NULL,
    status character varying(16) DEFAULT 'waiting'::character varying NOT NULL,
    requested_at timestamp(0) with time zone NOT NULL,
    requested_by_id bigint,
    resolved_at timestamp(0) with time zone,
    enrollment_id bigint,
    outcome_note text,
    created_at timestamp(0) with time zone,
    updated_at timestamp(0) with time zone,
    CONSTRAINT waitlist_entries_status_check CHECK (((status)::text = ANY ((ARRAY['waiting'::character varying, 'promoted'::character varying, 'removed'::character varying, 'expired'::character varying])::text[])))
);


--
-- Name: waitlist_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.waitlist_entries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: waitlist_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.waitlist_entries_id_seq OWNED BY public.waitlist_entries.id;


--
-- Name: course_grades; Type: VIEW; Schema: reporting; Owner: -
--

CREATE VIEW reporting.course_grades WITH (security_invoker='true') AS
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
   FROM ((((((public.enrollments e
     JOIN public.student_records sr ON ((sr.id = e.student_record_id)))
     JOIN public.terms t ON ((t.id = e.term_id)))
     JOIN public.courses c ON ((c.id = e.course_id)))
     JOIN public.course_versions cv ON ((cv.id = e.course_version_id)))
     JOIN public.sections s ON ((s.id = e.section_id)))
     LEFT JOIN public.course_categories cc ON ((cc.id = e.course_category_id)));


--
-- Name: degree_audits; Type: VIEW; Schema: reporting; Owner: -
--

CREATE VIEW reporting.degree_audits WITH (security_invoker='true') AS
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
   FROM (((public.degree_audits da
     JOIN public.student_records sr ON ((sr.id = da.student_record_id)))
     JOIN public.programs pr ON ((pr.id = da.program_id)))
     LEFT JOIN public.terms t ON ((t.id = da.term_id)))
  WHERE (da.id IN ( SELECT max(degree_audits.id) AS max
           FROM public.degree_audits
          GROUP BY degree_audits.student_record_id, degree_audits.program_role));


--
-- Name: headcount; Type: VIEW; Schema: reporting; Owner: -
--

CREATE VIEW reporting.headcount WITH (security_invoker='true') AS
 SELECT ou.id AS org_unit_id,
    ou.code AS org_unit_code,
    util.i18n(ou.name) AS org_unit_name,
    pr.id AS program_id,
    pr.code AS program_code,
    util.i18n(pr.name) AS program_name,
    sr.year_level,
    sr.status,
    count(*) AS students
   FROM ((public.student_records sr
     JOIN public.programs pr ON ((pr.id = sr.program_id)))
     JOIN public.org_units ou ON ((ou.id = sr.org_unit_id)))
  GROUP BY ou.id, ou.code, ou.name, pr.id, pr.code, pr.name, sr.year_level, sr.status;


--
-- Name: section_enrollments; Type: VIEW; Schema: reporting; Owner: -
--

CREATE VIEW reporting.section_enrollments WITH (security_invoker='true') AS
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
    ( SELECT count(*) AS count
           FROM public.enrollments e
          WHERE ((e.section_id = s.id) AND ((e.status)::text = ANY ((ARRAY['enrolled'::character varying, 'completed'::character varying])::text[])))) AS enrolled,
    ( SELECT count(*) AS count
           FROM public.waitlist_entries w
          WHERE ((w.section_id = s.id) AND ((w.status)::text = 'waiting'::text))) AS waiting,
    ( SELECT string_agg(COALESCE(util.i18n(ip.name_variants), ((ip.family_name)::text || COALESCE((' '::text || (ip.given_name)::text), ''::text))), ', '::text ORDER BY si.role) AS string_agg
           FROM ((public.section_instructors si
             JOIN public.instructors i ON ((i.id = si.instructor_id)))
             JOIN public.people ip ON ((ip.id = i.person_id)))
          WHERE (si.section_id = s.id)) AS instructors
   FROM ((((public.sections s
     JOIN public.terms t ON ((t.id = s.term_id)))
     JOIN public.courses c ON ((c.id = s.course_id)))
     JOIN public.course_versions cv ON ((cv.id = s.course_version_id)))
     JOIN public.org_units ou ON ((ou.id = s.org_unit_id)));


--
-- Name: section_meetings; Type: VIEW; Schema: reporting; Owner: -
--

CREATE VIEW reporting.section_meetings WITH (security_invoker='true') AS
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
   FROM ((((((public.section_meetings m
     JOIN public.sections s ON ((s.id = m.section_id)))
     JOIN public.terms t ON ((t.id = s.term_id)))
     JOIN public.courses c ON ((c.id = s.course_id)))
     JOIN public.course_versions cv ON ((cv.id = s.course_version_id)))
     LEFT JOIN public.rooms r ON ((r.id = m.room_id)))
     LEFT JOIN public.buildings b ON ((b.id = r.building_id)));


--
-- Name: status_changes; Type: VIEW; Schema: reporting; Owner: -
--

CREATE VIEW reporting.status_changes WITH (security_invoker='true') AS
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
   FROM (((public.student_status_changes sc
     JOIN public.student_records sr ON ((sr.id = sc.student_record_id)))
     JOIN public.student_status_change_types sct ON ((sct.id = sc.status_change_type_id)))
     LEFT JOIN public.terms t ON ((t.id = sc.term_id)));


--
-- Name: students; Type: VIEW; Schema: reporting; Owner: -
--

CREATE VIEW reporting.students WITH (security_invoker='true') AS
 SELECT sr.id AS student_record_id,
    sr.student_number,
    sr.person_id,
    COALESCE(util.i18n(p.name_variants), ((p.family_name)::text || COALESCE((' '::text || (p.given_name)::text), ''::text))) AS student_name,
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
   FROM (((public.student_records sr
     JOIN public.people p ON ((p.id = sr.person_id)))
     JOIN public.programs pr ON ((pr.id = sr.program_id)))
     JOIN public.org_units ou ON ((ou.id = sr.org_unit_id)));


--
-- Name: term_records; Type: VIEW; Schema: reporting; Owner: -
--

CREATE VIEW reporting.term_records WITH (security_invoker='true') AS
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
   FROM ((public.term_records tr
     JOIN public.student_records sr ON ((sr.id = tr.student_record_id)))
     JOIN public.terms t ON ((t.id = tr.term_id)));


--
-- Name: activity_log id; Type: DEFAULT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.activity_log ALTER COLUMN id SET DEFAULT nextval('audit.activity_log_id_seq'::regclass);


--
-- Name: record_changes id; Type: DEFAULT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.record_changes ALTER COLUMN id SET DEFAULT nextval('audit.record_changes_id_seq'::regclass);


--
-- Name: security_events id; Type: DEFAULT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.security_events ALTER COLUMN id SET DEFAULT nextval('audit.security_events_id_seq'::regclass);


--
-- Name: academic_years id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_years ALTER COLUMN id SET DEFAULT nextval('public.academic_years_id_seq'::regclass);


--
-- Name: account_invitations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_invitations ALTER COLUMN id SET DEFAULT nextval('public.account_invitations_id_seq'::regclass);


--
-- Name: additional_program_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests ALTER COLUMN id SET DEFAULT nextval('public.additional_program_requests_id_seq'::regclass);


--
-- Name: admission_cycle_document_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_document_types ALTER COLUMN id SET DEFAULT nextval('public.admission_cycle_document_types_id_seq'::regclass);


--
-- Name: admission_cycle_programs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_programs ALTER COLUMN id SET DEFAULT nextval('public.admission_cycle_programs_id_seq'::regclass);


--
-- Name: admission_cycles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycles ALTER COLUMN id SET DEFAULT nextval('public.admission_cycles_id_seq'::regclass);


--
-- Name: advisor_assignments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.advisor_assignments ALTER COLUMN id SET DEFAULT nextval('public.advisor_assignments_id_seq'::regclass);


--
-- Name: applications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications ALTER COLUMN id SET DEFAULT nextval('public.applications_id_seq'::regclass);


--
-- Name: assessment_component_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_component_scores ALTER COLUMN id SET DEFAULT nextval('public.assessment_component_scores_id_seq'::regclass);


--
-- Name: assessment_components id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_components ALTER COLUMN id SET DEFAULT nextval('public.assessment_components_id_seq'::regclass);


--
-- Name: assessment_registrations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_registrations ALTER COLUMN id SET DEFAULT nextval('public.assessment_registrations_id_seq'::regclass);


--
-- Name: assessment_result_corrections id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_result_corrections ALTER COLUMN id SET DEFAULT nextval('public.assessment_result_corrections_id_seq'::regclass);


--
-- Name: assessment_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results ALTER COLUMN id SET DEFAULT nextval('public.assessment_results_id_seq'::regclass);


--
-- Name: assessment_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_sessions ALTER COLUMN id SET DEFAULT nextval('public.assessment_sessions_id_seq'::regclass);


--
-- Name: assessment_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_types ALTER COLUMN id SET DEFAULT nextval('public.assessment_types_id_seq'::regclass);


--
-- Name: attendance_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records ALTER COLUMN id SET DEFAULT nextval('public.attendance_records_id_seq'::regclass);


--
-- Name: buildings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.buildings ALTER COLUMN id SET DEFAULT nextval('public.buildings_id_seq'::regclass);


--
-- Name: cart_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items ALTER COLUMN id SET DEFAULT nextval('public.cart_items_id_seq'::regclass);


--
-- Name: certificate_issues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_issues ALTER COLUMN id SET DEFAULT nextval('public.certificate_issues_id_seq'::regclass);


--
-- Name: certificate_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_templates ALTER COLUMN id SET DEFAULT nextval('public.certificate_templates_id_seq'::regclass);


--
-- Name: certificate_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_types ALTER COLUMN id SET DEFAULT nextval('public.certificate_types_id_seq'::regclass);


--
-- Name: class_meetings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.class_meetings ALTER COLUMN id SET DEFAULT nextval('public.class_meetings_id_seq'::regclass);


--
-- Name: countries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.countries ALTER COLUMN id SET DEFAULT nextval('public.countries_id_seq'::regclass);


--
-- Name: course_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_categories ALTER COLUMN id SET DEFAULT nextval('public.course_categories_id_seq'::regclass);


--
-- Name: course_equivalencies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_equivalencies ALTER COLUMN id SET DEFAULT nextval('public.course_equivalencies_id_seq'::regclass);


--
-- Name: course_requisites id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_requisites ALTER COLUMN id SET DEFAULT nextval('public.course_requisites_id_seq'::regclass);


--
-- Name: course_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_versions ALTER COLUMN id SET DEFAULT nextval('public.course_versions_id_seq'::regclass);


--
-- Name: courses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses ALTER COLUMN id SET DEFAULT nextval('public.courses_id_seq'::regclass);


--
-- Name: credit_limit_policies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_limit_policies ALTER COLUMN id SET DEFAULT nextval('public.credit_limit_policies_id_seq'::regclass);


--
-- Name: curriculum_requirement_courses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_courses ALTER COLUMN id SET DEFAULT nextval('public.curriculum_requirement_courses_id_seq'::regclass);


--
-- Name: curriculum_requirement_sets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_sets ALTER COLUMN id SET DEFAULT nextval('public.curriculum_requirement_sets_id_seq'::regclass);


--
-- Name: curriculum_requirements id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirements ALTER COLUMN id SET DEFAULT nextval('public.curriculum_requirements_id_seq'::regclass);


--
-- Name: degree_audits id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_audits ALTER COLUMN id SET DEFAULT nextval('public.degree_audits_id_seq'::regclass);


--
-- Name: degree_requirement_waivers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_requirement_waivers ALTER COLUMN id SET DEFAULT nextval('public.degree_requirement_waivers_id_seq'::regclass);


--
-- Name: enrollments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments ALTER COLUMN id SET DEFAULT nextval('public.enrollments_id_seq'::regclass);


--
-- Name: evaluation_completions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_completions ALTER COLUMN id SET DEFAULT nextval('public.evaluation_completions_id_seq'::regclass);


--
-- Name: evaluation_forms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_forms ALTER COLUMN id SET DEFAULT nextval('public.evaluation_forms_id_seq'::regclass);


--
-- Name: evaluation_method_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_method_requests ALTER COLUMN id SET DEFAULT nextval('public.evaluation_method_requests_id_seq'::regclass);


--
-- Name: evaluation_questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_questions ALTER COLUMN id SET DEFAULT nextval('public.evaluation_questions_id_seq'::regclass);


--
-- Name: exports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exports ALTER COLUMN id SET DEFAULT nextval('public.exports_id_seq'::regclass);


--
-- Name: failed_import_rows id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_import_rows ALTER COLUMN id SET DEFAULT nextval('public.failed_import_rows_id_seq'::regclass);


--
-- Name: failed_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_jobs ALTER COLUMN id SET DEFAULT nextval('public.failed_jobs_id_seq'::regclass);


--
-- Name: features id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.features ALTER COLUMN id SET DEFAULT nextval('public.features_id_seq'::regclass);


--
-- Name: grade_change_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_change_requests ALTER COLUMN id SET DEFAULT nextval('public.grade_change_requests_id_seq'::regclass);


--
-- Name: grade_scale_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_scale_items ALTER COLUMN id SET DEFAULT nextval('public.grade_scale_items_id_seq'::regclass);


--
-- Name: grade_scales id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_scales ALTER COLUMN id SET DEFAULT nextval('public.grade_scales_id_seq'::regclass);


--
-- Name: guardians id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.guardians ALTER COLUMN id SET DEFAULT nextval('public.guardians_id_seq'::regclass);


--
-- Name: imports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.imports ALTER COLUMN id SET DEFAULT nextval('public.imports_id_seq'::regclass);


--
-- Name: instructors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instructors ALTER COLUMN id SET DEFAULT nextval('public.instructors_id_seq'::regclass);


--
-- Name: jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs ALTER COLUMN id SET DEFAULT nextval('public.jobs_id_seq'::regclass);


--
-- Name: languages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.languages ALTER COLUMN id SET DEFAULT nextval('public.languages_id_seq'::regclass);


--
-- Name: lms_course_links id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_course_links ALTER COLUMN id SET DEFAULT nextval('public.lms_course_links_id_seq'::regclass);


--
-- Name: lms_platforms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_platforms ALTER COLUMN id SET DEFAULT nextval('public.lms_platforms_id_seq'::regclass);


--
-- Name: lms_sync_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_sync_logs ALTER COLUMN id SET DEFAULT nextval('public.lms_sync_logs_id_seq'::regclass);


--
-- Name: lms_user_links id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_user_links ALTER COLUMN id SET DEFAULT nextval('public.lms_user_links_id_seq'::regclass);


--
-- Name: lookup_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lookup_types ALTER COLUMN id SET DEFAULT nextval('public.lookup_types_id_seq'::regclass);


--
-- Name: lookup_values id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lookup_values ALTER COLUMN id SET DEFAULT nextval('public.lookup_values_id_seq'::regclass);


--
-- Name: media id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media ALTER COLUMN id SET DEFAULT nextval('public.media_id_seq'::regclass);


--
-- Name: migrations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.migrations ALTER COLUMN id SET DEFAULT nextval('public.migrations_id_seq'::regclass);


--
-- Name: org_unit_successions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_unit_successions ALTER COLUMN id SET DEFAULT nextval('public.org_unit_successions_id_seq'::regclass);


--
-- Name: org_unit_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_unit_types ALTER COLUMN id SET DEFAULT nextval('public.org_unit_types_id_seq'::regclass);


--
-- Name: org_units id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_units ALTER COLUMN id SET DEFAULT nextval('public.org_units_id_seq'::regclass);


--
-- Name: people id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people ALTER COLUMN id SET DEFAULT nextval('public.people_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: programs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs ALTER COLUMN id SET DEFAULT nextval('public.programs_id_seq'::regclass);


--
-- Name: registration_attempts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_attempts ALTER COLUMN id SET DEFAULT nextval('public.registration_attempts_id_seq'::regclass);


--
-- Name: registration_holds id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_holds ALTER COLUMN id SET DEFAULT nextval('public.registration_holds_id_seq'::regclass);


--
-- Name: registration_overrides id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_overrides ALTER COLUMN id SET DEFAULT nextval('public.registration_overrides_id_seq'::regclass);


--
-- Name: registration_rule_sets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rule_sets ALTER COLUMN id SET DEFAULT nextval('public.registration_rule_sets_id_seq'::regclass);


--
-- Name: registration_rules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rules ALTER COLUMN id SET DEFAULT nextval('public.registration_rules_id_seq'::regclass);


--
-- Name: role_assignments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignments ALTER COLUMN id SET DEFAULT nextval('public.role_assignments_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: rooms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms ALTER COLUMN id SET DEFAULT nextval('public.rooms_id_seq'::regclass);


--
-- Name: section_instructors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_instructors ALTER COLUMN id SET DEFAULT nextval('public.section_instructors_id_seq'::regclass);


--
-- Name: section_meetings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_meetings ALTER COLUMN id SET DEFAULT nextval('public.section_meetings_id_seq'::regclass);


--
-- Name: section_seat_groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_seat_groups ALTER COLUMN id SET DEFAULT nextval('public.section_seat_groups_id_seq'::regclass);


--
-- Name: sections id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections ALTER COLUMN id SET DEFAULT nextval('public.sections_id_seq'::regclass);


--
-- Name: settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.settings ALTER COLUMN id SET DEFAULT nextval('public.settings_id_seq'::regclass);


--
-- Name: student_record_programs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_record_programs ALTER COLUMN id SET DEFAULT nextval('public.student_record_programs_id_seq'::regclass);


--
-- Name: student_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records ALTER COLUMN id SET DEFAULT nextval('public.student_records_id_seq'::regclass);


--
-- Name: student_status_change_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_change_types ALTER COLUMN id SET DEFAULT nextval('public.student_status_change_types_id_seq'::regclass);


--
-- Name: student_status_changes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_changes ALTER COLUMN id SET DEFAULT nextval('public.student_status_changes_id_seq'::regclass);


--
-- Name: syllabi id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabi ALTER COLUMN id SET DEFAULT nextval('public.syllabi_id_seq'::regclass);


--
-- Name: term_evaluations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_evaluations ALTER COLUMN id SET DEFAULT nextval('public.term_evaluations_id_seq'::regclass);


--
-- Name: term_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_records ALTER COLUMN id SET DEFAULT nextval('public.term_records_id_seq'::regclass);


--
-- Name: term_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_sessions ALTER COLUMN id SET DEFAULT nextval('public.term_sessions_id_seq'::regclass);


--
-- Name: term_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_types ALTER COLUMN id SET DEFAULT nextval('public.term_types_id_seq'::regclass);


--
-- Name: term_windows id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_windows ALTER COLUMN id SET DEFAULT nextval('public.term_windows_id_seq'::regclass);


--
-- Name: terms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms ALTER COLUMN id SET DEFAULT nextval('public.terms_id_seq'::regclass);


--
-- Name: time_slots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.time_slots ALTER COLUMN id SET DEFAULT nextval('public.time_slots_id_seq'::regclass);


--
-- Name: user_identities id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_identities ALTER COLUMN id SET DEFAULT nextval('public.user_identities_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: waitlist_entries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.waitlist_entries ALTER COLUMN id SET DEFAULT nextval('public.waitlist_entries_id_seq'::regclass);


--
-- Name: activity_log activity_log_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.activity_log
    ADD CONSTRAINT activity_log_pkey PRIMARY KEY (id);


--
-- Name: record_changes record_changes_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.record_changes
    ADD CONSTRAINT record_changes_pkey PRIMARY KEY (id);


--
-- Name: security_events security_events_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.security_events
    ADD CONSTRAINT security_events_pkey PRIMARY KEY (id);


--
-- Name: academic_years academic_years_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_years
    ADD CONSTRAINT academic_years_code_unique UNIQUE (code);


--
-- Name: academic_years academic_years_no_overlap_excl; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_years
    ADD CONSTRAINT academic_years_no_overlap_excl EXCLUDE USING gist (year_period WITH &&);


--
-- Name: academic_years academic_years_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.academic_years
    ADD CONSTRAINT academic_years_pkey PRIMARY KEY (id);


--
-- Name: account_invitations account_invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_invitations
    ADD CONSTRAINT account_invitations_pkey PRIMARY KEY (id);


--
-- Name: account_invitations account_invitations_token_hash_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_invitations
    ADD CONSTRAINT account_invitations_token_hash_unique UNIQUE (token_hash);


--
-- Name: additional_program_requests additional_program_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests
    ADD CONSTRAINT additional_program_requests_pkey PRIMARY KEY (id);


--
-- Name: admission_cycle_document_types admission_cycle_document_types_admission_cycle_id_document_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_document_types
    ADD CONSTRAINT admission_cycle_document_types_admission_cycle_id_document_type UNIQUE (admission_cycle_id, document_type_id);


--
-- Name: admission_cycle_document_types admission_cycle_document_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_document_types
    ADD CONSTRAINT admission_cycle_document_types_pkey PRIMARY KEY (id);


--
-- Name: admission_cycle_programs admission_cycle_programs_admission_cycle_id_program_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_programs
    ADD CONSTRAINT admission_cycle_programs_admission_cycle_id_program_id_unique UNIQUE (admission_cycle_id, program_id);


--
-- Name: admission_cycle_programs admission_cycle_programs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_programs
    ADD CONSTRAINT admission_cycle_programs_pkey PRIMARY KEY (id);


--
-- Name: admission_cycles admission_cycles_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycles
    ADD CONSTRAINT admission_cycles_code_unique UNIQUE (code);


--
-- Name: admission_cycles admission_cycles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycles
    ADD CONSTRAINT admission_cycles_pkey PRIMARY KEY (id);


--
-- Name: advisor_assignments advisor_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.advisor_assignments
    ADD CONSTRAINT advisor_assignments_pkey PRIMARY KEY (id);


--
-- Name: application_number_sequences application_number_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_number_sequences
    ADD CONSTRAINT application_number_sequences_pkey PRIMARY KEY (admission_cycle_id);


--
-- Name: applications applications_application_number_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_application_number_unique UNIQUE (application_number);


--
-- Name: applications applications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_pkey PRIMARY KEY (id);


--
-- Name: applications applications_student_record_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_student_record_id_unique UNIQUE (student_record_id);


--
-- Name: assessment_component_scores assessment_component_scores_assessment_result_id_assessment_com; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_component_scores
    ADD CONSTRAINT assessment_component_scores_assessment_result_id_assessment_com UNIQUE (assessment_result_id, assessment_component_id);


--
-- Name: assessment_component_scores assessment_component_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_component_scores
    ADD CONSTRAINT assessment_component_scores_pkey PRIMARY KEY (id);


--
-- Name: assessment_components assessment_components_assessment_type_id_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_components
    ADD CONSTRAINT assessment_components_assessment_type_id_code_unique UNIQUE (assessment_type_id, code);


--
-- Name: assessment_components assessment_components_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_components
    ADD CONSTRAINT assessment_components_pkey PRIMARY KEY (id);


--
-- Name: assessment_registrations assessment_registrations_assessment_session_id_student_record_i; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_registrations
    ADD CONSTRAINT assessment_registrations_assessment_session_id_student_record_i UNIQUE (assessment_session_id, student_record_id);


--
-- Name: assessment_registrations assessment_registrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_registrations
    ADD CONSTRAINT assessment_registrations_pkey PRIMARY KEY (id);


--
-- Name: assessment_result_corrections assessment_result_corrections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_result_corrections
    ADD CONSTRAINT assessment_result_corrections_pkey PRIMARY KEY (id);


--
-- Name: assessment_results assessment_results_assessment_registration_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_assessment_registration_id_unique UNIQUE (assessment_registration_id);


--
-- Name: assessment_results assessment_results_assessment_session_id_student_record_id_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_assessment_session_id_student_record_id_uniq UNIQUE (assessment_session_id, student_record_id);


--
-- Name: assessment_results assessment_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_pkey PRIMARY KEY (id);


--
-- Name: assessment_sessions assessment_sessions_assessment_type_id_held_date_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT assessment_sessions_assessment_type_id_held_date_unique UNIQUE (assessment_type_id, held_date);


--
-- Name: assessment_sessions assessment_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT assessment_sessions_pkey PRIMARY KEY (id);


--
-- Name: assessment_types assessment_types_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_types
    ADD CONSTRAINT assessment_types_code_unique UNIQUE (code);


--
-- Name: assessment_types assessment_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_types
    ADD CONSTRAINT assessment_types_pkey PRIMARY KEY (id);


--
-- Name: attendance_records attendance_records_class_meeting_id_enrollment_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_class_meeting_id_enrollment_id_unique UNIQUE (class_meeting_id, enrollment_id);


--
-- Name: attendance_records attendance_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_pkey PRIMARY KEY (id);


--
-- Name: buildings buildings_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.buildings
    ADD CONSTRAINT buildings_code_unique UNIQUE (code);


--
-- Name: buildings buildings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.buildings
    ADD CONSTRAINT buildings_pkey PRIMARY KEY (id);


--
-- Name: cache_locks cache_locks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cache_locks
    ADD CONSTRAINT cache_locks_pkey PRIMARY KEY (key);


--
-- Name: cache cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cache
    ADD CONSTRAINT cache_pkey PRIMARY KEY (key);


--
-- Name: cart_items cart_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_pkey PRIMARY KEY (id);


--
-- Name: cart_items cart_items_student_record_id_section_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_student_record_id_section_id_unique UNIQUE (student_record_id, section_id);


--
-- Name: certificate_issues certificate_issues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_issues
    ADD CONSTRAINT certificate_issues_pkey PRIMARY KEY (id);


--
-- Name: certificate_issues certificate_issues_serial_number_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_issues
    ADD CONSTRAINT certificate_issues_serial_number_unique UNIQUE (serial_number);


--
-- Name: certificate_issues certificate_issues_verification_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_issues
    ADD CONSTRAINT certificate_issues_verification_code_unique UNIQUE (verification_code);


--
-- Name: certificate_number_sequences certificate_number_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_number_sequences
    ADD CONSTRAINT certificate_number_sequences_pkey PRIMARY KEY (prefix);


--
-- Name: certificate_templates certificate_templates_certificate_type_id_locale_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_templates
    ADD CONSTRAINT certificate_templates_certificate_type_id_locale_unique UNIQUE (certificate_type_id, locale);


--
-- Name: certificate_templates certificate_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_templates
    ADD CONSTRAINT certificate_templates_pkey PRIMARY KEY (id);


--
-- Name: certificate_types certificate_types_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_types
    ADD CONSTRAINT certificate_types_code_unique UNIQUE (code);


--
-- Name: certificate_types certificate_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_types
    ADD CONSTRAINT certificate_types_pkey PRIMARY KEY (id);


--
-- Name: class_meetings class_meetings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.class_meetings
    ADD CONSTRAINT class_meetings_pkey PRIMARY KEY (id);


--
-- Name: class_meetings class_meetings_section_id_meeting_date_start_time_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.class_meetings
    ADD CONSTRAINT class_meetings_section_id_meeting_date_start_time_unique UNIQUE (section_id, meeting_date, start_time);


--
-- Name: countries countries_alpha3_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.countries
    ADD CONSTRAINT countries_alpha3_code_unique UNIQUE (alpha3_code);


--
-- Name: countries countries_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.countries
    ADD CONSTRAINT countries_code_unique UNIQUE (code);


--
-- Name: countries countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.countries
    ADD CONSTRAINT countries_pkey PRIMARY KEY (id);


--
-- Name: course_categories course_categories_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_categories
    ADD CONSTRAINT course_categories_code_unique UNIQUE (code);


--
-- Name: course_categories course_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_categories
    ADD CONSTRAINT course_categories_pkey PRIMARY KEY (id);


--
-- Name: course_equivalencies course_equivalencies_no_overlap_excl; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_equivalencies
    ADD CONSTRAINT course_equivalencies_no_overlap_excl EXCLUDE USING gist (course_id WITH =, equivalent_course_id WITH =, effective_period WITH &&);


--
-- Name: course_equivalencies course_equivalencies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_equivalencies
    ADD CONSTRAINT course_equivalencies_pkey PRIMARY KEY (id);


--
-- Name: course_requisites course_requisites_course_version_id_kind_group_number_required_; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_requisites
    ADD CONSTRAINT course_requisites_course_version_id_kind_group_number_required_ UNIQUE (course_version_id, kind, group_number, required_course_id);


--
-- Name: course_requisites course_requisites_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_requisites
    ADD CONSTRAINT course_requisites_pkey PRIMARY KEY (id);


--
-- Name: course_versions course_versions_id_course_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_id_course_id_unique UNIQUE (id, course_id);


--
-- Name: course_versions course_versions_no_overlap_excl; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_no_overlap_excl EXCLUDE USING gist (course_id WITH =, effective_period WITH &&);


--
-- Name: course_versions course_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_pkey PRIMARY KEY (id);


--
-- Name: courses courses_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_code_unique UNIQUE (code);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: credit_limit_policies credit_limit_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_limit_policies
    ADD CONSTRAINT credit_limit_policies_pkey PRIMARY KEY (id);


--
-- Name: curriculum_requirement_courses curriculum_requirement_courses_curriculum_requirement_id_course; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_courses
    ADD CONSTRAINT curriculum_requirement_courses_curriculum_requirement_id_course UNIQUE (curriculum_requirement_id, course_id);


--
-- Name: curriculum_requirement_courses curriculum_requirement_courses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_courses
    ADD CONSTRAINT curriculum_requirement_courses_pkey PRIMARY KEY (id);


--
-- Name: curriculum_requirement_sets curriculum_requirement_sets_no_overlap_excl; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_sets
    ADD CONSTRAINT curriculum_requirement_sets_no_overlap_excl EXCLUDE USING gist (program_id WITH =, program_role WITH =, catalog_years WITH &&);


--
-- Name: curriculum_requirement_sets curriculum_requirement_sets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_sets
    ADD CONSTRAINT curriculum_requirement_sets_pkey PRIMARY KEY (id);


--
-- Name: curriculum_requirements curriculum_requirements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirements
    ADD CONSTRAINT curriculum_requirements_pkey PRIMARY KEY (id);


--
-- Name: degree_audits degree_audits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_audits
    ADD CONSTRAINT degree_audits_pkey PRIMARY KEY (id);


--
-- Name: degree_number_sequences degree_number_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_number_sequences
    ADD CONSTRAINT degree_number_sequences_pkey PRIMARY KEY (prefix);


--
-- Name: degree_requirement_waivers degree_requirement_waivers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_requirement_waivers
    ADD CONSTRAINT degree_requirement_waivers_pkey PRIMARY KEY (id);


--
-- Name: enrollments enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_pkey PRIMARY KEY (id);


--
-- Name: evaluation_answers evaluation_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_answers
    ADD CONSTRAINT evaluation_answers_pkey PRIMARY KEY (evaluation_response_id, evaluation_question_id);


--
-- Name: evaluation_completions evaluation_completions_enrollment_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_completions
    ADD CONSTRAINT evaluation_completions_enrollment_id_unique UNIQUE (enrollment_id);


--
-- Name: evaluation_completions evaluation_completions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_completions
    ADD CONSTRAINT evaluation_completions_pkey PRIMARY KEY (id);


--
-- Name: evaluation_forms evaluation_forms_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_forms
    ADD CONSTRAINT evaluation_forms_code_unique UNIQUE (code);


--
-- Name: evaluation_forms evaluation_forms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_forms
    ADD CONSTRAINT evaluation_forms_pkey PRIMARY KEY (id);


--
-- Name: evaluation_method_requests evaluation_method_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_method_requests
    ADD CONSTRAINT evaluation_method_requests_pkey PRIMARY KEY (id);


--
-- Name: evaluation_questions evaluation_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_questions
    ADD CONSTRAINT evaluation_questions_pkey PRIMARY KEY (id);


--
-- Name: evaluation_responses evaluation_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_responses
    ADD CONSTRAINT evaluation_responses_pkey PRIMARY KEY (id);


--
-- Name: exports exports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exports
    ADD CONSTRAINT exports_pkey PRIMARY KEY (id);


--
-- Name: failed_import_rows failed_import_rows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_import_rows
    ADD CONSTRAINT failed_import_rows_pkey PRIMARY KEY (id);


--
-- Name: failed_jobs failed_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_jobs
    ADD CONSTRAINT failed_jobs_pkey PRIMARY KEY (id);


--
-- Name: failed_jobs failed_jobs_uuid_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_jobs
    ADD CONSTRAINT failed_jobs_uuid_unique UNIQUE (uuid);


--
-- Name: features features_name_scope_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.features
    ADD CONSTRAINT features_name_scope_unique UNIQUE (name, scope);


--
-- Name: features features_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.features
    ADD CONSTRAINT features_pkey PRIMARY KEY (id);


--
-- Name: grade_change_requests grade_change_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_change_requests
    ADD CONSTRAINT grade_change_requests_pkey PRIMARY KEY (id);


--
-- Name: grade_scale_items grade_scale_items_grade_scale_id_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_scale_items
    ADD CONSTRAINT grade_scale_items_grade_scale_id_code_unique UNIQUE (grade_scale_id, code);


--
-- Name: grade_scale_items grade_scale_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_scale_items
    ADD CONSTRAINT grade_scale_items_pkey PRIMARY KEY (id);


--
-- Name: grade_scales grade_scales_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_scales
    ADD CONSTRAINT grade_scales_code_unique UNIQUE (code);


--
-- Name: grade_scales grade_scales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_scales
    ADD CONSTRAINT grade_scales_pkey PRIMARY KEY (id);


--
-- Name: guardians guardians_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.guardians
    ADD CONSTRAINT guardians_pkey PRIMARY KEY (id);


--
-- Name: imports imports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.imports
    ADD CONSTRAINT imports_pkey PRIMARY KEY (id);


--
-- Name: instructors instructors_employee_number_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instructors
    ADD CONSTRAINT instructors_employee_number_unique UNIQUE (employee_number);


--
-- Name: instructors instructors_person_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instructors
    ADD CONSTRAINT instructors_person_id_unique UNIQUE (person_id);


--
-- Name: instructors instructors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instructors
    ADD CONSTRAINT instructors_pkey PRIMARY KEY (id);


--
-- Name: job_batches job_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_batches
    ADD CONSTRAINT job_batches_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: languages languages_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.languages
    ADD CONSTRAINT languages_code_unique UNIQUE (code);


--
-- Name: languages languages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.languages
    ADD CONSTRAINT languages_pkey PRIMARY KEY (id);


--
-- Name: lms_course_links lms_course_links_lms_platform_id_section_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_course_links
    ADD CONSTRAINT lms_course_links_lms_platform_id_section_id_unique UNIQUE (lms_platform_id, section_id);


--
-- Name: lms_course_links lms_course_links_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_course_links
    ADD CONSTRAINT lms_course_links_pkey PRIMARY KEY (id);


--
-- Name: lms_platforms lms_platforms_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_platforms
    ADD CONSTRAINT lms_platforms_code_unique UNIQUE (code);


--
-- Name: lms_platforms lms_platforms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_platforms
    ADD CONSTRAINT lms_platforms_pkey PRIMARY KEY (id);


--
-- Name: lms_sync_logs lms_sync_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_sync_logs
    ADD CONSTRAINT lms_sync_logs_pkey PRIMARY KEY (id);


--
-- Name: lms_user_links lms_user_links_lms_platform_id_external_user_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_user_links
    ADD CONSTRAINT lms_user_links_lms_platform_id_external_user_id_unique UNIQUE (lms_platform_id, external_user_id);


--
-- Name: lms_user_links lms_user_links_lms_platform_id_user_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_user_links
    ADD CONSTRAINT lms_user_links_lms_platform_id_user_id_unique UNIQUE (lms_platform_id, user_id);


--
-- Name: lms_user_links lms_user_links_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_user_links
    ADD CONSTRAINT lms_user_links_pkey PRIMARY KEY (id);


--
-- Name: lookup_types lookup_types_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lookup_types
    ADD CONSTRAINT lookup_types_code_unique UNIQUE (code);


--
-- Name: lookup_types lookup_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lookup_types
    ADD CONSTRAINT lookup_types_pkey PRIMARY KEY (id);


--
-- Name: lookup_values lookup_values_lookup_type_id_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lookup_values
    ADD CONSTRAINT lookup_values_lookup_type_id_code_unique UNIQUE (lookup_type_id, code);


--
-- Name: lookup_values lookup_values_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lookup_values
    ADD CONSTRAINT lookup_values_pkey PRIMARY KEY (id);


--
-- Name: media media_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media
    ADD CONSTRAINT media_pkey PRIMARY KEY (id);


--
-- Name: media media_uuid_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media
    ADD CONSTRAINT media_uuid_unique UNIQUE (uuid);


--
-- Name: migrations migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.migrations
    ADD CONSTRAINT migrations_pkey PRIMARY KEY (id);


--
-- Name: model_has_permissions model_has_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_has_permissions
    ADD CONSTRAINT model_has_permissions_pkey PRIMARY KEY (permission_id, model_id, model_type);


--
-- Name: model_has_roles model_has_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_has_roles
    ADD CONSTRAINT model_has_roles_pkey PRIMARY KEY (role_id, model_id, model_type);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: org_unit_successions org_unit_successions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_unit_successions
    ADD CONSTRAINT org_unit_successions_pkey PRIMARY KEY (id);


--
-- Name: org_unit_successions org_unit_successions_predecessor_org_unit_id_successor_org_unit; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_unit_successions
    ADD CONSTRAINT org_unit_successions_predecessor_org_unit_id_successor_org_unit UNIQUE (predecessor_org_unit_id, successor_org_unit_id);


--
-- Name: org_unit_types org_unit_types_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_unit_types
    ADD CONSTRAINT org_unit_types_code_unique UNIQUE (code);


--
-- Name: org_unit_types org_unit_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_unit_types
    ADD CONSTRAINT org_unit_types_pkey PRIMARY KEY (id);


--
-- Name: org_units org_units_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_units
    ADD CONSTRAINT org_units_code_unique UNIQUE (code);


--
-- Name: org_units org_units_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_units
    ADD CONSTRAINT org_units_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (email);


--
-- Name: people people_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_name_guard_name_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_name_guard_name_unique UNIQUE (name, guard_name);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: programs programs_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs
    ADD CONSTRAINT programs_code_unique UNIQUE (code);


--
-- Name: programs programs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs
    ADD CONSTRAINT programs_pkey PRIMARY KEY (id);


--
-- Name: registration_attempts registration_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_attempts
    ADD CONSTRAINT registration_attempts_pkey PRIMARY KEY (id);


--
-- Name: registration_holds registration_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_holds
    ADD CONSTRAINT registration_holds_pkey PRIMARY KEY (id);


--
-- Name: registration_overrides registration_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_overrides
    ADD CONSTRAINT registration_overrides_pkey PRIMARY KEY (id);


--
-- Name: registration_rule_sets registration_rule_sets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rule_sets
    ADD CONSTRAINT registration_rule_sets_pkey PRIMARY KEY (id);


--
-- Name: registration_rule_sets registration_rule_sets_term_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rule_sets
    ADD CONSTRAINT registration_rule_sets_term_id_unique UNIQUE (term_id);


--
-- Name: registration_rules registration_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rules
    ADD CONSTRAINT registration_rules_pkey PRIMARY KEY (id);


--
-- Name: registration_rules registration_rules_registration_rule_set_id_rule_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rules
    ADD CONSTRAINT registration_rules_registration_rule_set_id_rule_code_unique UNIQUE (registration_rule_set_id, rule_code);


--
-- Name: role_assignments role_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignments
    ADD CONSTRAINT role_assignments_pkey PRIMARY KEY (id);


--
-- Name: role_has_permissions role_has_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_has_permissions
    ADD CONSTRAINT role_has_permissions_pkey PRIMARY KEY (permission_id, role_id);


--
-- Name: roles roles_name_guard_name_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_guard_name_unique UNIQUE (name, guard_name);


--
-- Name: roles roles_persona_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_persona_unique UNIQUE (persona);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: rooms rooms_building_id_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_building_id_code_unique UNIQUE (building_id, code);


--
-- Name: rooms rooms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_pkey PRIMARY KEY (id);


--
-- Name: section_instructors section_instructors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_instructors
    ADD CONSTRAINT section_instructors_pkey PRIMARY KEY (id);


--
-- Name: section_instructors section_instructors_section_id_instructor_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_instructors
    ADD CONSTRAINT section_instructors_section_id_instructor_id_unique UNIQUE (section_id, instructor_id);


--
-- Name: section_meetings section_meetings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_meetings
    ADD CONSTRAINT section_meetings_pkey PRIMARY KEY (id);


--
-- Name: section_meetings section_meetings_room_excl; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_meetings
    ADD CONSTRAINT section_meetings_room_excl EXCLUDE USING gist (room_id WITH =, weekday WITH =, time_range WITH &&, date_range WITH &&) WHERE (((room_id IS NOT NULL) AND is_active));


--
-- Name: section_meetings section_meetings_section_excl; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_meetings
    ADD CONSTRAINT section_meetings_section_excl EXCLUDE USING gist (section_id WITH =, weekday WITH =, time_range WITH &&, date_range WITH &&);


--
-- Name: section_seat_groups section_seat_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_seat_groups
    ADD CONSTRAINT section_seat_groups_pkey PRIMARY KEY (id);


--
-- Name: sections sections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_pkey PRIMARY KEY (id);


--
-- Name: sections sections_term_id_course_id_section_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_term_id_course_id_section_code_unique UNIQUE (term_id, course_id, section_code);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: settings settings_group_name_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_group_name_unique UNIQUE ("group", name);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (id);


--
-- Name: student_number_sequences student_number_sequences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_number_sequences
    ADD CONSTRAINT student_number_sequences_pkey PRIMARY KEY (prefix);


--
-- Name: student_record_programs student_record_programs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_record_programs
    ADD CONSTRAINT student_record_programs_pkey PRIMARY KEY (id);


--
-- Name: student_records student_records_degree_number_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records
    ADD CONSTRAINT student_records_degree_number_unique UNIQUE (degree_number);


--
-- Name: student_records student_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records
    ADD CONSTRAINT student_records_pkey PRIMARY KEY (id);


--
-- Name: student_records student_records_student_number_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records
    ADD CONSTRAINT student_records_student_number_unique UNIQUE (student_number);


--
-- Name: student_status_change_types student_status_change_types_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_change_types
    ADD CONSTRAINT student_status_change_types_code_unique UNIQUE (code);


--
-- Name: student_status_change_types student_status_change_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_change_types
    ADD CONSTRAINT student_status_change_types_pkey PRIMARY KEY (id);


--
-- Name: student_status_changes student_status_changes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_changes
    ADD CONSTRAINT student_status_changes_pkey PRIMARY KEY (id);


--
-- Name: syllabi syllabi_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabi
    ADD CONSTRAINT syllabi_pkey PRIMARY KEY (id);


--
-- Name: syllabi syllabi_section_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabi
    ADD CONSTRAINT syllabi_section_id_unique UNIQUE (section_id);


--
-- Name: term_evaluations term_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_evaluations
    ADD CONSTRAINT term_evaluations_pkey PRIMARY KEY (id);


--
-- Name: term_evaluations term_evaluations_term_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_evaluations
    ADD CONSTRAINT term_evaluations_term_id_unique UNIQUE (term_id);


--
-- Name: term_records term_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_records
    ADD CONSTRAINT term_records_pkey PRIMARY KEY (id);


--
-- Name: term_records term_records_student_record_id_term_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_records
    ADD CONSTRAINT term_records_student_record_id_term_id_unique UNIQUE (student_record_id, term_id);


--
-- Name: term_sessions term_sessions_id_term_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_sessions
    ADD CONSTRAINT term_sessions_id_term_id_unique UNIQUE (id, term_id);


--
-- Name: term_sessions term_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_sessions
    ADD CONSTRAINT term_sessions_pkey PRIMARY KEY (id);


--
-- Name: term_sessions term_sessions_term_id_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_sessions
    ADD CONSTRAINT term_sessions_term_id_code_unique UNIQUE (term_id, code);


--
-- Name: term_types term_types_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_types
    ADD CONSTRAINT term_types_code_unique UNIQUE (code);


--
-- Name: term_types term_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_types
    ADD CONSTRAINT term_types_pkey PRIMARY KEY (id);


--
-- Name: term_windows term_windows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_windows
    ADD CONSTRAINT term_windows_pkey PRIMARY KEY (id);


--
-- Name: terms terms_academic_year_id_term_type_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_academic_year_id_term_type_id_unique UNIQUE (academic_year_id, term_type_id);


--
-- Name: terms terms_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_code_unique UNIQUE (code);


--
-- Name: terms terms_no_overlap_excl; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_no_overlap_excl EXCLUDE USING gist (term_type_id WITH =, instruction_period WITH &&);


--
-- Name: terms terms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_pkey PRIMARY KEY (id);


--
-- Name: time_slots time_slots_code_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.time_slots
    ADD CONSTRAINT time_slots_code_unique UNIQUE (code);


--
-- Name: time_slots time_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.time_slots
    ADD CONSTRAINT time_slots_pkey PRIMARY KEY (id);


--
-- Name: user_identities user_identities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_identities
    ADD CONSTRAINT user_identities_pkey PRIMARY KEY (id);


--
-- Name: user_identities user_identities_provider_subject_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_identities
    ADD CONSTRAINT user_identities_provider_subject_unique UNIQUE (provider, subject);


--
-- Name: user_identities user_identities_user_id_provider_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_identities
    ADD CONSTRAINT user_identities_user_id_provider_unique UNIQUE (user_id, provider);


--
-- Name: users users_email_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_unique UNIQUE (email);


--
-- Name: users users_person_id_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_person_id_unique UNIQUE (person_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: waitlist_entries waitlist_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.waitlist_entries
    ADD CONSTRAINT waitlist_entries_pkey PRIMARY KEY (id);


--
-- Name: activity_log_causer; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX activity_log_causer ON audit.activity_log USING btree (causer_type, causer_id);


--
-- Name: activity_log_subject; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX activity_log_subject ON audit.activity_log USING btree (subject_type, subject_id);


--
-- Name: audit_activity_log_log_name_index; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX audit_activity_log_log_name_index ON audit.activity_log USING btree (log_name);


--
-- Name: audit_activity_log_request_id_index; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX audit_activity_log_request_id_index ON audit.activity_log USING btree (request_id);


--
-- Name: audit_record_changes_occurred_at_index; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX audit_record_changes_occurred_at_index ON audit.record_changes USING btree (occurred_at);


--
-- Name: audit_record_changes_table_name_record_id_index; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX audit_record_changes_table_name_record_id_index ON audit.record_changes USING btree (table_name, record_id);


--
-- Name: audit_record_changes_user_id_index; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX audit_record_changes_user_id_index ON audit.record_changes USING btree (user_id);


--
-- Name: audit_security_events_occurred_at_index; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX audit_security_events_occurred_at_index ON audit.security_events USING btree (occurred_at);


--
-- Name: audit_security_events_type_index; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX audit_security_events_type_index ON audit.security_events USING btree (type);


--
-- Name: audit_security_events_user_id_index; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX audit_security_events_user_id_index ON audit.security_events USING btree (user_id);


--
-- Name: security_events_subject; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX security_events_subject ON audit.security_events USING btree (subject_type, subject_id);


--
-- Name: account_invitations_person_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX account_invitations_person_id_index ON public.account_invitations USING btree (person_id);


--
-- Name: additional_program_requests_org_unit_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX additional_program_requests_org_unit_id_status_index ON public.additional_program_requests USING btree (org_unit_id, status);


--
-- Name: additional_program_requests_single_pending_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX additional_program_requests_single_pending_unique ON public.additional_program_requests USING btree (student_record_id, program_id) WHERE ((status)::text = 'requested'::text);


--
-- Name: additional_program_requests_student_record_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX additional_program_requests_student_record_id_status_index ON public.additional_program_requests USING btree (student_record_id, status);


--
-- Name: advisor_assignments_instructor_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX advisor_assignments_instructor_id_index ON public.advisor_assignments USING btree (instructor_id);


--
-- Name: advisor_assignments_single_primary_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX advisor_assignments_single_primary_unique ON public.advisor_assignments USING btree (student_record_id) WHERE (((role)::text = 'primary'::text) AND (end_date IS NULL));


--
-- Name: advisor_assignments_student_record_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX advisor_assignments_student_record_id_index ON public.advisor_assignments USING btree (student_record_id);


--
-- Name: applications_admission_cycle_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX applications_admission_cycle_id_status_index ON public.applications USING btree (admission_cycle_id, status);


--
-- Name: applications_org_unit_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX applications_org_unit_id_status_index ON public.applications USING btree (org_unit_id, status);


--
-- Name: applications_person_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX applications_person_id_index ON public.applications USING btree (person_id);


--
-- Name: applications_program_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX applications_program_id_status_index ON public.applications USING btree (program_id, status);


--
-- Name: applications_single_open_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX applications_single_open_unique ON public.applications USING btree (person_id, admission_cycle_id) WHERE ((status)::text <> ALL ((ARRAY['withdrawn'::character varying, 'rejected'::character varying, 'expired'::character varying])::text[]));


--
-- Name: assessment_registrations_student_record_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX assessment_registrations_student_record_id_index ON public.assessment_registrations USING btree (student_record_id);


--
-- Name: assessment_result_corrections_single_pending_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX assessment_result_corrections_single_pending_unique ON public.assessment_result_corrections USING btree (assessment_result_id) WHERE ((status)::text = 'pending'::text);


--
-- Name: assessment_result_corrections_status_requested_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX assessment_result_corrections_status_requested_at_index ON public.assessment_result_corrections USING btree (status, requested_at);


--
-- Name: assessment_results_student_record_id_assessment_type_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX assessment_results_student_record_id_assessment_type_id_index ON public.assessment_results USING btree (student_record_id, assessment_type_id);


--
-- Name: attendance_records_enrollment_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX attendance_records_enrollment_id_index ON public.attendance_records USING btree (enrollment_id);


--
-- Name: cache_expiration_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cache_expiration_index ON public.cache USING btree (expiration);


--
-- Name: cache_locks_expiration_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cache_locks_expiration_index ON public.cache_locks USING btree (expiration);


--
-- Name: certificate_issues_student_record_id_issued_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX certificate_issues_student_record_id_issued_at_index ON public.certificate_issues USING btree (student_record_id, issued_at);


--
-- Name: course_versions_course_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX course_versions_course_id_index ON public.course_versions USING btree (course_id);


--
-- Name: course_versions_title_search_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX course_versions_title_search_index ON public.course_versions USING gin (util.i18n_search_text(title) public.gin_trgm_ops);


--
-- Name: curriculum_requirement_sets_program_id_program_role_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curriculum_requirement_sets_program_id_program_role_index ON public.curriculum_requirement_sets USING btree (program_id, program_role);


--
-- Name: curriculum_requirements_curriculum_requirement_set_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX curriculum_requirements_curriculum_requirement_set_id_index ON public.curriculum_requirements USING btree (curriculum_requirement_set_id);


--
-- Name: degree_audits_student_record_id_program_role_audited_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX degree_audits_student_record_id_program_role_audited_at_index ON public.degree_audits USING btree (student_record_id, program_role, audited_at);


--
-- Name: degree_requirement_waivers_open_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX degree_requirement_waivers_open_unique ON public.degree_requirement_waivers USING btree (student_record_id, curriculum_requirement_id) WHERE ((status)::text = ANY ((ARRAY['pending'::character varying, 'approved'::character varying])::text[]));


--
-- Name: degree_requirement_waivers_student_record_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX degree_requirement_waivers_student_record_id_status_index ON public.degree_requirement_waivers USING btree (student_record_id, status);


--
-- Name: enrollments_active_course_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX enrollments_active_course_unique ON public.enrollments USING btree (student_record_id, term_id, course_id) WHERE ((status)::text = 'enrolled'::text);


--
-- Name: enrollments_active_section_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX enrollments_active_section_unique ON public.enrollments USING btree (student_record_id, section_id) WHERE ((status)::text = ANY ((ARRAY['enrolled'::character varying, 'completed'::character varying])::text[]));


--
-- Name: enrollments_section_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX enrollments_section_id_status_index ON public.enrollments USING btree (section_id, status);


--
-- Name: enrollments_student_record_id_course_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX enrollments_student_record_id_course_id_index ON public.enrollments USING btree (student_record_id, course_id);


--
-- Name: enrollments_student_record_id_term_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX enrollments_student_record_id_term_id_index ON public.enrollments USING btree (student_record_id, term_id);


--
-- Name: evaluation_method_requests_single_pending_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX evaluation_method_requests_single_pending_unique ON public.evaluation_method_requests USING btree (section_id) WHERE ((status)::text = 'pending'::text);


--
-- Name: evaluation_method_requests_status_requested_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX evaluation_method_requests_status_requested_at_index ON public.evaluation_method_requests USING btree (status, requested_at);


--
-- Name: evaluation_questions_evaluation_form_id_sort_order_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX evaluation_questions_evaluation_form_id_sort_order_index ON public.evaluation_questions USING btree (evaluation_form_id, sort_order);


--
-- Name: evaluation_responses_section_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX evaluation_responses_section_id_index ON public.evaluation_responses USING btree (section_id);


--
-- Name: failed_jobs_connection_queue_failed_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX failed_jobs_connection_queue_failed_at_index ON public.failed_jobs USING btree (connection, queue, failed_at);


--
-- Name: grade_change_requests_single_pending_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX grade_change_requests_single_pending_unique ON public.grade_change_requests USING btree (enrollment_id) WHERE ((status)::text = 'pending'::text);


--
-- Name: grade_change_requests_status_requested_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX grade_change_requests_status_requested_at_index ON public.grade_change_requests USING btree (status, requested_at);


--
-- Name: grade_scales_single_default_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX grade_scales_single_default_unique ON public.grade_scales USING btree (is_default) WHERE is_default;


--
-- Name: guardians_person_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX guardians_person_id_index ON public.guardians USING btree (person_id);


--
-- Name: instructors_org_unit_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX instructors_org_unit_id_index ON public.instructors USING btree (org_unit_id);


--
-- Name: jobs_queue_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX jobs_queue_index ON public.jobs USING btree (queue);


--
-- Name: lms_sync_logs_lms_platform_id_started_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lms_sync_logs_lms_platform_id_started_at_index ON public.lms_sync_logs USING btree (lms_platform_id, started_at);


--
-- Name: lms_sync_logs_section_id_started_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lms_sync_logs_section_id_started_at_index ON public.lms_sync_logs USING btree (section_id, started_at);


--
-- Name: media_model_type_model_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX media_model_type_model_id_index ON public.media USING btree (model_type, model_id);


--
-- Name: media_order_column_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX media_order_column_index ON public.media USING btree (order_column);


--
-- Name: model_has_permissions_model_id_model_type_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX model_has_permissions_model_id_model_type_index ON public.model_has_permissions USING btree (model_id, model_type);


--
-- Name: model_has_roles_model_id_model_type_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX model_has_roles_model_id_model_type_index ON public.model_has_roles USING btree (model_id, model_type);


--
-- Name: notifications_notifiable_type_notifiable_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notifications_notifiable_type_notifiable_id_index ON public.notifications USING btree (notifiable_type, notifiable_id);


--
-- Name: org_units_name_search_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX org_units_name_search_index ON public.org_units USING gin (util.i18n_search_text(name) public.gin_trgm_ops);


--
-- Name: org_units_parent_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX org_units_parent_id_index ON public.org_units USING btree (parent_id);


--
-- Name: people_birth_date_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX people_birth_date_index ON public.people USING btree (birth_date);


--
-- Name: people_family_name_given_name_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX people_family_name_given_name_index ON public.people USING btree (family_name, given_name);


--
-- Name: people_name_search_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX people_name_search_index ON public.people USING gin (((((((family_name)::text || ' '::text) || (COALESCE(given_name, ''::character varying))::text) || ' '::text) || util.i18n_search_text(name_variants))) public.gin_trgm_ops);


--
-- Name: people_national_id_hash_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX people_national_id_hash_index ON public.people USING btree (national_id_hash);


--
-- Name: people_passport_number_hash_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX people_passport_number_hash_index ON public.people USING btree (passport_number_hash);


--
-- Name: programs_name_search_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX programs_name_search_index ON public.programs USING gin (util.i18n_search_text(name) public.gin_trgm_ops);


--
-- Name: registration_attempts_section_id_attempted_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX registration_attempts_section_id_attempted_at_index ON public.registration_attempts USING btree (section_id, attempted_at);


--
-- Name: registration_attempts_student_record_id_attempted_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX registration_attempts_student_record_id_attempted_at_index ON public.registration_attempts USING btree (student_record_id, attempted_at);


--
-- Name: registration_holds_student_record_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX registration_holds_student_record_id_index ON public.registration_holds USING btree (student_record_id);


--
-- Name: registration_overrides_student_record_id_term_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX registration_overrides_student_record_id_term_id_index ON public.registration_overrides USING btree (student_record_id, term_id);


--
-- Name: role_assignments_user_id_role_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX role_assignments_user_id_role_id_index ON public.role_assignments USING btree (user_id, role_id);


--
-- Name: section_instructors_instructor_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX section_instructors_instructor_id_index ON public.section_instructors USING btree (instructor_id);


--
-- Name: section_meetings_room_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX section_meetings_room_id_index ON public.section_meetings USING btree (room_id);


--
-- Name: section_meetings_section_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX section_meetings_section_id_index ON public.section_meetings USING btree (section_id);


--
-- Name: section_seat_groups_section_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX section_seat_groups_section_id_index ON public.section_seat_groups USING btree (section_id);


--
-- Name: sections_course_version_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sections_course_version_id_index ON public.sections USING btree (course_version_id);


--
-- Name: sections_term_id_org_unit_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sections_term_id_org_unit_id_index ON public.sections USING btree (term_id, org_unit_id);


--
-- Name: sessions_last_activity_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sessions_last_activity_index ON public.sessions USING btree (last_activity);


--
-- Name: sessions_user_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX sessions_user_id_index ON public.sessions USING btree (user_id);


--
-- Name: student_record_programs_current_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX student_record_programs_current_unique ON public.student_record_programs USING btree (student_record_id, program_id) WHERE (end_date IS NULL);


--
-- Name: student_records_institutional_email_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX student_records_institutional_email_index ON public.student_records USING btree (institutional_email);


--
-- Name: student_records_org_unit_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX student_records_org_unit_id_status_index ON public.student_records USING btree (org_unit_id, status);


--
-- Name: student_records_person_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX student_records_person_id_index ON public.student_records USING btree (person_id);


--
-- Name: student_records_program_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX student_records_program_id_status_index ON public.student_records USING btree (program_id, status);


--
-- Name: student_status_changes_single_pending_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX student_status_changes_single_pending_unique ON public.student_status_changes USING btree (student_record_id) WHERE ((status)::text = 'requested'::text);


--
-- Name: student_status_changes_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX student_status_changes_status_index ON public.student_status_changes USING btree (status);


--
-- Name: student_status_changes_student_record_id_status_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX student_status_changes_student_record_id_status_index ON public.student_status_changes USING btree (student_record_id, status);


--
-- Name: term_records_term_id_academic_standing_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX term_records_term_id_academic_standing_index ON public.term_records USING btree (term_id, academic_standing);


--
-- Name: term_sessions_single_full_term_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX term_sessions_single_full_term_unique ON public.term_sessions USING btree (term_id) WHERE is_full_term;


--
-- Name: term_windows_term_session_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX term_windows_term_session_id_index ON public.term_windows USING btree (term_session_id);


--
-- Name: term_windows_window_type_opens_at_closes_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX term_windows_window_type_opens_at_closes_at_index ON public.term_windows USING btree (window_type, opens_at, closes_at);


--
-- Name: waitlist_entries_section_id_status_requested_at_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX waitlist_entries_section_id_status_requested_at_index ON public.waitlist_entries USING btree (section_id, status, requested_at);


--
-- Name: waitlist_entries_single_waiting_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX waitlist_entries_single_waiting_unique ON public.waitlist_entries USING btree (section_id, student_record_id) WHERE ((status)::text = 'waiting'::text);


--
-- Name: waitlist_entries_student_record_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX waitlist_entries_student_record_id_index ON public.waitlist_entries USING btree (student_record_id);


--
-- Name: activity_log activity_log_before_change_prevent_modification; Type: TRIGGER; Schema: audit; Owner: -
--

CREATE TRIGGER activity_log_before_change_prevent_modification BEFORE DELETE OR UPDATE OR TRUNCATE ON audit.activity_log FOR EACH STATEMENT EXECUTE FUNCTION audit.prevent_modification();


--
-- Name: activity_log activity_log_before_insert_row_hash; Type: TRIGGER; Schema: audit; Owner: -
--

CREATE TRIGGER activity_log_before_insert_row_hash BEFORE INSERT ON audit.activity_log FOR EACH ROW EXECUTE FUNCTION audit.set_row_hash();


--
-- Name: record_changes record_changes_before_change_prevent_modification; Type: TRIGGER; Schema: audit; Owner: -
--

CREATE TRIGGER record_changes_before_change_prevent_modification BEFORE DELETE OR UPDATE OR TRUNCATE ON audit.record_changes FOR EACH STATEMENT EXECUTE FUNCTION audit.prevent_modification();


--
-- Name: record_changes record_changes_before_insert_row_hash; Type: TRIGGER; Schema: audit; Owner: -
--

CREATE TRIGGER record_changes_before_insert_row_hash BEFORE INSERT ON audit.record_changes FOR EACH ROW EXECUTE FUNCTION audit.set_row_hash();


--
-- Name: security_events security_events_before_change_prevent_modification; Type: TRIGGER; Schema: audit; Owner: -
--

CREATE TRIGGER security_events_before_change_prevent_modification BEFORE DELETE OR UPDATE OR TRUNCATE ON audit.security_events FOR EACH STATEMENT EXECUTE FUNCTION audit.prevent_modification();


--
-- Name: security_events security_events_before_insert_row_hash; Type: TRIGGER; Schema: audit; Owner: -
--

CREATE TRIGGER security_events_before_insert_row_hash BEFORE INSERT ON audit.security_events FOR EACH ROW EXECUTE FUNCTION audit.set_row_hash();


--
-- Name: academic_years academic_years_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER academic_years_after_truncate_audit AFTER TRUNCATE ON public.academic_years FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: academic_years academic_years_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER academic_years_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.academic_years FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: account_invitations account_invitations_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER account_invitations_after_truncate_audit AFTER TRUNCATE ON public.account_invitations FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: account_invitations account_invitations_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER account_invitations_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.account_invitations FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: additional_program_requests additional_program_requests_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER additional_program_requests_after_truncate_audit AFTER TRUNCATE ON public.additional_program_requests FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: additional_program_requests additional_program_requests_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER additional_program_requests_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.additional_program_requests FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: admission_cycle_document_types admission_cycle_document_types_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER admission_cycle_document_types_after_truncate_audit AFTER TRUNCATE ON public.admission_cycle_document_types FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: admission_cycle_document_types admission_cycle_document_types_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER admission_cycle_document_types_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.admission_cycle_document_types FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: admission_cycle_programs admission_cycle_programs_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER admission_cycle_programs_after_truncate_audit AFTER TRUNCATE ON public.admission_cycle_programs FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: admission_cycle_programs admission_cycle_programs_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER admission_cycle_programs_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.admission_cycle_programs FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: admission_cycles admission_cycles_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER admission_cycles_after_truncate_audit AFTER TRUNCATE ON public.admission_cycles FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: admission_cycles admission_cycles_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER admission_cycles_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.admission_cycles FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: advisor_assignments advisor_assignments_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER advisor_assignments_after_truncate_audit AFTER TRUNCATE ON public.advisor_assignments FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: advisor_assignments advisor_assignments_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER advisor_assignments_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.advisor_assignments FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: applications applications_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER applications_after_truncate_audit AFTER TRUNCATE ON public.applications FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: applications applications_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER applications_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.applications FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_component_scores assessment_component_scores_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_component_scores_after_truncate_audit AFTER TRUNCATE ON public.assessment_component_scores FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_component_scores assessment_component_scores_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_component_scores_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.assessment_component_scores FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_components assessment_components_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_components_after_truncate_audit AFTER TRUNCATE ON public.assessment_components FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_components assessment_components_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_components_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.assessment_components FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_registrations assessment_registrations_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_registrations_after_truncate_audit AFTER TRUNCATE ON public.assessment_registrations FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_registrations assessment_registrations_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_registrations_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.assessment_registrations FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_result_corrections assessment_result_corrections_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_result_corrections_after_truncate_audit AFTER TRUNCATE ON public.assessment_result_corrections FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_result_corrections assessment_result_corrections_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_result_corrections_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.assessment_result_corrections FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_results assessment_results_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_results_after_truncate_audit AFTER TRUNCATE ON public.assessment_results FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_results assessment_results_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_results_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.assessment_results FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_sessions assessment_sessions_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_sessions_after_truncate_audit AFTER TRUNCATE ON public.assessment_sessions FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_sessions assessment_sessions_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_sessions_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.assessment_sessions FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_types assessment_types_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_types_after_truncate_audit AFTER TRUNCATE ON public.assessment_types FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: assessment_types assessment_types_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER assessment_types_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.assessment_types FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: attendance_records attendance_records_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER attendance_records_after_truncate_audit AFTER TRUNCATE ON public.attendance_records FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: attendance_records attendance_records_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER attendance_records_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.attendance_records FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: buildings buildings_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER buildings_after_truncate_audit AFTER TRUNCATE ON public.buildings FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: buildings buildings_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER buildings_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.buildings FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: certificate_issues certificate_issues_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER certificate_issues_after_truncate_audit AFTER TRUNCATE ON public.certificate_issues FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: certificate_issues certificate_issues_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER certificate_issues_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.certificate_issues FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: certificate_templates certificate_templates_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER certificate_templates_after_truncate_audit AFTER TRUNCATE ON public.certificate_templates FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: certificate_templates certificate_templates_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER certificate_templates_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.certificate_templates FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: certificate_types certificate_types_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER certificate_types_after_truncate_audit AFTER TRUNCATE ON public.certificate_types FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: certificate_types certificate_types_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER certificate_types_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.certificate_types FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: class_meetings class_meetings_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER class_meetings_after_truncate_audit AFTER TRUNCATE ON public.class_meetings FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: class_meetings class_meetings_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER class_meetings_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.class_meetings FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: countries countries_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER countries_after_truncate_audit AFTER TRUNCATE ON public.countries FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: countries countries_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER countries_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.countries FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: course_categories course_categories_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER course_categories_after_truncate_audit AFTER TRUNCATE ON public.course_categories FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: course_categories course_categories_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER course_categories_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.course_categories FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: course_equivalencies course_equivalencies_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER course_equivalencies_after_truncate_audit AFTER TRUNCATE ON public.course_equivalencies FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: course_equivalencies course_equivalencies_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER course_equivalencies_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.course_equivalencies FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: course_requisites course_requisites_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER course_requisites_after_truncate_audit AFTER TRUNCATE ON public.course_requisites FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: course_requisites course_requisites_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER course_requisites_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.course_requisites FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: course_versions course_versions_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER course_versions_after_truncate_audit AFTER TRUNCATE ON public.course_versions FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: course_versions course_versions_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER course_versions_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.course_versions FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: courses courses_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER courses_after_truncate_audit AFTER TRUNCATE ON public.courses FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: courses courses_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER courses_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.courses FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: credit_limit_policies credit_limit_policies_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER credit_limit_policies_after_truncate_audit AFTER TRUNCATE ON public.credit_limit_policies FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: credit_limit_policies credit_limit_policies_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER credit_limit_policies_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.credit_limit_policies FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: curriculum_requirement_courses curriculum_requirement_courses_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER curriculum_requirement_courses_after_truncate_audit AFTER TRUNCATE ON public.curriculum_requirement_courses FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: curriculum_requirement_courses curriculum_requirement_courses_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER curriculum_requirement_courses_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.curriculum_requirement_courses FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: curriculum_requirement_sets curriculum_requirement_sets_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER curriculum_requirement_sets_after_truncate_audit AFTER TRUNCATE ON public.curriculum_requirement_sets FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: curriculum_requirement_sets curriculum_requirement_sets_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER curriculum_requirement_sets_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.curriculum_requirement_sets FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: curriculum_requirements curriculum_requirements_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER curriculum_requirements_after_truncate_audit AFTER TRUNCATE ON public.curriculum_requirements FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: curriculum_requirements curriculum_requirements_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER curriculum_requirements_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.curriculum_requirements FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: degree_requirement_waivers degree_requirement_waivers_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER degree_requirement_waivers_after_truncate_audit AFTER TRUNCATE ON public.degree_requirement_waivers FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: degree_requirement_waivers degree_requirement_waivers_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER degree_requirement_waivers_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.degree_requirement_waivers FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: enrollments enrollments_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER enrollments_after_truncate_audit AFTER TRUNCATE ON public.enrollments FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: enrollments enrollments_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER enrollments_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.enrollments FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: enrollments enrollments_guard_finalized_grade; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER enrollments_guard_finalized_grade BEFORE DELETE OR UPDATE ON public.enrollments FOR EACH ROW EXECUTE FUNCTION util.guard_finalized_grade();


--
-- Name: evaluation_forms evaluation_forms_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER evaluation_forms_after_truncate_audit AFTER TRUNCATE ON public.evaluation_forms FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: evaluation_forms evaluation_forms_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER evaluation_forms_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.evaluation_forms FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: evaluation_method_requests evaluation_method_requests_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER evaluation_method_requests_after_truncate_audit AFTER TRUNCATE ON public.evaluation_method_requests FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: evaluation_method_requests evaluation_method_requests_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER evaluation_method_requests_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.evaluation_method_requests FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: evaluation_questions evaluation_questions_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER evaluation_questions_after_truncate_audit AFTER TRUNCATE ON public.evaluation_questions FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: evaluation_questions evaluation_questions_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER evaluation_questions_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.evaluation_questions FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: grade_change_requests grade_change_requests_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER grade_change_requests_after_truncate_audit AFTER TRUNCATE ON public.grade_change_requests FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: grade_change_requests grade_change_requests_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER grade_change_requests_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.grade_change_requests FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: grade_scale_items grade_scale_items_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER grade_scale_items_after_truncate_audit AFTER TRUNCATE ON public.grade_scale_items FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: grade_scale_items grade_scale_items_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER grade_scale_items_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.grade_scale_items FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: grade_scales grade_scales_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER grade_scales_after_truncate_audit AFTER TRUNCATE ON public.grade_scales FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: grade_scales grade_scales_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER grade_scales_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.grade_scales FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: guardians guardians_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guardians_after_truncate_audit AFTER TRUNCATE ON public.guardians FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: guardians guardians_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER guardians_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.guardians FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: instructors instructors_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER instructors_after_truncate_audit AFTER TRUNCATE ON public.instructors FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: instructors instructors_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER instructors_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.instructors FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: languages languages_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER languages_after_truncate_audit AFTER TRUNCATE ON public.languages FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: languages languages_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER languages_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.languages FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: lms_course_links lms_course_links_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lms_course_links_after_truncate_audit AFTER TRUNCATE ON public.lms_course_links FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: lms_course_links lms_course_links_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lms_course_links_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.lms_course_links FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: lms_platforms lms_platforms_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lms_platforms_after_truncate_audit AFTER TRUNCATE ON public.lms_platforms FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: lms_platforms lms_platforms_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lms_platforms_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.lms_platforms FOR EACH ROW EXECUTE FUNCTION audit.record_change('credentials');


--
-- Name: lms_user_links lms_user_links_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lms_user_links_after_truncate_audit AFTER TRUNCATE ON public.lms_user_links FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: lms_user_links lms_user_links_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lms_user_links_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.lms_user_links FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: lookup_types lookup_types_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lookup_types_after_truncate_audit AFTER TRUNCATE ON public.lookup_types FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: lookup_types lookup_types_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lookup_types_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.lookup_types FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: lookup_values lookup_values_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lookup_values_after_truncate_audit AFTER TRUNCATE ON public.lookup_values FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: lookup_values lookup_values_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER lookup_values_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.lookup_values FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: org_unit_successions org_unit_successions_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER org_unit_successions_after_truncate_audit AFTER TRUNCATE ON public.org_unit_successions FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: org_unit_successions org_unit_successions_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER org_unit_successions_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.org_unit_successions FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: org_unit_types org_unit_types_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER org_unit_types_after_truncate_audit AFTER TRUNCATE ON public.org_unit_types FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: org_unit_types org_unit_types_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER org_unit_types_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.org_unit_types FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: org_units org_units_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER org_units_after_truncate_audit AFTER TRUNCATE ON public.org_units FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: org_units org_units_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER org_units_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.org_units FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: org_units org_units_before_write_prevent_cycle; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER org_units_before_write_prevent_cycle BEFORE INSERT OR UPDATE OF parent_id ON public.org_units FOR EACH ROW EXECUTE FUNCTION util.org_units_prevent_cycle();


--
-- Name: people people_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER people_after_truncate_audit AFTER TRUNCATE ON public.people FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: people people_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER people_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.people FOR EACH ROW EXECUTE FUNCTION audit.record_change('national_id_encrypted', 'passport_number_encrypted');


--
-- Name: permissions permissions_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER permissions_after_truncate_audit AFTER TRUNCATE ON public.permissions FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: permissions permissions_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER permissions_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.permissions FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: programs programs_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER programs_after_truncate_audit AFTER TRUNCATE ON public.programs FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: programs programs_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER programs_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.programs FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: registration_holds registration_holds_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registration_holds_after_truncate_audit AFTER TRUNCATE ON public.registration_holds FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: registration_holds registration_holds_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registration_holds_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.registration_holds FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: registration_overrides registration_overrides_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registration_overrides_after_truncate_audit AFTER TRUNCATE ON public.registration_overrides FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: registration_overrides registration_overrides_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registration_overrides_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.registration_overrides FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: registration_rule_sets registration_rule_sets_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registration_rule_sets_after_truncate_audit AFTER TRUNCATE ON public.registration_rule_sets FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: registration_rule_sets registration_rule_sets_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registration_rule_sets_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.registration_rule_sets FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: registration_rules registration_rules_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registration_rules_after_truncate_audit AFTER TRUNCATE ON public.registration_rules FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: registration_rules registration_rules_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER registration_rules_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.registration_rules FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: role_assignments role_assignments_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER role_assignments_after_truncate_audit AFTER TRUNCATE ON public.role_assignments FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: role_assignments role_assignments_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER role_assignments_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.role_assignments FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: role_has_permissions role_has_permissions_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER role_has_permissions_after_truncate_audit AFTER TRUNCATE ON public.role_has_permissions FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: role_has_permissions role_has_permissions_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER role_has_permissions_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.role_has_permissions FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: roles roles_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER roles_after_truncate_audit AFTER TRUNCATE ON public.roles FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: roles roles_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER roles_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.roles FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: rooms rooms_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER rooms_after_truncate_audit AFTER TRUNCATE ON public.rooms FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: rooms rooms_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER rooms_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.rooms FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: section_instructors section_instructors_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_instructors_after_truncate_audit AFTER TRUNCATE ON public.section_instructors FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: section_instructors section_instructors_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_instructors_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.section_instructors FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: section_instructors section_instructors_after_write_check_meetings; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_instructors_after_write_check_meetings AFTER INSERT OR UPDATE OF section_id, instructor_id ON public.section_instructors FOR EACH ROW EXECUTE FUNCTION util.section_instructors_check_meetings();


--
-- Name: section_meetings section_meetings_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_meetings_after_truncate_audit AFTER TRUNCATE ON public.section_meetings FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: section_meetings section_meetings_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_meetings_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.section_meetings FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: section_meetings section_meetings_after_write_check_instructors; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_meetings_after_write_check_instructors AFTER INSERT OR UPDATE OF section_id, weekday, start_time, end_time, start_date, end_date, is_active ON public.section_meetings FOR EACH ROW EXECUTE FUNCTION util.section_meetings_check_instructors();


--
-- Name: section_seat_groups section_seat_groups_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_seat_groups_after_truncate_audit AFTER TRUNCATE ON public.section_seat_groups FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: section_seat_groups section_seat_groups_after_update_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_seat_groups_after_update_audit AFTER UPDATE ON public.section_seat_groups FOR EACH ROW WHEN (((to_jsonb(old.*) - '{enrolled_count,release_processed_at,updated_at}'::text[]) IS DISTINCT FROM (to_jsonb(new.*) - '{enrolled_count,release_processed_at,updated_at}'::text[]))) EXECUTE FUNCTION audit.record_change();


--
-- Name: section_seat_groups section_seat_groups_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER section_seat_groups_after_write_audit AFTER INSERT OR DELETE ON public.section_seat_groups FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: sections sections_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sections_after_truncate_audit AFTER TRUNCATE ON public.sections FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: sections sections_after_update_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sections_after_update_audit AFTER UPDATE ON public.sections FOR EACH ROW WHEN (((to_jsonb(old.*) - '{enrolled_count,updated_at}'::text[]) IS DISTINCT FROM (to_jsonb(new.*) - '{enrolled_count,updated_at}'::text[]))) EXECUTE FUNCTION audit.record_change();


--
-- Name: sections sections_after_update_sync_meetings; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sections_after_update_sync_meetings AFTER UPDATE OF status ON public.sections FOR EACH ROW WHEN (((old.status)::text IS DISTINCT FROM (new.status)::text)) EXECUTE FUNCTION util.sections_sync_meeting_activity();


--
-- Name: sections sections_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER sections_after_write_audit AFTER INSERT OR DELETE ON public.sections FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: settings settings_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER settings_after_truncate_audit AFTER TRUNCATE ON public.settings FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: settings settings_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER settings_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.settings FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: student_record_programs student_record_programs_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER student_record_programs_after_truncate_audit AFTER TRUNCATE ON public.student_record_programs FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: student_record_programs student_record_programs_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER student_record_programs_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.student_record_programs FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: student_records student_records_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER student_records_after_truncate_audit AFTER TRUNCATE ON public.student_records FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: student_records student_records_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER student_records_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.student_records FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: student_status_change_types student_status_change_types_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER student_status_change_types_after_truncate_audit AFTER TRUNCATE ON public.student_status_change_types FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: student_status_change_types student_status_change_types_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER student_status_change_types_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.student_status_change_types FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: student_status_changes student_status_changes_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER student_status_changes_after_truncate_audit AFTER TRUNCATE ON public.student_status_changes FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: student_status_changes student_status_changes_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER student_status_changes_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.student_status_changes FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: syllabi syllabi_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER syllabi_after_truncate_audit AFTER TRUNCATE ON public.syllabi FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: syllabi syllabi_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER syllabi_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.syllabi FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: term_evaluations term_evaluations_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_evaluations_after_truncate_audit AFTER TRUNCATE ON public.term_evaluations FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: term_evaluations term_evaluations_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_evaluations_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.term_evaluations FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: term_records term_records_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_records_after_truncate_audit AFTER TRUNCATE ON public.term_records FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: term_records term_records_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_records_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.term_records FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: term_sessions term_sessions_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_sessions_after_truncate_audit AFTER TRUNCATE ON public.term_sessions FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: term_sessions term_sessions_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_sessions_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.term_sessions FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: term_sessions term_sessions_before_write_within_term; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_sessions_before_write_within_term BEFORE INSERT OR UPDATE OF term_id, start_date, end_date ON public.term_sessions FOR EACH ROW EXECUTE FUNCTION util.term_sessions_within_term();


--
-- Name: term_types term_types_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_types_after_truncate_audit AFTER TRUNCATE ON public.term_types FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: term_types term_types_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_types_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.term_types FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: term_windows term_windows_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_windows_after_truncate_audit AFTER TRUNCATE ON public.term_windows FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: term_windows term_windows_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER term_windows_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.term_windows FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: terms terms_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER terms_after_truncate_audit AFTER TRUNCATE ON public.terms FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: terms terms_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER terms_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.terms FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: time_slots time_slots_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER time_slots_after_truncate_audit AFTER TRUNCATE ON public.time_slots FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: time_slots time_slots_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER time_slots_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.time_slots FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: user_identities user_identities_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER user_identities_after_truncate_audit AFTER TRUNCATE ON public.user_identities FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: user_identities user_identities_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER user_identities_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.user_identities FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: users users_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER users_after_truncate_audit AFTER TRUNCATE ON public.users FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: users users_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER users_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION audit.record_change('password', 'remember_token', 'two_factor_secret', 'two_factor_recovery_codes');


--
-- Name: waitlist_entries waitlist_entries_after_truncate_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER waitlist_entries_after_truncate_audit AFTER TRUNCATE ON public.waitlist_entries FOR EACH STATEMENT EXECUTE FUNCTION audit.record_change();


--
-- Name: waitlist_entries waitlist_entries_after_write_audit; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER waitlist_entries_after_write_audit AFTER INSERT OR DELETE OR UPDATE ON public.waitlist_entries FOR EACH ROW EXECUTE FUNCTION audit.record_change();


--
-- Name: account_invitations account_invitations_invited_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_invitations
    ADD CONSTRAINT account_invitations_invited_by_id_foreign FOREIGN KEY (invited_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: account_invitations account_invitations_person_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_invitations
    ADD CONSTRAINT account_invitations_person_id_foreign FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE CASCADE;


--
-- Name: additional_program_requests additional_program_requests_decided_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests
    ADD CONSTRAINT additional_program_requests_decided_by_id_foreign FOREIGN KEY (decided_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: additional_program_requests additional_program_requests_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests
    ADD CONSTRAINT additional_program_requests_org_unit_id_foreign FOREIGN KEY (org_unit_id) REFERENCES public.org_units(id) ON DELETE RESTRICT;


--
-- Name: additional_program_requests additional_program_requests_program_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests
    ADD CONSTRAINT additional_program_requests_program_id_foreign FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE RESTRICT;


--
-- Name: additional_program_requests additional_program_requests_requested_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests
    ADD CONSTRAINT additional_program_requests_requested_by_id_foreign FOREIGN KEY (requested_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: additional_program_requests additional_program_requests_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests
    ADD CONSTRAINT additional_program_requests_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: additional_program_requests additional_program_requests_student_record_program_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests
    ADD CONSTRAINT additional_program_requests_student_record_program_id_foreign FOREIGN KEY (student_record_program_id) REFERENCES public.student_record_programs(id) ON DELETE SET NULL;


--
-- Name: additional_program_requests additional_program_requests_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.additional_program_requests
    ADD CONSTRAINT additional_program_requests_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE RESTRICT;


--
-- Name: admission_cycle_document_types admission_cycle_document_types_admission_cycle_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_document_types
    ADD CONSTRAINT admission_cycle_document_types_admission_cycle_id_foreign FOREIGN KEY (admission_cycle_id) REFERENCES public.admission_cycles(id) ON DELETE CASCADE;


--
-- Name: admission_cycle_document_types admission_cycle_document_types_document_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_document_types
    ADD CONSTRAINT admission_cycle_document_types_document_type_id_foreign FOREIGN KEY (document_type_id) REFERENCES public.lookup_values(id) ON DELETE RESTRICT;


--
-- Name: admission_cycle_programs admission_cycle_programs_admission_cycle_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_programs
    ADD CONSTRAINT admission_cycle_programs_admission_cycle_id_foreign FOREIGN KEY (admission_cycle_id) REFERENCES public.admission_cycles(id) ON DELETE CASCADE;


--
-- Name: admission_cycle_programs admission_cycle_programs_program_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admission_cycle_programs
    ADD CONSTRAINT admission_cycle_programs_program_id_foreign FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE RESTRICT;


--
-- Name: advisor_assignments advisor_assignments_instructor_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.advisor_assignments
    ADD CONSTRAINT advisor_assignments_instructor_id_foreign FOREIGN KEY (instructor_id) REFERENCES public.instructors(id) ON DELETE RESTRICT;


--
-- Name: advisor_assignments advisor_assignments_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.advisor_assignments
    ADD CONSTRAINT advisor_assignments_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: application_number_sequences application_number_sequences_admission_cycle_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_number_sequences
    ADD CONSTRAINT application_number_sequences_admission_cycle_id_foreign FOREIGN KEY (admission_cycle_id) REFERENCES public.admission_cycles(id) ON DELETE CASCADE;


--
-- Name: applications applications_admission_cycle_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_admission_cycle_id_foreign FOREIGN KEY (admission_cycle_id) REFERENCES public.admission_cycles(id) ON DELETE RESTRICT;


--
-- Name: applications applications_admission_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_admission_type_id_foreign FOREIGN KEY (admission_type_id) REFERENCES public.lookup_values(id) ON DELETE SET NULL;


--
-- Name: applications applications_decided_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_decided_by_id_foreign FOREIGN KEY (decided_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: applications applications_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_org_unit_id_foreign FOREIGN KEY (org_unit_id) REFERENCES public.org_units(id) ON DELETE RESTRICT;


--
-- Name: applications applications_person_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_person_id_foreign FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE RESTRICT;


--
-- Name: applications applications_previous_school_country_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_previous_school_country_id_foreign FOREIGN KEY (previous_school_country_id) REFERENCES public.countries(id) ON DELETE SET NULL;


--
-- Name: applications applications_program_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_program_id_foreign FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE RESTRICT;


--
-- Name: applications applications_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE RESTRICT;


--
-- Name: assessment_component_scores assessment_component_scores_assessment_component_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_component_scores
    ADD CONSTRAINT assessment_component_scores_assessment_component_id_foreign FOREIGN KEY (assessment_component_id) REFERENCES public.assessment_components(id) ON DELETE RESTRICT;


--
-- Name: assessment_component_scores assessment_component_scores_assessment_result_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_component_scores
    ADD CONSTRAINT assessment_component_scores_assessment_result_id_foreign FOREIGN KEY (assessment_result_id) REFERENCES public.assessment_results(id) ON DELETE CASCADE;


--
-- Name: assessment_components assessment_components_assessment_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_components
    ADD CONSTRAINT assessment_components_assessment_type_id_foreign FOREIGN KEY (assessment_type_id) REFERENCES public.assessment_types(id) ON DELETE CASCADE;


--
-- Name: assessment_registrations assessment_registrations_assessment_session_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_registrations
    ADD CONSTRAINT assessment_registrations_assessment_session_id_foreign FOREIGN KEY (assessment_session_id) REFERENCES public.assessment_sessions(id) ON DELETE RESTRICT;


--
-- Name: assessment_registrations assessment_registrations_registered_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_registrations
    ADD CONSTRAINT assessment_registrations_registered_by_id_foreign FOREIGN KEY (registered_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: assessment_registrations assessment_registrations_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_registrations
    ADD CONSTRAINT assessment_registrations_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE RESTRICT;


--
-- Name: assessment_result_corrections assessment_result_corrections_assessment_result_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_result_corrections
    ADD CONSTRAINT assessment_result_corrections_assessment_result_id_foreign FOREIGN KEY (assessment_result_id) REFERENCES public.assessment_results(id) ON DELETE CASCADE;


--
-- Name: assessment_result_corrections assessment_result_corrections_decided_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_result_corrections
    ADD CONSTRAINT assessment_result_corrections_decided_by_id_foreign FOREIGN KEY (decided_by_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: assessment_result_corrections assessment_result_corrections_requested_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_result_corrections
    ADD CONSTRAINT assessment_result_corrections_requested_by_id_foreign FOREIGN KEY (requested_by_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: assessment_results assessment_results_assessment_registration_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_assessment_registration_id_foreign FOREIGN KEY (assessment_registration_id) REFERENCES public.assessment_registrations(id) ON DELETE RESTRICT;


--
-- Name: assessment_results assessment_results_assessment_session_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_assessment_session_id_foreign FOREIGN KEY (assessment_session_id) REFERENCES public.assessment_sessions(id) ON DELETE RESTRICT;


--
-- Name: assessment_results assessment_results_assessment_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_assessment_type_id_foreign FOREIGN KEY (assessment_type_id) REFERENCES public.assessment_types(id) ON DELETE RESTRICT;


--
-- Name: assessment_results assessment_results_entered_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_entered_by_id_foreign FOREIGN KEY (entered_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: assessment_results assessment_results_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_results
    ADD CONSTRAINT assessment_results_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE RESTRICT;


--
-- Name: assessment_sessions assessment_sessions_assessment_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_sessions
    ADD CONSTRAINT assessment_sessions_assessment_type_id_foreign FOREIGN KEY (assessment_type_id) REFERENCES public.assessment_types(id) ON DELETE RESTRICT;


--
-- Name: attendance_records attendance_records_class_meeting_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_class_meeting_id_foreign FOREIGN KEY (class_meeting_id) REFERENCES public.class_meetings(id) ON DELETE CASCADE;


--
-- Name: attendance_records attendance_records_enrollment_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_enrollment_id_foreign FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(id) ON DELETE CASCADE;


--
-- Name: attendance_records attendance_records_recorded_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_records
    ADD CONSTRAINT attendance_records_recorded_by_id_foreign FOREIGN KEY (recorded_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: cart_items cart_items_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: cart_items cart_items_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: cart_items cart_items_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- Name: certificate_issues certificate_issues_certificate_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_issues
    ADD CONSTRAINT certificate_issues_certificate_type_id_foreign FOREIGN KEY (certificate_type_id) REFERENCES public.certificate_types(id) ON DELETE RESTRICT;


--
-- Name: certificate_issues certificate_issues_issued_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_issues
    ADD CONSTRAINT certificate_issues_issued_by_id_foreign FOREIGN KEY (issued_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: certificate_issues certificate_issues_revoked_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_issues
    ADD CONSTRAINT certificate_issues_revoked_by_id_foreign FOREIGN KEY (revoked_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: certificate_issues certificate_issues_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_issues
    ADD CONSTRAINT certificate_issues_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE RESTRICT;


--
-- Name: certificate_templates certificate_templates_certificate_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.certificate_templates
    ADD CONSTRAINT certificate_templates_certificate_type_id_foreign FOREIGN KEY (certificate_type_id) REFERENCES public.certificate_types(id) ON DELETE CASCADE;


--
-- Name: class_meetings class_meetings_room_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.class_meetings
    ADD CONSTRAINT class_meetings_room_id_foreign FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE RESTRICT;


--
-- Name: class_meetings class_meetings_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.class_meetings
    ADD CONSTRAINT class_meetings_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: class_meetings class_meetings_section_meeting_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.class_meetings
    ADD CONSTRAINT class_meetings_section_meeting_id_foreign FOREIGN KEY (section_meeting_id) REFERENCES public.section_meetings(id) ON DELETE SET NULL;


--
-- Name: course_categories course_categories_parent_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_categories
    ADD CONSTRAINT course_categories_parent_id_foreign FOREIGN KEY (parent_id) REFERENCES public.course_categories(id) ON DELETE RESTRICT;


--
-- Name: course_equivalencies course_equivalencies_course_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_equivalencies
    ADD CONSTRAINT course_equivalencies_course_id_foreign FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: course_equivalencies course_equivalencies_equivalent_course_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_equivalencies
    ADD CONSTRAINT course_equivalencies_equivalent_course_id_foreign FOREIGN KEY (equivalent_course_id) REFERENCES public.courses(id) ON DELETE RESTRICT;


--
-- Name: course_requisites course_requisites_course_version_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_requisites
    ADD CONSTRAINT course_requisites_course_version_id_foreign FOREIGN KEY (course_version_id) REFERENCES public.course_versions(id) ON DELETE CASCADE;


--
-- Name: course_requisites course_requisites_required_course_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_requisites
    ADD CONSTRAINT course_requisites_required_course_id_foreign FOREIGN KEY (required_course_id) REFERENCES public.courses(id) ON DELETE RESTRICT;


--
-- Name: course_versions course_versions_course_category_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_course_category_id_foreign FOREIGN KEY (course_category_id) REFERENCES public.course_categories(id) ON DELETE RESTRICT;


--
-- Name: course_versions course_versions_course_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_course_id_foreign FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: courses courses_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_org_unit_id_foreign FOREIGN KEY (org_unit_id) REFERENCES public.org_units(id) ON DELETE RESTRICT;


--
-- Name: credit_limit_policies credit_limit_policies_term_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_limit_policies
    ADD CONSTRAINT credit_limit_policies_term_type_id_foreign FOREIGN KEY (term_type_id) REFERENCES public.term_types(id) ON DELETE RESTRICT;


--
-- Name: curriculum_requirement_courses curriculum_requirement_courses_course_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_courses
    ADD CONSTRAINT curriculum_requirement_courses_course_id_foreign FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE RESTRICT;


--
-- Name: curriculum_requirement_courses curriculum_requirement_courses_curriculum_requirement_id_foreig; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_courses
    ADD CONSTRAINT curriculum_requirement_courses_curriculum_requirement_id_foreig FOREIGN KEY (curriculum_requirement_id) REFERENCES public.curriculum_requirements(id) ON DELETE CASCADE;


--
-- Name: curriculum_requirement_sets curriculum_requirement_sets_program_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirement_sets
    ADD CONSTRAINT curriculum_requirement_sets_program_id_foreign FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE RESTRICT;


--
-- Name: curriculum_requirements curriculum_requirements_assessment_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirements
    ADD CONSTRAINT curriculum_requirements_assessment_type_id_foreign FOREIGN KEY (assessment_type_id) REFERENCES public.assessment_types(id) ON DELETE RESTRICT;


--
-- Name: curriculum_requirements curriculum_requirements_course_category_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirements
    ADD CONSTRAINT curriculum_requirements_course_category_id_foreign FOREIGN KEY (course_category_id) REFERENCES public.course_categories(id) ON DELETE RESTRICT;


--
-- Name: curriculum_requirements curriculum_requirements_curriculum_requirement_set_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.curriculum_requirements
    ADD CONSTRAINT curriculum_requirements_curriculum_requirement_set_id_foreign FOREIGN KEY (curriculum_requirement_set_id) REFERENCES public.curriculum_requirement_sets(id) ON DELETE CASCADE;


--
-- Name: degree_audits degree_audits_audited_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_audits
    ADD CONSTRAINT degree_audits_audited_by_id_foreign FOREIGN KEY (audited_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: degree_audits degree_audits_curriculum_requirement_set_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_audits
    ADD CONSTRAINT degree_audits_curriculum_requirement_set_id_foreign FOREIGN KEY (curriculum_requirement_set_id) REFERENCES public.curriculum_requirement_sets(id) ON DELETE RESTRICT;


--
-- Name: degree_audits degree_audits_program_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_audits
    ADD CONSTRAINT degree_audits_program_id_foreign FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE RESTRICT;


--
-- Name: degree_audits degree_audits_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_audits
    ADD CONSTRAINT degree_audits_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE RESTRICT;


--
-- Name: degree_audits degree_audits_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_audits
    ADD CONSTRAINT degree_audits_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE RESTRICT;


--
-- Name: degree_requirement_waivers degree_requirement_waivers_curriculum_requirement_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_requirement_waivers
    ADD CONSTRAINT degree_requirement_waivers_curriculum_requirement_id_foreign FOREIGN KEY (curriculum_requirement_id) REFERENCES public.curriculum_requirements(id) ON DELETE CASCADE;


--
-- Name: degree_requirement_waivers degree_requirement_waivers_decided_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_requirement_waivers
    ADD CONSTRAINT degree_requirement_waivers_decided_by_id_foreign FOREIGN KEY (decided_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: degree_requirement_waivers degree_requirement_waivers_lifted_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_requirement_waivers
    ADD CONSTRAINT degree_requirement_waivers_lifted_by_id_foreign FOREIGN KEY (lifted_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: degree_requirement_waivers degree_requirement_waivers_requested_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_requirement_waivers
    ADD CONSTRAINT degree_requirement_waivers_requested_by_id_foreign FOREIGN KEY (requested_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: degree_requirement_waivers degree_requirement_waivers_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.degree_requirement_waivers
    ADD CONSTRAINT degree_requirement_waivers_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: enrollments enrollments_changed_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_changed_by_id_foreign FOREIGN KEY (changed_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: enrollments enrollments_course_category_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_course_category_id_foreign FOREIGN KEY (course_category_id) REFERENCES public.course_categories(id) ON DELETE SET NULL;


--
-- Name: enrollments enrollments_course_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_course_id_foreign FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE RESTRICT;


--
-- Name: enrollments enrollments_course_version_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_course_version_id_foreign FOREIGN KEY (course_version_id) REFERENCES public.course_versions(id) ON DELETE RESTRICT;


--
-- Name: enrollments enrollments_grade_entered_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_grade_entered_by_id_foreign FOREIGN KEY (grade_entered_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: enrollments enrollments_grade_finalized_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_grade_finalized_by_id_foreign FOREIGN KEY (grade_finalized_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: enrollments enrollments_grade_scale_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_grade_scale_id_foreign FOREIGN KEY (grade_scale_id) REFERENCES public.grade_scales(id) ON DELETE RESTRICT;


--
-- Name: enrollments enrollments_grade_submitted_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_grade_submitted_by_id_foreign FOREIGN KEY (grade_submitted_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: enrollments enrollments_repeats_enrollment_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_repeats_enrollment_id_foreign FOREIGN KEY (repeats_enrollment_id) REFERENCES public.enrollments(id) ON DELETE SET NULL;


--
-- Name: enrollments enrollments_seat_group_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_seat_group_id_foreign FOREIGN KEY (seat_group_id) REFERENCES public.section_seat_groups(id) ON DELETE SET NULL;


--
-- Name: enrollments enrollments_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE RESTRICT;


--
-- Name: enrollments enrollments_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE RESTRICT;


--
-- Name: enrollments enrollments_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE RESTRICT;


--
-- Name: evaluation_answers evaluation_answers_evaluation_question_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_answers
    ADD CONSTRAINT evaluation_answers_evaluation_question_id_foreign FOREIGN KEY (evaluation_question_id) REFERENCES public.evaluation_questions(id) ON DELETE RESTRICT;


--
-- Name: evaluation_answers evaluation_answers_evaluation_response_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_answers
    ADD CONSTRAINT evaluation_answers_evaluation_response_id_foreign FOREIGN KEY (evaluation_response_id) REFERENCES public.evaluation_responses(id) ON DELETE CASCADE;


--
-- Name: evaluation_completions evaluation_completions_enrollment_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_completions
    ADD CONSTRAINT evaluation_completions_enrollment_id_foreign FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(id) ON DELETE RESTRICT;


--
-- Name: evaluation_method_requests evaluation_method_requests_decided_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_method_requests
    ADD CONSTRAINT evaluation_method_requests_decided_by_id_foreign FOREIGN KEY (decided_by_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: evaluation_method_requests evaluation_method_requests_requested_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_method_requests
    ADD CONSTRAINT evaluation_method_requests_requested_by_id_foreign FOREIGN KEY (requested_by_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: evaluation_method_requests evaluation_method_requests_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_method_requests
    ADD CONSTRAINT evaluation_method_requests_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE RESTRICT;


--
-- Name: evaluation_questions evaluation_questions_evaluation_form_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_questions
    ADD CONSTRAINT evaluation_questions_evaluation_form_id_foreign FOREIGN KEY (evaluation_form_id) REFERENCES public.evaluation_forms(id) ON DELETE CASCADE;


--
-- Name: evaluation_responses evaluation_responses_evaluation_form_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_responses
    ADD CONSTRAINT evaluation_responses_evaluation_form_id_foreign FOREIGN KEY (evaluation_form_id) REFERENCES public.evaluation_forms(id) ON DELETE RESTRICT;


--
-- Name: evaluation_responses evaluation_responses_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_responses
    ADD CONSTRAINT evaluation_responses_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE RESTRICT;


--
-- Name: evaluation_responses evaluation_responses_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_responses
    ADD CONSTRAINT evaluation_responses_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE RESTRICT;


--
-- Name: exports exports_user_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exports
    ADD CONSTRAINT exports_user_id_foreign FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: failed_import_rows failed_import_rows_import_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_import_rows
    ADD CONSTRAINT failed_import_rows_import_id_foreign FOREIGN KEY (import_id) REFERENCES public.imports(id) ON DELETE CASCADE;


--
-- Name: grade_change_requests grade_change_requests_decided_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_change_requests
    ADD CONSTRAINT grade_change_requests_decided_by_id_foreign FOREIGN KEY (decided_by_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: grade_change_requests grade_change_requests_enrollment_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_change_requests
    ADD CONSTRAINT grade_change_requests_enrollment_id_foreign FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(id) ON DELETE RESTRICT;


--
-- Name: grade_change_requests grade_change_requests_requested_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_change_requests
    ADD CONSTRAINT grade_change_requests_requested_by_id_foreign FOREIGN KEY (requested_by_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: grade_scale_items grade_scale_items_grade_scale_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_scale_items
    ADD CONSTRAINT grade_scale_items_grade_scale_id_foreign FOREIGN KEY (grade_scale_id) REFERENCES public.grade_scales(id) ON DELETE CASCADE;


--
-- Name: guardians guardians_person_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.guardians
    ADD CONSTRAINT guardians_person_id_foreign FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE CASCADE;


--
-- Name: imports imports_user_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.imports
    ADD CONSTRAINT imports_user_id_foreign FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: instructors instructors_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instructors
    ADD CONSTRAINT instructors_org_unit_id_foreign FOREIGN KEY (org_unit_id) REFERENCES public.org_units(id) ON DELETE RESTRICT;


--
-- Name: instructors instructors_person_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instructors
    ADD CONSTRAINT instructors_person_id_foreign FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE RESTRICT;


--
-- Name: lms_course_links lms_course_links_lms_platform_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_course_links
    ADD CONSTRAINT lms_course_links_lms_platform_id_foreign FOREIGN KEY (lms_platform_id) REFERENCES public.lms_platforms(id) ON DELETE CASCADE;


--
-- Name: lms_course_links lms_course_links_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_course_links
    ADD CONSTRAINT lms_course_links_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: lms_sync_logs lms_sync_logs_enrollment_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_sync_logs
    ADD CONSTRAINT lms_sync_logs_enrollment_id_foreign FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(id) ON DELETE SET NULL;


--
-- Name: lms_sync_logs lms_sync_logs_lms_platform_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_sync_logs
    ADD CONSTRAINT lms_sync_logs_lms_platform_id_foreign FOREIGN KEY (lms_platform_id) REFERENCES public.lms_platforms(id) ON DELETE CASCADE;


--
-- Name: lms_sync_logs lms_sync_logs_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_sync_logs
    ADD CONSTRAINT lms_sync_logs_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE SET NULL;


--
-- Name: lms_sync_logs lms_sync_logs_user_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_sync_logs
    ADD CONSTRAINT lms_sync_logs_user_id_foreign FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: lms_user_links lms_user_links_lms_platform_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_user_links
    ADD CONSTRAINT lms_user_links_lms_platform_id_foreign FOREIGN KEY (lms_platform_id) REFERENCES public.lms_platforms(id) ON DELETE CASCADE;


--
-- Name: lms_user_links lms_user_links_user_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lms_user_links
    ADD CONSTRAINT lms_user_links_user_id_foreign FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: lookup_values lookup_values_lookup_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lookup_values
    ADD CONSTRAINT lookup_values_lookup_type_id_foreign FOREIGN KEY (lookup_type_id) REFERENCES public.lookup_types(id) ON DELETE CASCADE;


--
-- Name: model_has_permissions model_has_permissions_permission_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_has_permissions
    ADD CONSTRAINT model_has_permissions_permission_id_foreign FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: model_has_roles model_has_roles_role_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_has_roles
    ADD CONSTRAINT model_has_roles_role_id_foreign FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: org_unit_successions org_unit_successions_predecessor_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_unit_successions
    ADD CONSTRAINT org_unit_successions_predecessor_org_unit_id_foreign FOREIGN KEY (predecessor_org_unit_id) REFERENCES public.org_units(id) ON DELETE CASCADE;


--
-- Name: org_unit_successions org_unit_successions_successor_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_unit_successions
    ADD CONSTRAINT org_unit_successions_successor_org_unit_id_foreign FOREIGN KEY (successor_org_unit_id) REFERENCES public.org_units(id) ON DELETE CASCADE;


--
-- Name: org_units org_units_org_unit_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_units
    ADD CONSTRAINT org_units_org_unit_type_id_foreign FOREIGN KEY (org_unit_type_id) REFERENCES public.org_unit_types(id) ON DELETE RESTRICT;


--
-- Name: org_units org_units_parent_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.org_units
    ADD CONSTRAINT org_units_parent_id_foreign FOREIGN KEY (parent_id) REFERENCES public.org_units(id) ON DELETE RESTRICT;


--
-- Name: people people_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: people people_ethnicity_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_ethnicity_id_foreign FOREIGN KEY (ethnicity_id) REFERENCES public.lookup_values(id) ON DELETE SET NULL;


--
-- Name: people people_merged_into_person_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_merged_into_person_id_foreign FOREIGN KEY (merged_into_person_id) REFERENCES public.people(id) ON DELETE SET NULL;


--
-- Name: people people_nationality_country_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.people
    ADD CONSTRAINT people_nationality_country_id_foreign FOREIGN KEY (nationality_country_id) REFERENCES public.countries(id) ON DELETE SET NULL;


--
-- Name: programs programs_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs
    ADD CONSTRAINT programs_org_unit_id_foreign FOREIGN KEY (org_unit_id) REFERENCES public.org_units(id) ON DELETE RESTRICT;


--
-- Name: registration_attempts registration_attempts_actor_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_attempts
    ADD CONSTRAINT registration_attempts_actor_id_foreign FOREIGN KEY (actor_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: registration_attempts registration_attempts_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_attempts
    ADD CONSTRAINT registration_attempts_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE SET NULL;


--
-- Name: registration_attempts registration_attempts_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_attempts
    ADD CONSTRAINT registration_attempts_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: registration_attempts registration_attempts_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_attempts
    ADD CONSTRAINT registration_attempts_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE SET NULL;


--
-- Name: registration_holds registration_holds_created_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_holds
    ADD CONSTRAINT registration_holds_created_by_id_foreign FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: registration_holds registration_holds_released_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_holds
    ADD CONSTRAINT registration_holds_released_by_id_foreign FOREIGN KEY (released_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: registration_holds registration_holds_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_holds
    ADD CONSTRAINT registration_holds_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: registration_overrides registration_overrides_course_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_overrides
    ADD CONSTRAINT registration_overrides_course_id_foreign FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: registration_overrides registration_overrides_granted_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_overrides
    ADD CONSTRAINT registration_overrides_granted_by_id_foreign FOREIGN KEY (granted_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: registration_overrides registration_overrides_revoked_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_overrides
    ADD CONSTRAINT registration_overrides_revoked_by_id_foreign FOREIGN KEY (revoked_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: registration_overrides registration_overrides_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_overrides
    ADD CONSTRAINT registration_overrides_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: registration_overrides registration_overrides_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_overrides
    ADD CONSTRAINT registration_overrides_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: registration_overrides registration_overrides_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_overrides
    ADD CONSTRAINT registration_overrides_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- Name: registration_rule_sets registration_rule_sets_copied_from_rule_set_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rule_sets
    ADD CONSTRAINT registration_rule_sets_copied_from_rule_set_id_foreign FOREIGN KEY (copied_from_rule_set_id) REFERENCES public.registration_rule_sets(id) ON DELETE SET NULL;


--
-- Name: registration_rule_sets registration_rule_sets_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rule_sets
    ADD CONSTRAINT registration_rule_sets_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- Name: registration_rules registration_rules_registration_rule_set_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.registration_rules
    ADD CONSTRAINT registration_rules_registration_rule_set_id_foreign FOREIGN KEY (registration_rule_set_id) REFERENCES public.registration_rule_sets(id) ON DELETE CASCADE;


--
-- Name: role_assignments role_assignments_assigned_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignments
    ADD CONSTRAINT role_assignments_assigned_by_id_foreign FOREIGN KEY (assigned_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: role_assignments role_assignments_role_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignments
    ADD CONSTRAINT role_assignments_role_id_foreign FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: role_assignments role_assignments_user_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignments
    ADD CONSTRAINT role_assignments_user_id_foreign FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: role_has_permissions role_has_permissions_permission_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_has_permissions
    ADD CONSTRAINT role_has_permissions_permission_id_foreign FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: role_has_permissions role_has_permissions_role_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_has_permissions
    ADD CONSTRAINT role_has_permissions_role_id_foreign FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: rooms rooms_building_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_building_id_foreign FOREIGN KEY (building_id) REFERENCES public.buildings(id) ON DELETE RESTRICT;


--
-- Name: rooms rooms_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_org_unit_id_foreign FOREIGN KEY (org_unit_id) REFERENCES public.org_units(id) ON DELETE SET NULL;


--
-- Name: rooms rooms_room_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_room_type_id_foreign FOREIGN KEY (room_type_id) REFERENCES public.lookup_values(id) ON DELETE SET NULL;


--
-- Name: section_instructors section_instructors_instructor_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_instructors
    ADD CONSTRAINT section_instructors_instructor_id_foreign FOREIGN KEY (instructor_id) REFERENCES public.instructors(id) ON DELETE RESTRICT;


--
-- Name: section_instructors section_instructors_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_instructors
    ADD CONSTRAINT section_instructors_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: section_meetings section_meetings_room_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_meetings
    ADD CONSTRAINT section_meetings_room_id_foreign FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE RESTRICT;


--
-- Name: section_meetings section_meetings_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_meetings
    ADD CONSTRAINT section_meetings_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: section_seat_groups section_seat_groups_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_seat_groups
    ADD CONSTRAINT section_seat_groups_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: sections sections_copied_from_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_copied_from_section_id_foreign FOREIGN KEY (copied_from_section_id) REFERENCES public.sections(id) ON DELETE SET NULL;


--
-- Name: sections sections_course_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_course_id_foreign FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE RESTRICT;


--
-- Name: sections sections_course_version_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_course_version_id_foreign FOREIGN KEY (course_version_id, course_id) REFERENCES public.course_versions(id, course_id) ON DELETE RESTRICT;


--
-- Name: sections sections_grade_exception_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_grade_exception_by_id_foreign FOREIGN KEY (grade_exception_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: sections sections_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_org_unit_id_foreign FOREIGN KEY (org_unit_id) REFERENCES public.org_units(id) ON DELETE RESTRICT;


--
-- Name: sections sections_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE RESTRICT;


--
-- Name: sections sections_term_session_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_term_session_id_foreign FOREIGN KEY (term_session_id, term_id) REFERENCES public.term_sessions(id, term_id) ON DELETE RESTRICT;


--
-- Name: student_record_programs student_record_programs_program_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_record_programs
    ADD CONSTRAINT student_record_programs_program_id_foreign FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE RESTRICT;


--
-- Name: student_record_programs student_record_programs_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_record_programs
    ADD CONSTRAINT student_record_programs_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: student_records student_records_admission_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records
    ADD CONSTRAINT student_records_admission_term_id_foreign FOREIGN KEY (admission_term_id) REFERENCES public.terms(id) ON DELETE SET NULL;


--
-- Name: student_records student_records_admission_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records
    ADD CONSTRAINT student_records_admission_type_id_foreign FOREIGN KEY (admission_type_id) REFERENCES public.lookup_values(id) ON DELETE SET NULL;


--
-- Name: student_records student_records_org_unit_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records
    ADD CONSTRAINT student_records_org_unit_id_foreign FOREIGN KEY (org_unit_id) REFERENCES public.org_units(id) ON DELETE RESTRICT;


--
-- Name: student_records student_records_person_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records
    ADD CONSTRAINT student_records_person_id_foreign FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE RESTRICT;


--
-- Name: student_records student_records_program_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_records
    ADD CONSTRAINT student_records_program_id_foreign FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE RESTRICT;


--
-- Name: student_status_changes student_status_changes_decided_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_changes
    ADD CONSTRAINT student_status_changes_decided_by_id_foreign FOREIGN KEY (decided_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: student_status_changes student_status_changes_requested_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_changes
    ADD CONSTRAINT student_status_changes_requested_by_id_foreign FOREIGN KEY (requested_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: student_status_changes student_status_changes_status_change_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_changes
    ADD CONSTRAINT student_status_changes_status_change_type_id_foreign FOREIGN KEY (status_change_type_id) REFERENCES public.student_status_change_types(id) ON DELETE RESTRICT;


--
-- Name: student_status_changes student_status_changes_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_changes
    ADD CONSTRAINT student_status_changes_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: student_status_changes student_status_changes_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_status_changes
    ADD CONSTRAINT student_status_changes_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE SET NULL;


--
-- Name: syllabi syllabi_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabi
    ADD CONSTRAINT syllabi_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: syllabi syllabi_updated_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.syllabi
    ADD CONSTRAINT syllabi_updated_by_id_foreign FOREIGN KEY (updated_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: term_evaluations term_evaluations_evaluation_form_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_evaluations
    ADD CONSTRAINT term_evaluations_evaluation_form_id_foreign FOREIGN KEY (evaluation_form_id) REFERENCES public.evaluation_forms(id) ON DELETE RESTRICT;


--
-- Name: term_evaluations term_evaluations_published_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_evaluations
    ADD CONSTRAINT term_evaluations_published_by_id_foreign FOREIGN KEY (published_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: term_evaluations term_evaluations_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_evaluations
    ADD CONSTRAINT term_evaluations_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE RESTRICT;


--
-- Name: term_records term_records_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_records
    ADD CONSTRAINT term_records_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE RESTRICT;


--
-- Name: term_records term_records_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_records
    ADD CONSTRAINT term_records_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE RESTRICT;


--
-- Name: term_sessions term_sessions_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_sessions
    ADD CONSTRAINT term_sessions_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- Name: term_windows term_windows_term_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_windows
    ADD CONSTRAINT term_windows_term_id_foreign FOREIGN KEY (term_id) REFERENCES public.terms(id) ON DELETE CASCADE;


--
-- Name: term_windows term_windows_term_session_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.term_windows
    ADD CONSTRAINT term_windows_term_session_id_foreign FOREIGN KEY (term_session_id, term_id) REFERENCES public.term_sessions(id, term_id) ON DELETE CASCADE;


--
-- Name: terms terms_academic_year_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_academic_year_id_foreign FOREIGN KEY (academic_year_id) REFERENCES public.academic_years(id) ON DELETE RESTRICT;


--
-- Name: terms terms_term_type_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_term_type_id_foreign FOREIGN KEY (term_type_id) REFERENCES public.term_types(id) ON DELETE RESTRICT;


--
-- Name: user_identities user_identities_user_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_identities
    ADD CONSTRAINT user_identities_user_id_foreign FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: users users_person_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_person_id_foreign FOREIGN KEY (person_id) REFERENCES public.people(id) ON DELETE SET NULL;


--
-- Name: waitlist_entries waitlist_entries_enrollment_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.waitlist_entries
    ADD CONSTRAINT waitlist_entries_enrollment_id_foreign FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(id) ON DELETE SET NULL;


--
-- Name: waitlist_entries waitlist_entries_requested_by_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.waitlist_entries
    ADD CONSTRAINT waitlist_entries_requested_by_id_foreign FOREIGN KEY (requested_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: waitlist_entries waitlist_entries_section_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.waitlist_entries
    ADD CONSTRAINT waitlist_entries_section_id_foreign FOREIGN KEY (section_id) REFERENCES public.sections(id) ON DELETE CASCADE;


--
-- Name: waitlist_entries waitlist_entries_student_record_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.waitlist_entries
    ADD CONSTRAINT waitlist_entries_student_record_id_foreign FOREIGN KEY (student_record_id) REFERENCES public.student_records(id) ON DELETE CASCADE;


--
-- Name: additional_program_requests; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.additional_program_requests ENABLE ROW LEVEL SECURITY;

--
-- Name: additional_program_requests additional_program_requests_approver_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY additional_program_requests_approver_select ON public.additional_program_requests FOR SELECT USING ((( SELECT util.has_permission('additional_programs.approve'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('additional_programs.approve'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('additional_programs.approve'::text, 'program'::text) AS permission_scope_ids)::bigint[]))));


--
-- Name: additional_program_requests additional_program_requests_approver_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY additional_program_requests_approver_update ON public.additional_program_requests FOR UPDATE USING ((( SELECT util.has_permission('additional_programs.approve'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('additional_programs.approve'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('additional_programs.approve'::text, 'program'::text) AS permission_scope_ids)::bigint[])))) WITH CHECK ((( SELECT util.has_permission('additional_programs.approve'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('additional_programs.approve'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('additional_programs.approve'::text, 'program'::text) AS permission_scope_ids)::bigint[]))));


--
-- Name: additional_program_requests additional_program_requests_owner_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY additional_program_requests_owner_insert ON public.additional_program_requests FOR INSERT WITH CHECK ((((status)::text = 'requested'::text) AND (requested_by_id = ( SELECT util.current_user_id() AS current_user_id)) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = additional_program_requests.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id)))))));


--
-- Name: additional_program_requests additional_program_requests_owner_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY additional_program_requests_owner_update ON public.additional_program_requests FOR UPDATE USING ((((status)::text = 'requested'::text) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = additional_program_requests.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id))))))) WITH CHECK (((status)::text = ANY ((ARRAY['requested'::character varying, 'cancelled'::character varying])::text[])));


--
-- Name: additional_program_requests additional_program_requests_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY additional_program_requests_record_select ON public.additional_program_requests FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = additional_program_requests.student_record_id))));


--
-- Name: additional_program_requests additional_program_requests_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY additional_program_requests_system_all ON public.additional_program_requests USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: applications; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;

--
-- Name: applications applications_owner_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY applications_owner_insert ON public.applications FOR INSERT WITH CHECK (((person_id = ( SELECT util.current_person_id() AS current_person_id)) AND ((status)::text = 'draft'::text)));


--
-- Name: applications applications_owner_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY applications_owner_select ON public.applications FOR SELECT USING ((person_id = ( SELECT util.current_person_id() AS current_person_id)));


--
-- Name: applications applications_owner_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY applications_owner_update ON public.applications FOR UPDATE USING (((person_id = ( SELECT util.current_person_id() AS current_person_id)) AND ((status)::text = ANY ((ARRAY['draft'::character varying, 'submitted'::character varying, 'under_review'::character varying, 'admitted'::character varying])::text[])))) WITH CHECK (((person_id = ( SELECT util.current_person_id() AS current_person_id)) AND ((status)::text = ANY ((ARRAY['draft'::character varying, 'submitted'::character varying, 'confirmed'::character varying, 'withdrawn'::character varying])::text[]))));


--
-- Name: applications applications_staff_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY applications_staff_select ON public.applications FOR SELECT USING ((( SELECT util.has_permission('applications.view'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('applications.view'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('applications.view'::text, 'program'::text) AS permission_scope_ids)::bigint[])) OR ( SELECT util.has_permission('applications.review'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('applications.review'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('applications.review'::text, 'program'::text) AS permission_scope_ids)::bigint[]))));


--
-- Name: applications applications_staff_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY applications_staff_update ON public.applications FOR UPDATE USING ((( SELECT util.has_permission('applications.review'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('applications.review'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('applications.review'::text, 'program'::text) AS permission_scope_ids)::bigint[])))) WITH CHECK ((( SELECT util.has_permission('applications.review'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('applications.review'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('applications.review'::text, 'program'::text) AS permission_scope_ids)::bigint[]))));


--
-- Name: applications applications_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY applications_system_all ON public.applications USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: assessment_component_scores; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.assessment_component_scores ENABLE ROW LEVEL SECURITY;

--
-- Name: assessment_component_scores assessment_component_scores_result_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_component_scores_result_select ON public.assessment_component_scores FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.assessment_results r
  WHERE (r.id = assessment_component_scores.assessment_result_id))));


--
-- Name: assessment_component_scores assessment_component_scores_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_component_scores_staff_write ON public.assessment_component_scores USING ((( SELECT util.has_permission('assessments.record'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.assessment_results r
  WHERE (r.id = assessment_component_scores.assessment_result_id))))) WITH CHECK ((( SELECT util.has_permission('assessments.record'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.assessment_results r
  WHERE (r.id = assessment_component_scores.assessment_result_id)))));


--
-- Name: assessment_component_scores assessment_component_scores_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_component_scores_system_all ON public.assessment_component_scores USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: assessment_registrations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.assessment_registrations ENABLE ROW LEVEL SECURITY;

--
-- Name: assessment_registrations assessment_registrations_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_registrations_record_select ON public.assessment_registrations FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = assessment_registrations.student_record_id))));


--
-- Name: assessment_registrations assessment_registrations_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_registrations_staff_write ON public.assessment_registrations USING ((( SELECT util.has_permission('assessments.record'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = assessment_registrations.student_record_id))))) WITH CHECK ((( SELECT util.has_permission('assessments.record'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = assessment_registrations.student_record_id)))));


--
-- Name: assessment_registrations assessment_registrations_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_registrations_system_all ON public.assessment_registrations USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: assessment_result_corrections; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.assessment_result_corrections ENABLE ROW LEVEL SECURITY;

--
-- Name: assessment_result_corrections assessment_result_corrections_result_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_result_corrections_result_select ON public.assessment_result_corrections FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.assessment_results r
  WHERE (r.id = assessment_result_corrections.assessment_result_id))));


--
-- Name: assessment_result_corrections assessment_result_corrections_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_result_corrections_staff_write ON public.assessment_result_corrections USING (((( SELECT util.has_permission('assessments.record'::text) AS has_permission) OR ( SELECT util.has_permission('assessments.manage'::text) AS has_permission)) AND (EXISTS ( SELECT 1
   FROM public.assessment_results r
  WHERE (r.id = assessment_result_corrections.assessment_result_id))))) WITH CHECK (((( SELECT util.has_permission('assessments.record'::text) AS has_permission) OR ( SELECT util.has_permission('assessments.manage'::text) AS has_permission)) AND (EXISTS ( SELECT 1
   FROM public.assessment_results r
  WHERE (r.id = assessment_result_corrections.assessment_result_id)))));


--
-- Name: assessment_result_corrections assessment_result_corrections_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_result_corrections_system_all ON public.assessment_result_corrections USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: assessment_results; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.assessment_results ENABLE ROW LEVEL SECURITY;

--
-- Name: assessment_results assessment_results_owner_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_results_owner_select ON public.assessment_results FOR SELECT USING (((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = assessment_results.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id))))) AND ((assessment_session_id IS NULL) OR (EXISTS ( SELECT 1
   FROM public.assessment_sessions s
  WHERE ((s.id = assessment_results.assessment_session_id) AND (s.results_published_at IS NOT NULL)))))));


--
-- Name: assessment_results assessment_results_staff_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_results_staff_select ON public.assessment_results FOR SELECT USING (((( SELECT util.has_permission('assessments.record'::text) AS has_permission) OR ( SELECT util.has_permission('assessments.manage'::text) AS has_permission)) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = assessment_results.student_record_id)))));


--
-- Name: assessment_results assessment_results_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_results_staff_write ON public.assessment_results USING ((( SELECT util.has_permission('assessments.record'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = assessment_results.student_record_id))))) WITH CHECK ((( SELECT util.has_permission('assessments.record'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = assessment_results.student_record_id)))));


--
-- Name: assessment_results assessment_results_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY assessment_results_system_all ON public.assessment_results USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: attendance_records; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.attendance_records ENABLE ROW LEVEL SECURITY;

--
-- Name: attendance_records attendance_records_enrollment_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY attendance_records_enrollment_select ON public.attendance_records FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.enrollments e
  WHERE (e.id = attendance_records.enrollment_id))));


--
-- Name: attendance_records attendance_records_instructor_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY attendance_records_instructor_write ON public.attendance_records USING ((EXISTS ( SELECT 1
   FROM ((public.class_meetings m
     JOIN public.section_instructors si ON ((si.section_id = m.section_id)))
     JOIN public.instructors i ON ((i.id = si.instructor_id)))
  WHERE ((m.id = attendance_records.class_meeting_id) AND (i.person_id = ( SELECT util.current_person_id() AS current_person_id)))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM ((public.class_meetings m
     JOIN public.section_instructors si ON ((si.section_id = m.section_id)))
     JOIN public.instructors i ON ((i.id = si.instructor_id)))
  WHERE ((m.id = attendance_records.class_meeting_id) AND (i.person_id = ( SELECT util.current_person_id() AS current_person_id))))));


--
-- Name: attendance_records attendance_records_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY attendance_records_staff_write ON public.attendance_records USING ((( SELECT util.has_permission('sections.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM (public.class_meetings m
     JOIN public.sections s ON ((s.id = m.section_id)))
  WHERE ((m.id = attendance_records.class_meeting_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('sections.manage'::text) AS permission_org_unit_ids)::bigint[]))))))) WITH CHECK ((( SELECT util.has_permission('sections.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM (public.class_meetings m
     JOIN public.sections s ON ((s.id = m.section_id)))
  WHERE ((m.id = attendance_records.class_meeting_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('sections.manage'::text) AS permission_org_unit_ids)::bigint[])))))));


--
-- Name: attendance_records attendance_records_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY attendance_records_system_all ON public.attendance_records USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: cart_items; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.cart_items ENABLE ROW LEVEL SECURITY;

--
-- Name: cart_items cart_items_owner_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY cart_items_owner_all ON public.cart_items USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = cart_items.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id)))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = cart_items.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id))))));


--
-- Name: cart_items cart_items_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY cart_items_record_select ON public.cart_items FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = cart_items.student_record_id))));


--
-- Name: cart_items cart_items_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY cart_items_system_all ON public.cart_items USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: certificate_issues; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.certificate_issues ENABLE ROW LEVEL SECURITY;

--
-- Name: certificate_issues certificate_issues_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY certificate_issues_record_select ON public.certificate_issues FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = certificate_issues.student_record_id))));


--
-- Name: certificate_issues certificate_issues_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY certificate_issues_staff_write ON public.certificate_issues USING ((( SELECT util.has_permission('certificates.issue'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = certificate_issues.student_record_id))))) WITH CHECK ((( SELECT util.has_permission('certificates.issue'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = certificate_issues.student_record_id)))));


--
-- Name: certificate_issues certificate_issues_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY certificate_issues_system_all ON public.certificate_issues USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: class_meetings; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.class_meetings ENABLE ROW LEVEL SECURITY;

--
-- Name: class_meetings class_meetings_instructor_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY class_meetings_instructor_write ON public.class_meetings USING ((EXISTS ( SELECT 1
   FROM (public.section_instructors si
     JOIN public.instructors i ON ((i.id = si.instructor_id)))
  WHERE ((si.section_id = class_meetings.section_id) AND (i.person_id = ( SELECT util.current_person_id() AS current_person_id)))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM (public.section_instructors si
     JOIN public.instructors i ON ((i.id = si.instructor_id)))
  WHERE ((si.section_id = class_meetings.section_id) AND (i.person_id = ( SELECT util.current_person_id() AS current_person_id))))));


--
-- Name: class_meetings class_meetings_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY class_meetings_select ON public.class_meetings FOR SELECT USING ((( SELECT util.current_user_id() AS current_user_id) IS NOT NULL));


--
-- Name: class_meetings class_meetings_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY class_meetings_staff_write ON public.class_meetings USING ((( SELECT util.has_permission('sections.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = class_meetings.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('sections.manage'::text) AS permission_org_unit_ids)::bigint[]))))))) WITH CHECK ((( SELECT util.has_permission('sections.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = class_meetings.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('sections.manage'::text) AS permission_org_unit_ids)::bigint[])))))));


--
-- Name: class_meetings class_meetings_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY class_meetings_system_all ON public.class_meetings USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: degree_audits; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.degree_audits ENABLE ROW LEVEL SECURITY;

--
-- Name: degree_audits degree_audits_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY degree_audits_record_select ON public.degree_audits FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = degree_audits.student_record_id))));


--
-- Name: degree_audits degree_audits_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY degree_audits_staff_write ON public.degree_audits USING ((( SELECT util.has_permission('graduation.audit'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = degree_audits.student_record_id))))) WITH CHECK ((( SELECT util.has_permission('graduation.audit'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = degree_audits.student_record_id)))));


--
-- Name: degree_audits degree_audits_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY degree_audits_system_all ON public.degree_audits USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: degree_requirement_waivers; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.degree_requirement_waivers ENABLE ROW LEVEL SECURITY;

--
-- Name: degree_requirement_waivers degree_requirement_waivers_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY degree_requirement_waivers_record_select ON public.degree_requirement_waivers FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = degree_requirement_waivers.student_record_id))));


--
-- Name: degree_requirement_waivers degree_requirement_waivers_staff_write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY degree_requirement_waivers_staff_write ON public.degree_requirement_waivers USING ((( SELECT util.has_permission('graduation.process'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = degree_requirement_waivers.student_record_id))))) WITH CHECK ((( SELECT util.has_permission('graduation.process'::text) AS has_permission) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = degree_requirement_waivers.student_record_id)))));


--
-- Name: degree_requirement_waivers degree_requirement_waivers_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY degree_requirement_waivers_system_all ON public.degree_requirement_waivers USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: enrollments; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.enrollments ENABLE ROW LEVEL SECURITY;

--
-- Name: enrollments enrollments_grades_staff_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_grades_staff_select ON public.enrollments FOR SELECT USING ((( SELECT util.has_permission('grades.view'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = enrollments.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('grades.view'::text) AS permission_org_unit_ids)::bigint[])))))));


--
-- Name: enrollments enrollments_grades_staff_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_grades_staff_update ON public.enrollments FOR UPDATE USING ((( SELECT util.has_permission('grades.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = enrollments.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('grades.manage'::text) AS permission_org_unit_ids)::bigint[]))))) OR ( SELECT util.has_permission('grade_changes.approve'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = enrollments.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('grade_changes.approve'::text) AS permission_org_unit_ids)::bigint[]))))))) WITH CHECK ((( SELECT util.has_permission('grades.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = enrollments.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('grades.manage'::text) AS permission_org_unit_ids)::bigint[]))))) OR ( SELECT util.has_permission('grade_changes.approve'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = enrollments.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('grade_changes.approve'::text) AS permission_org_unit_ids)::bigint[])))))));


--
-- Name: enrollments enrollments_instructor_grade_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_instructor_grade_update ON public.enrollments FOR UPDATE USING ((((status)::text = 'enrolled'::text) AND ((grade_status)::text = ANY ((ARRAY['none'::character varying, 'draft'::character varying])::text[])) AND (EXISTS ( SELECT 1
   FROM (public.section_instructors si
     JOIN public.instructors i ON ((i.id = si.instructor_id)))
  WHERE ((si.section_id = enrollments.section_id) AND (i.person_id = ( SELECT util.current_person_id() AS current_person_id))))))) WITH CHECK ((((status)::text = 'enrolled'::text) AND ((grade_status)::text = ANY ((ARRAY['none'::character varying, 'draft'::character varying, 'submitted'::character varying])::text[]))));


--
-- Name: enrollments enrollments_instructor_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_instructor_select ON public.enrollments FOR SELECT USING ((EXISTS ( SELECT 1
   FROM (public.section_instructors si
     JOIN public.instructors i ON ((i.id = si.instructor_id)))
  WHERE ((si.section_id = enrollments.section_id) AND (i.person_id = ( SELECT util.current_person_id() AS current_person_id))))));


--
-- Name: enrollments enrollments_owner_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_owner_insert ON public.enrollments FOR INSERT WITH CHECK ((((status)::text = 'enrolled'::text) AND ((grade_status)::text = 'none'::text) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = enrollments.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id)))))));


--
-- Name: enrollments enrollments_owner_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_owner_update ON public.enrollments FOR UPDATE USING ((((status)::text = 'enrolled'::text) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = enrollments.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id))))))) WITH CHECK ((((status)::text = ANY ((ARRAY['enrolled'::character varying, 'dropped'::character varying, 'withdrawn'::character varying])::text[])) AND ((grade_status)::text = 'none'::text) AND (grade_code IS NULL) AND (is_passed IS NULL)));


--
-- Name: enrollments enrollments_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_record_select ON public.enrollments FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = enrollments.student_record_id))));


--
-- Name: enrollments enrollments_section_staff_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_section_staff_select ON public.enrollments FOR SELECT USING ((( SELECT util.has_permission('enrollments.view'::text) AS has_permission) OR ( SELECT util.has_permission('registration.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = enrollments.section_id) AND ((s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('enrollments.view'::text) AS permission_org_unit_ids)::bigint[])) OR (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration.manage'::text) AS permission_org_unit_ids)::bigint[]))))))));


--
-- Name: enrollments enrollments_staff_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_staff_all ON public.enrollments USING ((( SELECT util.has_permission('registration.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = enrollments.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration.manage'::text) AS permission_org_unit_ids)::bigint[]))))))) WITH CHECK ((( SELECT util.has_permission('registration.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = enrollments.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration.manage'::text) AS permission_org_unit_ids)::bigint[])))))));


--
-- Name: enrollments enrollments_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY enrollments_system_all ON public.enrollments USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: evaluation_answers; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.evaluation_answers ENABLE ROW LEVEL SECURITY;

--
-- Name: evaluation_answers evaluation_answers_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY evaluation_answers_select ON public.evaluation_answers FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.evaluation_responses r
  WHERE (r.id = evaluation_answers.evaluation_response_id))));


--
-- Name: evaluation_answers evaluation_answers_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY evaluation_answers_system_all ON public.evaluation_answers USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: evaluation_completions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.evaluation_completions ENABLE ROW LEVEL SECURITY;

--
-- Name: evaluation_completions evaluation_completions_owner_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY evaluation_completions_owner_select ON public.evaluation_completions FOR SELECT USING ((EXISTS ( SELECT 1
   FROM (public.enrollments e
     JOIN public.student_records sr ON ((sr.id = e.student_record_id)))
  WHERE ((e.id = evaluation_completions.enrollment_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id))))));


--
-- Name: evaluation_completions evaluation_completions_staff_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY evaluation_completions_staff_select ON public.evaluation_completions FOR SELECT USING ((( SELECT util.has_permission('evaluations.view'::text) AS has_permission) OR ( SELECT util.has_permission('evaluations.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM (public.enrollments e
     JOIN public.sections s ON ((s.id = e.section_id)))
  WHERE ((e.id = evaluation_completions.enrollment_id) AND ((s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('evaluations.view'::text) AS permission_org_unit_ids)::bigint[])) OR (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('evaluations.manage'::text) AS permission_org_unit_ids)::bigint[]))))))));


--
-- Name: evaluation_completions evaluation_completions_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY evaluation_completions_system_all ON public.evaluation_completions USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: evaluation_responses; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.evaluation_responses ENABLE ROW LEVEL SECURITY;

--
-- Name: evaluation_responses evaluation_responses_instructor_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY evaluation_responses_instructor_select ON public.evaluation_responses FOR SELECT USING (((EXISTS ( SELECT 1
   FROM public.term_evaluations te
  WHERE ((te.term_id = evaluation_responses.term_id) AND (te.results_published_at IS NOT NULL)))) AND (EXISTS ( SELECT 1
   FROM (public.section_instructors si
     JOIN public.instructors i ON ((i.id = si.instructor_id)))
  WHERE ((si.section_id = evaluation_responses.section_id) AND (i.person_id = ( SELECT util.current_person_id() AS current_person_id)))))));


--
-- Name: evaluation_responses evaluation_responses_staff_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY evaluation_responses_staff_select ON public.evaluation_responses FOR SELECT USING ((( SELECT util.has_permission('evaluations.view'::text) AS has_permission) OR ( SELECT util.has_permission('evaluations.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = evaluation_responses.section_id) AND ((s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('evaluations.view'::text) AS permission_org_unit_ids)::bigint[])) OR (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('evaluations.manage'::text) AS permission_org_unit_ids)::bigint[]))))))));


--
-- Name: evaluation_responses evaluation_responses_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY evaluation_responses_system_all ON public.evaluation_responses USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: grade_change_requests; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.grade_change_requests ENABLE ROW LEVEL SECURITY;

--
-- Name: grade_change_requests grade_change_requests_approver_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY grade_change_requests_approver_update ON public.grade_change_requests FOR UPDATE USING ((EXISTS ( SELECT 1
   FROM (public.enrollments e
     JOIN public.sections s ON ((s.id = e.section_id)))
  WHERE ((e.id = grade_change_requests.enrollment_id) AND (( SELECT util.has_permission('grade_changes.approve'::text) AS has_permission) OR (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('grade_changes.approve'::text) AS permission_org_unit_ids)::bigint[]))))))) WITH CHECK (((decided_by_id IS NULL) OR (decided_by_id = ( SELECT util.current_user_id() AS current_user_id))));


--
-- Name: grade_change_requests grade_change_requests_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY grade_change_requests_insert ON public.grade_change_requests FOR INSERT WITH CHECK (((requested_by_id = ( SELECT util.current_user_id() AS current_user_id)) AND ((status)::text = 'pending'::text) AND (EXISTS ( SELECT 1
   FROM (public.enrollments e
     JOIN public.sections s ON ((s.id = e.section_id)))
  WHERE ((e.id = grade_change_requests.enrollment_id) AND (( SELECT util.has_permission('grade_changes.request'::text) AS has_permission) OR (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('grade_changes.request'::text) AS permission_org_unit_ids)::bigint[])) OR (EXISTS ( SELECT 1
           FROM (public.section_instructors si
             JOIN public.instructors i ON ((i.id = si.instructor_id)))
          WHERE ((si.section_id = s.id) AND (i.person_id = ( SELECT util.current_person_id() AS current_person_id)))))))))));


--
-- Name: grade_change_requests grade_change_requests_requester_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY grade_change_requests_requester_update ON public.grade_change_requests FOR UPDATE USING ((((status)::text = 'pending'::text) AND (requested_by_id = ( SELECT util.current_user_id() AS current_user_id)))) WITH CHECK ((((status)::text = ANY ((ARRAY['pending'::character varying, 'cancelled'::character varying])::text[])) AND (requested_by_id = ( SELECT util.current_user_id() AS current_user_id))));


--
-- Name: grade_change_requests grade_change_requests_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY grade_change_requests_select ON public.grade_change_requests FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.enrollments e
  WHERE (e.id = grade_change_requests.enrollment_id))));


--
-- Name: grade_change_requests grade_change_requests_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY grade_change_requests_system_all ON public.grade_change_requests USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: guardians; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.guardians ENABLE ROW LEVEL SECURITY;

--
-- Name: guardians guardians_owner_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY guardians_owner_all ON public.guardians USING ((person_id = ( SELECT util.current_person_id() AS current_person_id))) WITH CHECK ((person_id = ( SELECT util.current_person_id() AS current_person_id)));


--
-- Name: guardians guardians_person_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY guardians_person_select ON public.guardians FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.people p
  WHERE (p.id = guardians.person_id))));


--
-- Name: guardians guardians_staff_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY guardians_staff_all ON public.guardians USING ((( SELECT util.has_permission('people.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.person_id = guardians.person_id) AND (( SELECT util.has_permission('student_records.manage'::text) AS has_permission) OR (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_records.manage'::text) AS permission_org_unit_ids)::bigint[])) OR (sr.program_id = ANY (( SELECT util.permission_scope_ids('student_records.manage'::text, 'program'::text) AS permission_scope_ids)::bigint[])))))))) WITH CHECK ((( SELECT util.has_permission('people.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.person_id = guardians.person_id) AND (( SELECT util.has_permission('student_records.manage'::text) AS has_permission) OR (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_records.manage'::text) AS permission_org_unit_ids)::bigint[])) OR (sr.program_id = ANY (( SELECT util.permission_scope_ids('student_records.manage'::text, 'program'::text) AS permission_scope_ids)::bigint[]))))))));


--
-- Name: guardians guardians_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY guardians_system_all ON public.guardians USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: lms_course_links; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.lms_course_links ENABLE ROW LEVEL SECURITY;

--
-- Name: lms_course_links lms_course_links_manage; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY lms_course_links_manage ON public.lms_course_links USING (( SELECT util.has_permission('lms.manage'::text) AS has_permission)) WITH CHECK (( SELECT util.has_permission('lms.manage'::text) AS has_permission));


--
-- Name: lms_course_links lms_course_links_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY lms_course_links_select ON public.lms_course_links FOR SELECT USING ((( SELECT util.current_user_id() AS current_user_id) IS NOT NULL));


--
-- Name: lms_course_links lms_course_links_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY lms_course_links_system_all ON public.lms_course_links USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: lms_sync_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.lms_sync_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: lms_sync_logs lms_sync_logs_manage; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY lms_sync_logs_manage ON public.lms_sync_logs USING (( SELECT util.has_permission('lms.manage'::text) AS has_permission)) WITH CHECK (( SELECT util.has_permission('lms.manage'::text) AS has_permission));


--
-- Name: lms_sync_logs lms_sync_logs_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY lms_sync_logs_system_all ON public.lms_sync_logs USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: lms_user_links; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.lms_user_links ENABLE ROW LEVEL SECURITY;

--
-- Name: lms_user_links lms_user_links_manage; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY lms_user_links_manage ON public.lms_user_links USING (( SELECT util.has_permission('lms.manage'::text) AS has_permission)) WITH CHECK (( SELECT util.has_permission('lms.manage'::text) AS has_permission));


--
-- Name: lms_user_links lms_user_links_owner_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY lms_user_links_owner_select ON public.lms_user_links FOR SELECT USING ((user_id = ( SELECT util.current_user_id() AS current_user_id)));


--
-- Name: lms_user_links lms_user_links_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY lms_user_links_system_all ON public.lms_user_links USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: people; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.people ENABLE ROW LEVEL SECURITY;

--
-- Name: people people_creator_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_creator_select ON public.people FOR SELECT USING ((created_by_id = ( SELECT util.current_user_id() AS current_user_id)));


--
-- Name: people people_instructors_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_instructors_select ON public.people FOR SELECT USING (((( SELECT util.current_user_id() AS current_user_id) IS NOT NULL) AND (EXISTS ( SELECT 1
   FROM public.instructors i
  WHERE (i.person_id = people.id)))));


--
-- Name: people people_manager_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_manager_all ON public.people USING (( SELECT util.has_permission('people.manage'::text) AS has_permission)) WITH CHECK (( SELECT util.has_permission('people.manage'::text) AS has_permission));


--
-- Name: people people_owner_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_owner_select ON public.people FOR SELECT USING ((id = ( SELECT util.current_person_id() AS current_person_id)));


--
-- Name: people people_owner_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_owner_update ON public.people FOR UPDATE USING ((id = ( SELECT util.current_person_id() AS current_person_id))) WITH CHECK ((id = ( SELECT util.current_person_id() AS current_person_id)));


--
-- Name: people people_record_manager_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_record_manager_insert ON public.people FOR INSERT WITH CHECK ((( SELECT util.has_permission('student_records.manage'::text) AS has_permission) OR (cardinality(( SELECT util.permission_org_unit_ids('student_records.manage'::text) AS permission_org_unit_ids)) > 0) OR (cardinality(( SELECT util.permission_scope_ids('student_records.manage'::text, 'program'::text) AS permission_scope_ids)) > 0)));


--
-- Name: people people_record_manager_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_record_manager_update ON public.people FOR UPDATE USING (((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.person_id = people.id) AND (( SELECT util.has_permission('student_records.manage'::text) AS has_permission) OR (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_records.manage'::text) AS permission_org_unit_ids)::bigint[])) OR (sr.program_id = ANY (( SELECT util.permission_scope_ids('student_records.manage'::text, 'program'::text) AS permission_scope_ids)::bigint[])))))) OR (created_by_id = ( SELECT util.current_user_id() AS current_user_id))));


--
-- Name: people people_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_system_all ON public.people USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: people people_via_applications_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_via_applications_select ON public.people FOR SELECT USING ((id IN ( SELECT a.person_id
   FROM public.applications a)));


--
-- Name: people people_via_student_records_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_via_student_records_select ON public.people FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.person_id = people.id))));


--
-- Name: people people_viewer_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY people_viewer_select ON public.people FOR SELECT USING (( SELECT util.has_permission('people.view'::text) AS has_permission));


--
-- Name: registration_attempts; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.registration_attempts ENABLE ROW LEVEL SECURITY;

--
-- Name: registration_attempts registration_attempts_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY registration_attempts_insert ON public.registration_attempts FOR INSERT WITH CHECK (((NOT (actor_id IS DISTINCT FROM ( SELECT util.current_user_id() AS current_user_id))) OR ( SELECT util.is_system_context() AS is_system_context)));


--
-- Name: registration_attempts registration_attempts_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY registration_attempts_record_select ON public.registration_attempts FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = registration_attempts.student_record_id))));


--
-- Name: registration_holds; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.registration_holds ENABLE ROW LEVEL SECURITY;

--
-- Name: registration_holds registration_holds_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY registration_holds_record_select ON public.registration_holds FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = registration_holds.student_record_id))));


--
-- Name: registration_holds registration_holds_staff_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY registration_holds_staff_all ON public.registration_holds USING ((( SELECT util.has_permission('registration_holds.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = registration_holds.student_record_id) AND (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration_holds.manage'::text) AS permission_org_unit_ids)::bigint[]))))))) WITH CHECK ((( SELECT util.has_permission('registration_holds.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = registration_holds.student_record_id) AND (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration_holds.manage'::text) AS permission_org_unit_ids)::bigint[])))))));


--
-- Name: registration_holds registration_holds_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY registration_holds_system_all ON public.registration_holds USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: registration_overrides; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.registration_overrides ENABLE ROW LEVEL SECURITY;

--
-- Name: registration_overrides registration_overrides_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY registration_overrides_record_select ON public.registration_overrides FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = registration_overrides.student_record_id))));


--
-- Name: registration_overrides registration_overrides_staff_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY registration_overrides_staff_all ON public.registration_overrides USING ((( SELECT util.has_permission('registration_holds.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = registration_overrides.student_record_id) AND (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration_holds.manage'::text) AS permission_org_unit_ids)::bigint[]))))))) WITH CHECK ((( SELECT util.has_permission('registration_holds.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = registration_overrides.student_record_id) AND (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration_holds.manage'::text) AS permission_org_unit_ids)::bigint[])))))));


--
-- Name: registration_overrides registration_overrides_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY registration_overrides_system_all ON public.registration_overrides USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: student_records; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.student_records ENABLE ROW LEVEL SECURITY;

--
-- Name: student_records student_records_additional_programs_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_records_additional_programs_select ON public.student_records FOR SELECT USING ((id IN ( SELECT srp.student_record_id
   FROM (public.student_record_programs srp
     JOIN public.programs p ON ((p.id = srp.program_id)))
  WHERE ((srp.end_date IS NULL) AND ((p.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_records.view'::text) AS permission_org_unit_ids)::bigint[])) OR (srp.program_id = ANY (( SELECT util.permission_scope_ids('student_records.view'::text, 'program'::text) AS permission_scope_ids)::bigint[])) OR (p.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_records.manage'::text) AS permission_org_unit_ids)::bigint[])) OR (srp.program_id = ANY (( SELECT util.permission_scope_ids('student_records.manage'::text, 'program'::text) AS permission_scope_ids)::bigint[])))))));


--
-- Name: student_records student_records_advisor_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_records_advisor_select ON public.student_records FOR SELECT USING ((id IN ( SELECT aa.student_record_id
   FROM (public.advisor_assignments aa
     JOIN public.instructors i ON ((i.id = aa.instructor_id)))
  WHERE ((i.person_id = ( SELECT util.current_person_id() AS current_person_id)) AND (aa.start_date <= CURRENT_DATE) AND ((aa.end_date IS NULL) OR (aa.end_date >= CURRENT_DATE))))));


--
-- Name: student_records student_records_instructor_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_records_instructor_select ON public.student_records FOR SELECT USING ((id IN ( SELECT util.taught_student_record_ids() AS taught_student_record_ids)));


--
-- Name: student_records student_records_owner_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_records_owner_select ON public.student_records FOR SELECT USING ((person_id = ( SELECT util.current_person_id() AS current_person_id)));


--
-- Name: student_records student_records_requested_programs_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_records_requested_programs_select ON public.student_records FOR SELECT USING ((id = ANY (( SELECT util.additional_program_request_record_ids() AS additional_program_request_record_ids)::bigint[])));


--
-- Name: student_records student_records_staff_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_records_staff_all ON public.student_records USING ((( SELECT util.has_permission('student_records.manage'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_records.manage'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('student_records.manage'::text, 'program'::text) AS permission_scope_ids)::bigint[])))) WITH CHECK ((( SELECT util.has_permission('student_records.manage'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_records.manage'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('student_records.manage'::text, 'program'::text) AS permission_scope_ids)::bigint[]))));


--
-- Name: student_records student_records_staff_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_records_staff_select ON public.student_records FOR SELECT USING ((( SELECT util.has_permission('student_records.view'::text) AS has_permission) OR (org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_records.view'::text) AS permission_org_unit_ids)::bigint[])) OR (program_id = ANY (( SELECT util.permission_scope_ids('student_records.view'::text, 'program'::text) AS permission_scope_ids)::bigint[]))));


--
-- Name: student_records student_records_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_records_system_all ON public.student_records USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: student_status_changes; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.student_status_changes ENABLE ROW LEVEL SECURITY;

--
-- Name: student_status_changes student_status_changes_owner_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_status_changes_owner_insert ON public.student_status_changes FOR INSERT WITH CHECK (((requested_by_id = ( SELECT util.current_user_id() AS current_user_id)) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = student_status_changes.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id)))))));


--
-- Name: student_status_changes student_status_changes_owner_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_status_changes_owner_update ON public.student_status_changes FOR UPDATE USING (((requested_by_id = ( SELECT util.current_user_id() AS current_user_id)) AND ((status)::text = 'requested'::text))) WITH CHECK ((requested_by_id = ( SELECT util.current_user_id() AS current_user_id)));


--
-- Name: student_status_changes student_status_changes_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_status_changes_record_select ON public.student_status_changes FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = student_status_changes.student_record_id))));


--
-- Name: student_status_changes student_status_changes_staff_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_status_changes_staff_all ON public.student_status_changes USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = student_status_changes.student_record_id) AND (( SELECT util.has_permission('student_status_changes.approve'::text) AS has_permission) OR (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_status_changes.approve'::text) AS permission_org_unit_ids)::bigint[])) OR (sr.program_id = ANY (( SELECT util.permission_scope_ids('student_status_changes.approve'::text, 'program'::text) AS permission_scope_ids)::bigint[]))))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = student_status_changes.student_record_id) AND (( SELECT util.has_permission('student_status_changes.approve'::text) AS has_permission) OR (sr.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('student_status_changes.approve'::text) AS permission_org_unit_ids)::bigint[])) OR (sr.program_id = ANY (( SELECT util.permission_scope_ids('student_status_changes.approve'::text, 'program'::text) AS permission_scope_ids)::bigint[])))))));


--
-- Name: student_status_changes student_status_changes_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY student_status_changes_system_all ON public.student_status_changes USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: term_records; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.term_records ENABLE ROW LEVEL SECURITY;

--
-- Name: term_records term_records_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY term_records_record_select ON public.term_records FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = term_records.student_record_id))));


--
-- Name: term_records term_records_staff_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY term_records_staff_all ON public.term_records USING (( SELECT util.has_permission('grades.manage'::text) AS has_permission)) WITH CHECK (( SELECT util.has_permission('grades.manage'::text) AS has_permission));


--
-- Name: term_records term_records_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY term_records_system_all ON public.term_records USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- Name: waitlist_entries; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.waitlist_entries ENABLE ROW LEVEL SECURITY;

--
-- Name: waitlist_entries waitlist_entries_owner_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY waitlist_entries_owner_insert ON public.waitlist_entries FOR INSERT WITH CHECK ((((status)::text = 'waiting'::text) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = waitlist_entries.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id)))))));


--
-- Name: waitlist_entries waitlist_entries_owner_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY waitlist_entries_owner_update ON public.waitlist_entries FOR UPDATE USING ((((status)::text = 'waiting'::text) AND (EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE ((sr.id = waitlist_entries.student_record_id) AND (sr.person_id = ( SELECT util.current_person_id() AS current_person_id))))))) WITH CHECK (((status)::text = ANY ((ARRAY['waiting'::character varying, 'removed'::character varying])::text[])));


--
-- Name: waitlist_entries waitlist_entries_record_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY waitlist_entries_record_select ON public.waitlist_entries FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.student_records sr
  WHERE (sr.id = waitlist_entries.student_record_id))));


--
-- Name: waitlist_entries waitlist_entries_staff_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY waitlist_entries_staff_all ON public.waitlist_entries USING ((( SELECT util.has_permission('registration.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = waitlist_entries.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration.manage'::text) AS permission_org_unit_ids)::bigint[]))))))) WITH CHECK ((( SELECT util.has_permission('registration.manage'::text) AS has_permission) OR (EXISTS ( SELECT 1
   FROM public.sections s
  WHERE ((s.id = waitlist_entries.section_id) AND (s.org_unit_id = ANY (( SELECT util.permission_org_unit_ids('registration.manage'::text) AS permission_org_unit_ids)::bigint[])))))));


--
-- Name: waitlist_entries waitlist_entries_system_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY waitlist_entries_system_all ON public.waitlist_entries USING (( SELECT util.is_system_context() AS is_system_context)) WITH CHECK (( SELECT util.is_system_context() AS is_system_context));


--
-- PostgreSQL database dump complete
--


