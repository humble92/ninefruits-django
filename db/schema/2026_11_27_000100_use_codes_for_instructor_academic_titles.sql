ALTER TABLE instructors ADD COLUMN academic_title_id bigint;
ALTER TABLE instructors ADD CONSTRAINT instructors_academic_title_id_foreign
    FOREIGN KEY (academic_title_id) REFERENCES lookup_values (id) ON DELETE RESTRICT;
CREATE INDEX instructors_academic_title_id_index ON instructors (academic_title_id);

INSERT INTO lookup_types (code, name, is_system, created_at, updated_at)
VALUES ('academic_title', '{"en":"Academic title","ko":"직위","zh-hans":"职称"}', true, now(), now())
ON CONFLICT (code) DO UPDATE SET is_system = true;

INSERT INTO lookup_values (lookup_type_id, code, name, created_at, updated_at)
SELECT DISTINCT types.id, 'legacy_' || md5(instructors.academic_title::text), instructors.academic_title, now(), now()
FROM instructors
CROSS JOIN lookup_types AS types
WHERE types.code = 'academic_title' AND instructors.academic_title IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM lookup_values AS existing
        WHERE existing.lookup_type_id = types.id AND existing.name = instructors.academic_title
    )
ON CONFLICT (lookup_type_id, code) DO NOTHING;

UPDATE instructors
SET academic_title_id = matches.id
FROM (
    SELECT DISTINCT ON (titles.name) titles.name, titles.id
    FROM lookup_values AS titles
    JOIN lookup_types AS types ON types.id = titles.lookup_type_id
    WHERE types.code = 'academic_title'
    ORDER BY titles.name, titles.is_active DESC, titles.id
) AS matches
WHERE instructors.academic_title = matches.name;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM instructors WHERE academic_title IS NOT NULL AND academic_title_id IS NULL) THEN
        RAISE EXCEPTION 'An existing academic title could not be assigned a code.';
    END IF;
END;
$$;

ALTER TABLE instructors DROP COLUMN academic_title;
