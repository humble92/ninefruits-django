-- Org unit hierarchy. Scope assignments on an org unit cover its descendants.

-- The given units and every unit below them (any depth).
CREATE OR REPLACE FUNCTION util.org_unit_descendant_ids(root_ids bigint[]) RETURNS bigint[]
    LANGUAGE sql STABLE PARALLEL SAFE
AS $$
    WITH RECURSIVE tree (id) AS (
        SELECT o.id FROM public.org_units AS o WHERE o.id = ANY (root_ids)
        UNION
        SELECT child.id FROM public.org_units AS child JOIN tree ON child.parent_id = tree.id
    )
    SELECT COALESCE(array_agg(tree.id), '{}') FROM tree
$$;

-- The unit and every unit above it, nearest first.
CREATE OR REPLACE FUNCTION util.org_unit_ancestor_ids(start_id bigint) RETURNS bigint[]
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

-- Trigger org_units_before_write_prevent_cycle: a unit cannot be placed under itself or a descendant.
CREATE OR REPLACE FUNCTION util.org_units_prevent_cycle() RETURNS trigger
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

-- Org units (with descendants) where the current user has the permission. For RLS policies:
--   USING (org_unit_id = ANY ((SELECT util.permission_org_unit_ids('student_records.view'))::bigint[]))
CREATE OR REPLACE FUNCTION util.permission_org_unit_ids(permission_name text) RETURNS bigint[]
    LANGUAGE sql STABLE PARALLEL SAFE
AS $$
    SELECT util.org_unit_descendant_ids(util.permission_scope_ids(permission_name, 'org_unit'))
$$;
