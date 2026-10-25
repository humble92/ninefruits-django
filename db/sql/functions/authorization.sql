-- Permission checks for row level security policies. They mirror
-- App\Domain\Security\Services\AuthorizationService (role assignments with scope and period).
-- Persona access ("own records") is expressed in each table's policy, e.g.
--   USING (user_id = util.current_user_id())

-- True when the current user has the permission with global scope.
CREATE OR REPLACE FUNCTION util.has_permission(permission_name text) RETURNS boolean
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

-- Scope ids (org units or programs) where the current user has the permission.
CREATE OR REPLACE FUNCTION util.permission_scope_ids(permission_name text, scope_type text) RETURNS bigint[]
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
