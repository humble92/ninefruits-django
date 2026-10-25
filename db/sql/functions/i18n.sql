-- Localized value lookup for translatable jsonb columns ({"en": "...", "ko": "..."}).
-- Order: requested locale, base language (zh_CN -> zh), fallback locale, first non-empty value by key.

CREATE OR REPLACE FUNCTION util.i18n(value jsonb, locale text, fallback text DEFAULT 'en') RETURNS text
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

-- Uses the session settings app.locale and app.fallback_locale. For reporting views and ad hoc SQL:
--   SET app.locale = 'ko';
CREATE OR REPLACE FUNCTION util.i18n(value jsonb) RETURNS text
    LANGUAGE sql STABLE PARALLEL SAFE
AS $$
    SELECT util.i18n(
        value,
        COALESCE(NULLIF(current_setting('app.locale', true), ''), 'en'),
        COALESCE(NULLIF(current_setting('app.fallback_locale', true), ''), 'en')
    )
$$;

-- All translations joined, for language independent partial search with a pg_trgm GIN index:
--   CREATE INDEX ... USING gin (util.i18n_search_text(name) gin_trgm_ops);
CREATE OR REPLACE FUNCTION util.i18n_search_text(value jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$
    SELECT COALESCE(string_agg(e.v, ' ' ORDER BY e.k), '')
    FROM jsonb_each_text(CASE WHEN jsonb_typeof(value) = 'object' THEN value ELSE '{}'::jsonb END) AS e(k, v)
$$;
