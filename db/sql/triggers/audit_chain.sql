-- Tamper evidence for the audit tables (docs/manual/ko/operations/audit-and-maintenance.md).
--
-- Every row gets row_hash at insert: SHA-256 of its content (jsonb text, sorted keys,
-- without the hash columns). audit:seal then links rows in id order:
-- chain_hash = SHA-256(previous chain_hash || row_hash). audit:verify-chain recomputes both,
-- so an edited or removed row shows up. Maintenance (sealing, pruning) runs on the schema
-- owner's connection with app.audit_maintenance = on; the runtime role has no UPDATE or
-- DELETE on these tables anyway.

CREATE OR REPLACE FUNCTION audit.row_hash_of(content jsonb) RETURNS char(64)
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$
    SELECT encode(sha256(convert_to((content - 'row_hash' - 'chain_hash' - 'sealed_at')::text, 'UTF8')), 'hex')
$$;

CREATE OR REPLACE FUNCTION audit.set_row_hash() RETURNS trigger
    LANGUAGE plpgsql
AS $$
BEGIN
    NEW.chain_hash := NULL;
    NEW.sealed_at := NULL;
    NEW.row_hash := audit.row_hash_of(to_jsonb(NEW));
    RETURN NEW;
END
$$;

-- Append-only, except maintenance by the schema owner.
CREATE OR REPLACE FUNCTION audit.prevent_modification() RETURNS trigger
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

-- Links unsealed rows to the chain, in id order. Returns how many were sealed.
CREATE OR REPLACE FUNCTION audit.seal(target regclass) RETURNS bigint
    LANGUAGE plpgsql
AS $$
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
$$;

-- Recomputes every row hash and the chain. The first remaining row's link is taken as
-- given (rows before it may have been pruned).
CREATE OR REPLACE FUNCTION audit.verify_chain(target regclass, OUT checked bigint, OUT sealed bigint, OUT row_mismatches bigint, OUT chain_mismatches bigint, OUT first_bad_id bigint)
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
