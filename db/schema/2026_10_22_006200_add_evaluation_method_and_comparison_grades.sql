alter table "sections" add column "evaluation_method" varchar(16) not null default 'relative';

ALTER TABLE sections ADD CONSTRAINT sections_evaluation_method_check CHECK (evaluation_method IN ('absolute', 'relative'));

alter table "enrollments" add column "comparison_grade_scale_id" bigint null;

alter table "enrollments" add constraint "enrollments_comparison_grade_scale_id_foreign" foreign key ("comparison_grade_scale_id") references "grade_scales" ("id") on delete restrict;

alter table "enrollments" add column "comparison_grade_code" varchar(8) null;

alter table "enrollments" add column "comparison_grade_points" decimal(4, 2) null;

ALTER TABLE enrollments ADD CONSTRAINT enrollments_comparison_grade_check CHECK (
    (comparison_grade_code IS NULL) = (comparison_grade_scale_id IS NULL)
    AND (comparison_grade_code IS NULL OR score IS NOT NULL)
);

-- @apply triggers/grades.sql

