create table "assessment_types" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "category" varchar(16) not null default 'comprehensive', "scoring" varchar(16) not null default 'score', "max_score" decimal(6, 1) null, "pass_score" decimal(6, 1) null, "allows_external" boolean not null default '0', "is_active" boolean not null default '1', "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "assessment_types" add constraint "assessment_types_code_unique" unique ("code");

create table "assessment_components" ("id" bigserial not null primary key, "assessment_type_id" bigint not null, "code" varchar(32) not null, "name" jsonb not null, "max_score" decimal(6, 1) not null, "min_score" decimal(6, 1) null, "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "assessment_components" add constraint "assessment_components_assessment_type_id_foreign" foreign key ("assessment_type_id") references "assessment_types" ("id") on delete cascade;

alter table "assessment_components" add constraint "assessment_components_assessment_type_id_code_unique" unique ("assessment_type_id", "code");

create table "assessment_sessions" ("id" bigserial not null primary key, "assessment_type_id" bigint not null, "held_date" date not null, "venue" varchar(120) null, "registration_opens_at" timestamp(0) with time zone null, "registration_closes_at" timestamp(0) with time zone null, "capacity" integer null, "pass_score" decimal(6, 1) null, "results_published_at" timestamp(0) with time zone null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "assessment_sessions" add constraint "assessment_sessions_assessment_type_id_foreign" foreign key ("assessment_type_id") references "assessment_types" ("id") on delete restrict;

alter table "assessment_sessions" add constraint "assessment_sessions_assessment_type_id_held_date_unique" unique ("assessment_type_id", "held_date");

create table "assessment_registrations" ("id" bigserial not null primary key, "assessment_session_id" bigint not null, "student_record_id" bigint not null, "status" varchar(16) not null default 'registered', "registered_at" timestamp(0) with time zone not null, "registered_by_id" bigint null, "cancelled_at" timestamp(0) with time zone null, "cancel_reason" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "assessment_registrations" add constraint "assessment_registrations_assessment_session_id_foreign" foreign key ("assessment_session_id") references "assessment_sessions" ("id") on delete restrict;

alter table "assessment_registrations" add constraint "assessment_registrations_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete restrict;

alter table "assessment_registrations" add constraint "assessment_registrations_registered_by_id_foreign" foreign key ("registered_by_id") references "users" ("id") on delete set null;

alter table "assessment_registrations" add constraint "assessment_registrations_assessment_session_id_student_record_id_unique" unique ("assessment_session_id", "student_record_id");

create index "assessment_registrations_student_record_id_index" on "assessment_registrations" ("student_record_id");

create table "assessment_results" ("id" bigserial not null primary key, "student_record_id" bigint not null, "assessment_type_id" bigint not null, "assessment_session_id" bigint null, "assessment_registration_id" bigint null, "source" varchar(16) not null, "taken_date" date not null, "total_score" decimal(6, 1) null, "level" varchar(32) null, "is_passed" boolean not null, "certificate_number" varchar(64) null, "note" text null, "entered_by_id" bigint null, "entered_at" timestamp(0) with time zone not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "assessment_results" add constraint "assessment_results_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete restrict;

alter table "assessment_results" add constraint "assessment_results_assessment_type_id_foreign" foreign key ("assessment_type_id") references "assessment_types" ("id") on delete restrict;

alter table "assessment_results" add constraint "assessment_results_assessment_session_id_foreign" foreign key ("assessment_session_id") references "assessment_sessions" ("id") on delete restrict;

alter table "assessment_results" add constraint "assessment_results_assessment_registration_id_foreign" foreign key ("assessment_registration_id") references "assessment_registrations" ("id") on delete restrict;

alter table "assessment_results" add constraint "assessment_results_entered_by_id_foreign" foreign key ("entered_by_id") references "users" ("id") on delete set null;

alter table "assessment_results" add constraint "assessment_results_assessment_session_id_student_record_id_unique" unique ("assessment_session_id", "student_record_id");

create index "assessment_results_student_record_id_assessment_type_id_index" on "assessment_results" ("student_record_id", "assessment_type_id");

alter table "assessment_results" add constraint "assessment_results_assessment_registration_id_unique" unique ("assessment_registration_id");

create table "assessment_component_scores" ("id" bigserial not null primary key, "assessment_result_id" bigint not null, "assessment_component_id" bigint not null, "score" decimal(6, 1) not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "assessment_component_scores" add constraint "assessment_component_scores_assessment_result_id_foreign" foreign key ("assessment_result_id") references "assessment_results" ("id") on delete cascade;

alter table "assessment_component_scores" add constraint "assessment_component_scores_assessment_component_id_foreign" foreign key ("assessment_component_id") references "assessment_components" ("id") on delete restrict;

alter table "assessment_component_scores" add constraint "assessment_component_scores_assessment_result_id_assessment_component_id_unique" unique ("assessment_result_id", "assessment_component_id");

alter table "curriculum_requirements" add column "assessment_type_id" bigint null;

alter table "curriculum_requirements" add constraint "curriculum_requirements_assessment_type_id_foreign" foreign key ("assessment_type_id") references "assessment_types" ("id") on delete restrict;

ALTER TABLE assessment_types ADD CONSTRAINT assessment_types_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE assessment_components ADD CONSTRAINT assessment_components_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE assessment_types
    ADD CONSTRAINT assessment_types_category_check CHECK (category IN ('language', 'comprehensive', 'thesis', 'external')),
    ADD CONSTRAINT assessment_types_scoring_check CHECK (scoring IN ('score', 'pass_fail'));

ALTER TABLE assessment_sessions
    ADD CONSTRAINT assessment_sessions_registration_check
        CHECK (registration_opens_at IS NULL OR registration_closes_at IS NULL OR registration_opens_at < registration_closes_at),
    ADD CONSTRAINT assessment_sessions_capacity_check CHECK (capacity IS NULL OR capacity > 0);

ALTER TABLE assessment_registrations
    ADD CONSTRAINT assessment_registrations_status_check CHECK (status IN ('registered', 'cancelled', 'absent')),
    ADD CONSTRAINT assessment_registrations_cancelled_check CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL));

ALTER TABLE assessment_results
    ADD CONSTRAINT assessment_results_source_check CHECK (source IN ('session', 'external')),
    ADD CONSTRAINT assessment_results_session_check CHECK ((source = 'session') = (assessment_session_id IS NOT NULL) AND (source = 'session') = (assessment_registration_id IS NOT NULL));

ALTER TABLE curriculum_requirements DROP CONSTRAINT curriculum_requirements_kind_check;

ALTER TABLE curriculum_requirements ADD CONSTRAINT curriculum_requirements_kind_check CHECK (
    (kind = 'category_credits' AND course_category_id IS NOT NULL AND min_credits IS NOT NULL AND assessment_type_id IS NULL)
    OR (kind = 'required_courses' AND course_category_id IS NULL AND assessment_type_id IS NULL)
    OR (kind = 'course_group' AND course_category_id IS NULL AND assessment_type_id IS NULL AND (min_credits IS NOT NULL OR min_courses IS NOT NULL))
    OR (kind = 'assessment_pass' AND assessment_type_id IS NOT NULL AND course_category_id IS NULL AND min_credits IS NULL AND min_courses IS NULL)
);

SELECT util.enable_audit('assessment_types'::regclass);

SELECT util.enable_audit('assessment_components'::regclass);

SELECT util.enable_audit('assessment_sessions'::regclass);

SELECT util.enable_audit('assessment_registrations'::regclass);

SELECT util.enable_audit('assessment_results'::regclass);

SELECT util.enable_audit('assessment_component_scores'::regclass);

