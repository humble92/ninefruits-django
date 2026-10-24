create table "course_categories" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "parent_id" bigint null, "sort_order" integer not null default '0', "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "course_categories" add constraint "course_categories_parent_id_foreign" foreign key ("parent_id") references "course_categories" ("id") on delete restrict;

alter table "course_categories" add constraint "course_categories_code_unique" unique ("code");

create table "grade_scales" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "max_grade_points" decimal(4, 2) not null, "is_default" boolean not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "grade_scales" add constraint "grade_scales_code_unique" unique ("code");

create table "grade_scale_items" ("id" bigserial not null primary key, "grade_scale_id" bigint not null, "code" varchar(16) not null, "name" jsonb null, "grade_points" decimal(4, 2) null, "min_percentage" decimal(5, 2) null, "max_percentage" decimal(5, 2) null, "counts_in_gpa" boolean not null default '1', "is_passing" boolean not null default '1', "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "grade_scale_items" add constraint "grade_scale_items_grade_scale_id_foreign" foreign key ("grade_scale_id") references "grade_scales" ("id") on delete cascade;

alter table "grade_scale_items" add constraint "grade_scale_items_grade_scale_id_code_unique" unique ("grade_scale_id", "code");

ALTER TABLE course_categories ADD CONSTRAINT course_categories_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE grade_scales ADD CONSTRAINT grade_scales_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE grade_scale_items ADD CONSTRAINT grade_scale_items_name_object_check CHECK (name IS NULL OR jsonb_typeof(name) = 'object');

CREATE UNIQUE INDEX grade_scales_single_default_unique ON grade_scales (is_default) WHERE is_default;

ALTER TABLE course_categories ADD CONSTRAINT course_categories_not_own_parent_check CHECK (parent_id IS NULL OR parent_id <> id);

ALTER TABLE grade_scale_items
    ADD CONSTRAINT grade_scale_items_points_check CHECK (grade_points IS NULL OR grade_points >= 0),
    ADD CONSTRAINT grade_scale_items_percentage_check CHECK (
        (min_percentage IS NULL OR min_percentage BETWEEN 0 AND 100)
        AND (max_percentage IS NULL OR max_percentage BETWEEN 0 AND 100)
        AND (min_percentage IS NULL OR max_percentage IS NULL OR min_percentage <= max_percentage)
    ),
    ADD CONSTRAINT grade_scale_items_gpa_points_check CHECK (NOT counts_in_gpa OR grade_points IS NOT NULL);

SELECT util.enable_audit('course_categories'::regclass);

SELECT util.enable_audit('grade_scales'::regclass);

SELECT util.enable_audit('grade_scale_items'::regclass);

