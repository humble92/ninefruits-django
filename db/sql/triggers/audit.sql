-- Data audit: every INSERT, UPDATE, DELETE and TRUNCATE on an audited table is written to
-- audit.record_changes, including changes made outside the application.
--
-- Enable per table (trigger name: {table}_after_write_audit):
--   SELECT util.enable_audit('users', ARRAY['password', 'remember_token']);
-- Values of the listed columns are stored as "[redacted]". A third argument lists columns
-- whose changes alone are not recorded (see enable_audit).

CREATE OR REPLACE FUNCTION audit.record_change() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, pg_temp
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

-- The two-argument version (before ignored_columns) would make calls ambiguous.
DROP FUNCTION IF EXISTS util.enable_audit(regclass, text[]);

-- ignored_columns: an UPDATE that changes only these columns is not recorded (e.g. seat
-- counters changed on every registration). Other changes to the row are recorded in full.
CREATE OR REPLACE FUNCTION util.enable_audit(target regclass, redacted_columns text[] DEFAULT '{}', ignored_columns text[] DEFAULT '{}') RETURNS void
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

-- Audit tables are append-only. Attached as {table}_before_change_prevent_modification.
CREATE OR REPLACE FUNCTION audit.prevent_modification() RETURNS trigger
    LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Audit records are append-only: %.%', TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END
$$;
