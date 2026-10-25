create table "courses" ("id" bigserial not null primary key, "code" varchar(32) not null, "org_unit_id" bigint not null, "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "courses" add constraint "courses_org_unit_id_foreign" foreign key ("org_unit_id") references "org_units" ("id") on delete restrict;

alter table "courses" add constraint "courses_code_unique" unique ("code");

create table "course_versions" ("id" bigserial not null primary key, "course_id" bigint not null, "effective_start_date" date not null, "effective_end_date" date null, "title" jsonb not null, "description" jsonb null, "credits" decimal(4, 1) not null, "lecture_hours" decimal(4, 1) not null default '0', "lab_hours" decimal(4, 1) not null default '0', "course_category_id" bigint null, "grading_basis" varchar(16) not null default 'graded', "counts_toward_credit_limit" boolean not null default '1', "is_repeatable" boolean not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "course_versions" add constraint "course_versions_course_id_foreign" foreign key ("course_id") references "courses" ("id") on delete cascade;

alter table "course_versions" add constraint "course_versions_course_category_id_foreign" foreign key ("course_category_id") references "course_categories" ("id") on delete restrict;

create index "course_versions_course_id_index" on "course_versions" ("course_id");

alter table "course_versions" add constraint "course_versions_id_course_id_unique" unique ("id", "course_id");

create table "course_requisites" ("id" bigserial not null primary key, "course_version_id" bigint not null, "kind" varchar(16) not null, "group_number" smallint not null default '1', "required_course_id" bigint not null, "minimum_grade" varchar(8) null, "allows_concurrent" boolean not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "course_requisites" add constraint "course_requisites_course_version_id_foreign" foreign key ("course_version_id") references "course_versions" ("id") on delete cascade;

alter table "course_requisites" add constraint "course_requisites_required_course_id_foreign" foreign key ("required_course_id") references "courses" ("id") on delete restrict;

alter table "course_requisites" add constraint "course_requisites_course_version_id_kind_group_number_required_course_id_unique" unique ("course_version_id", "kind", "group_number", "required_course_id");

create table "course_equivalencies" ("id" bigserial not null primary key, "course_id" bigint not null, "equivalent_course_id" bigint not null, "is_mutual" boolean not null default '1', "effective_start_date" date not null, "effective_end_date" date null, "note" jsonb null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "course_equivalencies" add constraint "course_equivalencies_course_id_foreign" foreign key ("course_id") references "courses" ("id") on delete cascade;

alter table "course_equivalencies" add constraint "course_equivalencies_equivalent_course_id_foreign" foreign key ("equivalent_course_id") references "courses" ("id") on delete restrict;

ALTER TABLE course_versions ADD CONSTRAINT course_versions_title_object_check CHECK (jsonb_typeof(title) = 'object');

ALTER TABLE course_versions ADD CONSTRAINT course_versions_description_object_check CHECK (description IS NULL OR jsonb_typeof(description) = 'object');

ALTER TABLE course_equivalencies ADD CONSTRAINT course_equivalencies_note_object_check CHECK (note IS NULL OR jsonb_typeof(note) = 'object');

CREATE INDEX course_versions_title_search_index ON course_versions USING gin (util.i18n_search_text(title) gin_trgm_ops);

ALTER TABLE course_versions
    ADD COLUMN effective_period daterange GENERATED ALWAYS AS (daterange(effective_start_date, effective_end_date, '[]')) STORED,
    ADD CONSTRAINT course_versions_effective_period_order_check CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date);

ALTER TABLE course_versions ADD CONSTRAINT course_versions_no_overlap_excl EXCLUDE USING gist (course_id WITH =, effective_period WITH &&);

ALTER TABLE course_equivalencies
    ADD COLUMN effective_period daterange GENERATED ALWAYS AS (daterange(effective_start_date, effective_end_date, '[]')) STORED,
    ADD CONSTRAINT course_equivalencies_effective_period_order_check CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date);

ALTER TABLE course_equivalencies ADD CONSTRAINT course_equivalencies_no_overlap_excl EXCLUDE USING gist (course_id WITH =, equivalent_course_id WITH =, effective_period WITH &&);

ALTER TABLE course_versions
    ADD CONSTRAINT course_versions_credits_check CHECK (credits >= 0 AND lecture_hours >= 0 AND lab_hours >= 0),
    ADD CONSTRAINT course_versions_grading_basis_check CHECK (grading_basis IN ('graded', 'pass_fail'));

ALTER TABLE course_requisites ADD CONSTRAINT course_requisites_kind_check CHECK (kind IN ('prerequisite', 'corequisite'));

ALTER TABLE course_requisites ADD CONSTRAINT course_requisites_group_check CHECK (group_number >= 1);

ALTER TABLE course_equivalencies ADD CONSTRAINT course_equivalencies_distinct_check CHECK (course_id <> equivalent_course_id);

SELECT util.enable_audit('courses'::regclass);

SELECT util.enable_audit('course_versions'::regclass);

SELECT util.enable_audit('course_requisites'::regclass);

SELECT util.enable_audit('course_equivalencies'::regclass);

