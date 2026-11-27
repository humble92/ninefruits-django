ALTER TABLE instructors ADD COLUMN academic_title jsonb;
ALTER TABLE instructors ADD CONSTRAINT instructors_academic_title_object_check
    CHECK (academic_title IS NULL OR jsonb_typeof(academic_title) = 'object');

UPDATE instructors
SET academic_title = lookup_values.name
FROM lookup_values
WHERE instructors.academic_title_id = lookup_values.id;

ALTER TABLE instructors DROP COLUMN academic_title_id;
