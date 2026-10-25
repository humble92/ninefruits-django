-- Request context set by App\Support\Database\DatabaseSessionContext.
-- Row level security policies and audit triggers read these values.

CREATE OR REPLACE FUNCTION util.current_user_id() RETURNS bigint
    LANGUAGE sql STABLE PARALLEL SAFE
AS $$
    SELECT NULLIF(current_setting('app.user_id', true), '')::bigint
$$;

CREATE OR REPLACE FUNCTION util.current_actor() RETURNS text
    LANGUAGE sql STABLE PARALLEL SAFE
AS $$
    SELECT NULLIF(current_setting('app.actor', true), '')
$$;

CREATE OR REPLACE FUNCTION util.current_request_id() RETURNS text
    LANGUAGE sql STABLE PARALLEL SAFE
AS $$
    SELECT NULLIF(current_setting('app.request_id', true), '')
$$;

-- True for queued jobs, scheduled tasks and console commands (app.actor = 'system:...').
CREATE OR REPLACE FUNCTION util.is_system_context() RETURNS boolean
    LANGUAGE sql STABLE PARALLEL SAFE
AS $$
    SELECT COALESCE(util.current_actor() LIKE 'system:%', false)
$$;
