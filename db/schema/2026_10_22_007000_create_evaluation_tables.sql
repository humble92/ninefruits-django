create table "evaluation_forms" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "description" jsonb null, "scale_points" smallint not null default '5', "scale_low_label" jsonb null, "scale_high_label" jsonb null, "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "evaluation_forms" add constraint "evaluation_forms_code_unique" unique ("code");

create table "evaluation_questions" ("id" bigserial not null primary key, "evaluation_form_id" bigint not null, "sort_order" integer not null default '0', "category" jsonb null, "text" jsonb not null, "question_type" varchar(16) not null default 'scale', "is_required" boolean not null default '1', "is_reversed" boolean not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "evaluation_questions" add constraint "evaluation_questions_evaluation_form_id_foreign" foreign key ("evaluation_form_id") references "evaluation_forms" ("id") on delete cascade;

create index "evaluation_questions_evaluation_form_id_sort_order_index" on "evaluation_questions" ("evaluation_form_id", "sort_order");

create table "term_evaluations" ("id" bigserial not null primary key, "term_id" bigint not null, "evaluation_form_id" bigint not null, "minimum_responses" integer not null default '5', "minimum_response_percent" integer not null default '0', "results_published_at" timestamp(0) with time zone null, "published_by_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "term_evaluations" add constraint "term_evaluations_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete restrict;

alter table "term_evaluations" add constraint "term_evaluations_evaluation_form_id_foreign" foreign key ("evaluation_form_id") references "evaluation_forms" ("id") on delete restrict;

alter table "term_evaluations" add constraint "term_evaluations_published_by_id_foreign" foreign key ("published_by_id") references "users" ("id") on delete set null;

alter table "term_evaluations" add constraint "term_evaluations_term_id_unique" unique ("term_id");

create table "evaluation_completions" ("id" bigserial not null primary key, "enrollment_id" bigint not null, "completed_at" timestamp(0) with time zone not null);

alter table "evaluation_completions" add constraint "evaluation_completions_enrollment_id_foreign" foreign key ("enrollment_id") references "enrollments" ("id") on delete restrict;

alter table "evaluation_completions" add constraint "evaluation_completions_enrollment_id_unique" unique ("enrollment_id");

create table "evaluation_responses" ("id" uuid not null, "term_id" bigint not null, "section_id" bigint not null, "evaluation_form_id" bigint not null);

alter table "evaluation_responses" add constraint "evaluation_responses_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete restrict;

alter table "evaluation_responses" add constraint "evaluation_responses_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete restrict;

alter table "evaluation_responses" add constraint "evaluation_responses_evaluation_form_id_foreign" foreign key ("evaluation_form_id") references "evaluation_forms" ("id") on delete restrict;

create index "evaluation_responses_section_id_index" on "evaluation_responses" ("section_id");

alter table "evaluation_responses" add primary key ("id");

create table "evaluation_answers" ("evaluation_response_id" uuid not null, "evaluation_question_id" bigint not null, "value" smallint null, "comment" text null);

alter table "evaluation_answers" add constraint "evaluation_answers_evaluation_response_id_foreign" foreign key ("evaluation_response_id") references "evaluation_responses" ("id") on delete cascade;

alter table "evaluation_answers" add constraint "evaluation_answers_evaluation_question_id_foreign" foreign key ("evaluation_question_id") references "evaluation_questions" ("id") on delete restrict;

alter table "evaluation_answers" add primary key ("evaluation_response_id", "evaluation_question_id");

alter table "course_versions" add column "requires_evaluation" boolean not null default '1';

ALTER TABLE evaluation_forms ADD CONSTRAINT evaluation_forms_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE evaluation_forms ADD CONSTRAINT evaluation_forms_description_object_check CHECK (description IS NULL OR jsonb_typeof(description) = 'object');

ALTER TABLE evaluation_forms ADD CONSTRAINT evaluation_forms_scale_low_label_object_check CHECK (scale_low_label IS NULL OR jsonb_typeof(scale_low_label) = 'object');

ALTER TABLE evaluation_forms ADD CONSTRAINT evaluation_forms_scale_high_label_object_check CHECK (scale_high_label IS NULL OR jsonb_typeof(scale_high_label) = 'object');

ALTER TABLE evaluation_questions ADD CONSTRAINT evaluation_questions_category_object_check CHECK (category IS NULL OR jsonb_typeof(category) = 'object');

ALTER TABLE evaluation_questions ADD CONSTRAINT evaluation_questions_text_object_check CHECK (jsonb_typeof(text) = 'object');

ALTER TABLE evaluation_forms ADD CONSTRAINT evaluation_forms_scale_points_check CHECK (scale_points BETWEEN 2 AND 10);

ALTER TABLE evaluation_questions ADD CONSTRAINT evaluation_questions_type_check CHECK (question_type IN ('scale', 'text'));

ALTER TABLE term_evaluations
    ADD CONSTRAINT term_evaluations_minimum_check CHECK (minimum_responses >= 0 AND minimum_response_percent BETWEEN 0 AND 100);

ALTER TABLE evaluation_answers ADD CONSTRAINT evaluation_answers_value_check CHECK ((value IS NULL OR value BETWEEN 1 AND 10) AND (value IS NOT NULL OR comment IS NOT NULL));

SELECT util.enable_audit('evaluation_forms'::regclass);

SELECT util.enable_audit('evaluation_questions'::regclass);

SELECT util.enable_audit('term_evaluations'::regclass);

