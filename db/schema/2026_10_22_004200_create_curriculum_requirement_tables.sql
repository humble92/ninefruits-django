create table "curriculum_requirement_sets" ("id" bigserial not null primary key, "program_id" bigint not null, "program_role" varchar(16) not null, "catalog_year_from" smallint not null, "catalog_year_to" smallint null, "name" jsonb not null, "total_credits" decimal(5, 1) null, "note" jsonb null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "curriculum_requirement_sets" add constraint "curriculum_requirement_sets_program_id_foreign" foreign key ("program_id") references "programs" ("id") on delete restrict;

create index "curriculum_requirement_sets_program_id_program_role_index" on "curriculum_requirement_sets" ("program_id", "program_role");

create table "curriculum_requirements" ("id" bigserial not null primary key, "curriculum_requirement_set_id" bigint not null, "kind" varchar(32) not null, "name" jsonb null, "course_category_id" bigint null, "min_credits" decimal(5, 1) null, "min_courses" smallint null, "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "curriculum_requirements" add constraint "curriculum_requirements_curriculum_requirement_set_id_foreign" foreign key ("curriculum_requirement_set_id") references "curriculum_requirement_sets" ("id") on delete cascade;

alter table "curriculum_requirements" add constraint "curriculum_requirements_course_category_id_foreign" foreign key ("course_category_id") references "course_categories" ("id") on delete restrict;

create index "curriculum_requirements_curriculum_requirement_set_id_index" on "curriculum_requirements" ("curriculum_requirement_set_id");

create table "curriculum_requirement_courses" ("id" bigserial not null primary key, "curriculum_requirement_id" bigint not null, "course_id" bigint not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "curriculum_requirement_courses" add constraint "curriculum_requirement_courses_curriculum_requirement_id_foreign" foreign key ("curriculum_requirement_id") references "curriculum_requirements" ("id") on delete cascade;

alter table "curriculum_requirement_courses" add constraint "curriculum_requirement_courses_course_id_foreign" foreign key ("course_id") references "courses" ("id") on delete restrict;

alter table "curriculum_requirement_courses" add constraint "curriculum_requirement_courses_curriculum_requirement_id_course_id_unique" unique ("curriculum_requirement_id", "course_id");

ALTER TABLE curriculum_requirement_sets ADD CONSTRAINT curriculum_requirement_sets_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE curriculum_requirement_sets ADD CONSTRAINT curriculum_requirement_sets_note_object_check CHECK (note IS NULL OR jsonb_typeof(note) = 'object');

ALTER TABLE curriculum_requirements ADD CONSTRAINT curriculum_requirements_name_object_check CHECK (name IS NULL OR jsonb_typeof(name) = 'object');

ALTER TABLE curriculum_requirement_sets
    ADD COLUMN catalog_years int4range GENERATED ALWAYS AS (int4range(catalog_year_from, catalog_year_to, '[]')) STORED,
    ADD CONSTRAINT curriculum_requirement_sets_role_check CHECK (program_role IN ('primary', 'second_major', 'minor')),
    ADD CONSTRAINT curriculum_requirement_sets_years_check CHECK (catalog_year_to IS NULL OR catalog_year_to >= catalog_year_from),
    ADD CONSTRAINT curriculum_requirement_sets_no_overlap_excl EXCLUDE USING gist (program_id WITH =, program_role WITH =, catalog_years WITH &&);

ALTER TABLE curriculum_requirements ADD CONSTRAINT curriculum_requirements_kind_check CHECK (
    (kind = 'category_credits' AND course_category_id IS NOT NULL AND min_credits IS NOT NULL)
    OR (kind = 'required_courses' AND course_category_id IS NULL)
    OR (kind = 'course_group' AND course_category_id IS NULL AND (min_credits IS NOT NULL OR min_courses IS NOT NULL))
);

SELECT util.enable_audit('curriculum_requirement_sets'::regclass);

SELECT util.enable_audit('curriculum_requirements'::regclass);

SELECT util.enable_audit('curriculum_requirement_courses'::regclass);

