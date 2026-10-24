alter table "sections" add column "enrolled_count" integer not null default '0';

alter table "sections" add column "waitlist_capacity" integer not null default '0';

alter table "section_seat_groups" add column "enrolled_count" integer not null default '0';

alter table "section_seat_groups" add column "release_processed_at" timestamp(0) with time zone null;

create table "enrollments" ("id" bigserial not null primary key, "student_record_id" bigint not null, "section_id" bigint not null, "term_id" bigint not null, "course_id" bigint not null, "course_version_id" bigint not null, "credits" decimal(4, 1) not null, "course_category_id" bigint null, "counts_toward_credit_limit" boolean not null default '1', "status" varchar(16) not null default 'enrolled', "seat_group_id" bigint null, "is_retake" boolean not null default '0', "repeats_enrollment_id" bigint null, "source" varchar(16) not null default 'student', "enrolled_at" timestamp(0) with time zone not null, "dropped_at" timestamp(0) with time zone null, "withdrawn_at" timestamp(0) with time zone null, "changed_by_id" bigint null, "grade_status" varchar(16) not null default 'none', "grade_code" varchar(8) null, "is_passed" boolean null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "enrollments" add constraint "enrollments_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete restrict;

alter table "enrollments" add constraint "enrollments_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete restrict;

alter table "enrollments" add constraint "enrollments_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete restrict;

alter table "enrollments" add constraint "enrollments_course_id_foreign" foreign key ("course_id") references "courses" ("id") on delete restrict;

alter table "enrollments" add constraint "enrollments_course_version_id_foreign" foreign key ("course_version_id") references "course_versions" ("id") on delete restrict;

alter table "enrollments" add constraint "enrollments_course_category_id_foreign" foreign key ("course_category_id") references "course_categories" ("id") on delete set null;

alter table "enrollments" add constraint "enrollments_seat_group_id_foreign" foreign key ("seat_group_id") references "section_seat_groups" ("id") on delete set null;

alter table "enrollments" add constraint "enrollments_repeats_enrollment_id_foreign" foreign key ("repeats_enrollment_id") references "enrollments" ("id") on delete set null;

alter table "enrollments" add constraint "enrollments_changed_by_id_foreign" foreign key ("changed_by_id") references "users" ("id") on delete set null;

create index "enrollments_student_record_id_term_id_index" on "enrollments" ("student_record_id", "term_id");

create index "enrollments_section_id_status_index" on "enrollments" ("section_id", "status");

create index "enrollments_student_record_id_course_id_index" on "enrollments" ("student_record_id", "course_id");

create table "waitlist_entries" ("id" bigserial not null primary key, "section_id" bigint not null, "student_record_id" bigint not null, "status" varchar(16) not null default 'waiting', "requested_at" timestamp(0) with time zone not null, "requested_by_id" bigint null, "resolved_at" timestamp(0) with time zone null, "enrollment_id" bigint null, "outcome_note" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "waitlist_entries" add constraint "waitlist_entries_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

alter table "waitlist_entries" add constraint "waitlist_entries_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "waitlist_entries" add constraint "waitlist_entries_requested_by_id_foreign" foreign key ("requested_by_id") references "users" ("id") on delete set null;

alter table "waitlist_entries" add constraint "waitlist_entries_enrollment_id_foreign" foreign key ("enrollment_id") references "enrollments" ("id") on delete set null;

create index "waitlist_entries_section_id_status_requested_at_index" on "waitlist_entries" ("section_id", "status", "requested_at");

create index "waitlist_entries_student_record_id_index" on "waitlist_entries" ("student_record_id");

create table "registration_holds" ("id" bigserial not null primary key, "student_record_id" bigint not null, "hold_type" varchar(32) not null, "blocks_registration" boolean not null default '1', "blocks_grades" boolean not null default '0', "blocks_certificates" boolean not null default '0', "starts_at" timestamp(0) with time zone not null, "ends_at" timestamp(0) with time zone null, "reason" text not null, "source" varchar(16) not null default 'manual', "created_by_id" bigint null, "released_at" timestamp(0) with time zone null, "released_by_id" bigint null, "release_reason" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "registration_holds" add constraint "registration_holds_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "registration_holds" add constraint "registration_holds_created_by_id_foreign" foreign key ("created_by_id") references "users" ("id") on delete set null;

alter table "registration_holds" add constraint "registration_holds_released_by_id_foreign" foreign key ("released_by_id") references "users" ("id") on delete set null;

create index "registration_holds_student_record_id_index" on "registration_holds" ("student_record_id");

create table "registration_overrides" ("id" bigserial not null primary key, "student_record_id" bigint not null, "term_id" bigint not null, "rule_code" varchar(64) not null, "section_id" bigint null, "course_id" bigint null, "reason" text not null, "expires_at" timestamp(0) with time zone null, "granted_by_id" bigint null, "revoked_at" timestamp(0) with time zone null, "revoked_by_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "registration_overrides" add constraint "registration_overrides_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "registration_overrides" add constraint "registration_overrides_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete cascade;

alter table "registration_overrides" add constraint "registration_overrides_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

alter table "registration_overrides" add constraint "registration_overrides_course_id_foreign" foreign key ("course_id") references "courses" ("id") on delete cascade;

alter table "registration_overrides" add constraint "registration_overrides_granted_by_id_foreign" foreign key ("granted_by_id") references "users" ("id") on delete set null;

alter table "registration_overrides" add constraint "registration_overrides_revoked_by_id_foreign" foreign key ("revoked_by_id") references "users" ("id") on delete set null;

create index "registration_overrides_student_record_id_term_id_index" on "registration_overrides" ("student_record_id", "term_id");

create table "registration_rule_sets" ("id" bigserial not null primary key, "term_id" bigint not null, "copied_from_rule_set_id" bigint null, "note" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "registration_rule_sets" add constraint "registration_rule_sets_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete cascade;

alter table "registration_rule_sets" add constraint "registration_rule_sets_copied_from_rule_set_id_foreign" foreign key ("copied_from_rule_set_id") references "registration_rule_sets" ("id") on delete set null;

alter table "registration_rule_sets" add constraint "registration_rule_sets_term_id_unique" unique ("term_id");

create table "registration_rules" ("id" bigserial not null primary key, "registration_rule_set_id" bigint not null, "rule_code" varchar(64) not null, "is_enabled" boolean not null default '1', "severity" varchar(8) not null default 'block', "allows_override" boolean not null default '1', "parameters" jsonb null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "registration_rules" add constraint "registration_rules_registration_rule_set_id_foreign" foreign key ("registration_rule_set_id") references "registration_rule_sets" ("id") on delete cascade;

alter table "registration_rules" add constraint "registration_rules_registration_rule_set_id_rule_code_unique" unique ("registration_rule_set_id", "rule_code");

create table "credit_limit_policies" ("id" bigserial not null primary key, "name" jsonb not null, "term_type_id" bigint null, "eligibility" jsonb null, "min_credits" decimal(4, 1) null, "max_credits" decimal(4, 1) not null, "priority" integer not null default '0', "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "credit_limit_policies" add constraint "credit_limit_policies_term_type_id_foreign" foreign key ("term_type_id") references "term_types" ("id") on delete restrict;

create table "cart_items" ("id" bigserial not null primary key, "student_record_id" bigint not null, "term_id" bigint not null, "section_id" bigint not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "cart_items" add constraint "cart_items_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "cart_items" add constraint "cart_items_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete cascade;

alter table "cart_items" add constraint "cart_items_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

alter table "cart_items" add constraint "cart_items_student_record_id_section_id_unique" unique ("student_record_id", "section_id");

create table "registration_attempts" ("id" bigserial not null primary key, "student_record_id" bigint not null, "term_id" bigint null, "section_id" bigint null, "action" varchar(16) not null, "outcome" varchar(16) not null, "results" jsonb not null, "actor_id" bigint null, "request_id" varchar(255) null, "attempted_at" timestamp(0) with time zone not null);

alter table "registration_attempts" add constraint "registration_attempts_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "registration_attempts" add constraint "registration_attempts_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete set null;

alter table "registration_attempts" add constraint "registration_attempts_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete set null;

alter table "registration_attempts" add constraint "registration_attempts_actor_id_foreign" foreign key ("actor_id") references "users" ("id") on delete set null;

create index "registration_attempts_student_record_id_attempted_at_index" on "registration_attempts" ("student_record_id", "attempted_at");

create index "registration_attempts_section_id_attempted_at_index" on "registration_attempts" ("section_id", "attempted_at");

ALTER TABLE credit_limit_policies ADD CONSTRAINT credit_limit_policies_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE sections
    ADD CONSTRAINT sections_enrolled_count_check CHECK (enrolled_count >= 0 AND enrolled_count <= capacity),
    ADD CONSTRAINT sections_waitlist_capacity_check CHECK (waitlist_capacity >= 0);

ALTER TABLE section_seat_groups ADD CONSTRAINT section_seat_groups_enrolled_count_check CHECK (enrolled_count >= 0 AND enrolled_count <= capacity);

ALTER TABLE enrollments
    ADD CONSTRAINT enrollments_status_check CHECK (status IN ('enrolled', 'dropped', 'withdrawn', 'completed')),
    ADD CONSTRAINT enrollments_grade_status_check CHECK (grade_status IN ('none', 'draft', 'submitted', 'finalized')),
    ADD CONSTRAINT enrollments_source_check CHECK (source IN ('student', 'staff', 'waitlist', 'import'));

CREATE UNIQUE INDEX enrollments_active_section_unique ON enrollments (student_record_id, section_id) WHERE status IN ('enrolled', 'completed');

CREATE UNIQUE INDEX enrollments_active_course_unique ON enrollments (student_record_id, term_id, course_id) WHERE status = 'enrolled';

ALTER TABLE waitlist_entries ADD CONSTRAINT waitlist_entries_status_check CHECK (status IN ('waiting', 'promoted', 'removed', 'expired'));

CREATE UNIQUE INDEX waitlist_entries_single_waiting_unique ON waitlist_entries (section_id, student_record_id) WHERE status = 'waiting';

ALTER TABLE registration_holds
    ADD CONSTRAINT registration_holds_type_check CHECK (hold_type IN ('unregistered', 'financial', 'academic', 'administrative', 'other')),
    ADD CONSTRAINT registration_holds_source_check CHECK (source IN ('manual', 'import', 'system')),
    ADD CONSTRAINT registration_holds_period_check CHECK (ends_at IS NULL OR ends_at > starts_at);

ALTER TABLE registration_rules ADD CONSTRAINT registration_rules_severity_check CHECK (severity IN ('block', 'warn'));

ALTER TABLE registration_rules ADD CONSTRAINT registration_rules_parameters_check CHECK (parameters IS NULL OR jsonb_typeof(parameters) = 'object');

ALTER TABLE credit_limit_policies
    ADD CONSTRAINT credit_limit_policies_credits_check CHECK (max_credits >= 0 AND (min_credits IS NULL OR min_credits <= max_credits));

ALTER TABLE registration_attempts
    ADD CONSTRAINT registration_attempts_action_check CHECK (action IN ('enroll', 'drop', 'withdraw', 'waitlist', 'promote', 'cart')),
    ADD CONSTRAINT registration_attempts_outcome_check CHECK (outcome IN ('succeeded', 'waitlisted', 'refused'));

-- @apply triggers/audit.sql

SELECT util.enable_audit('sections', '{}', ARRAY['enrolled_count', 'updated_at']);

SELECT util.enable_audit('section_seat_groups', '{}', ARRAY['enrolled_count', 'release_processed_at', 'updated_at']);

SELECT util.enable_audit('enrollments'::regclass);

SELECT util.enable_audit('waitlist_entries'::regclass);

SELECT util.enable_audit('registration_holds'::regclass);

SELECT util.enable_audit('registration_overrides'::regclass);

SELECT util.enable_audit('registration_rule_sets'::regclass);

SELECT util.enable_audit('registration_rules'::regclass);

SELECT util.enable_audit('credit_limit_policies'::regclass);

