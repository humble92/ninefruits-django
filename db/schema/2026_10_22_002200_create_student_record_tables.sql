create table "student_status_change_types" ("id" bigserial not null primary key, "code" varchar(64) not null, "name" jsonb not null, "to_status" varchar(32) not null, "from_statuses" jsonb not null, "can_student_request" boolean not null default '0', "is_system" boolean not null default '0', "is_active" boolean not null default '1', "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "student_status_change_types" add constraint "student_status_change_types_code_unique" unique ("code");

create table "student_number_sequences" ("prefix" varchar(64) not null, "last_value" bigint not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "student_number_sequences" add primary key ("prefix");

create table "student_records" ("id" bigserial not null primary key, "person_id" bigint not null, "student_number" varchar(32) not null, "program_id" bigint not null, "org_unit_id" bigint not null, "admission_term_id" bigint null, "admission_type_id" bigint null, "admission_date" date not null, "catalog_year" smallint not null, "year_level" smallint not null default '1', "status" varchar(32) not null default 'enrolled', "status_changed_at" timestamp(0) with time zone null, "academic_standing" varchar(32) null, "graduation_date" date null, "degree_number" varchar(64) null, "institutional_email" varchar(255) null, "tags" jsonb null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "student_records" add constraint "student_records_person_id_foreign" foreign key ("person_id") references "people" ("id") on delete restrict;

alter table "student_records" add constraint "student_records_program_id_foreign" foreign key ("program_id") references "programs" ("id") on delete restrict;

alter table "student_records" add constraint "student_records_org_unit_id_foreign" foreign key ("org_unit_id") references "org_units" ("id") on delete restrict;

alter table "student_records" add constraint "student_records_admission_term_id_foreign" foreign key ("admission_term_id") references "terms" ("id") on delete set null;

alter table "student_records" add constraint "student_records_admission_type_id_foreign" foreign key ("admission_type_id") references "lookup_values" ("id") on delete set null;

create index "student_records_person_id_index" on "student_records" ("person_id");

create index "student_records_org_unit_id_status_index" on "student_records" ("org_unit_id", "status");

create index "student_records_program_id_status_index" on "student_records" ("program_id", "status");

create index "student_records_institutional_email_index" on "student_records" ("institutional_email");

alter table "student_records" add constraint "student_records_student_number_unique" unique ("student_number");

alter table "student_records" add constraint "student_records_degree_number_unique" unique ("degree_number");

create table "student_record_programs" ("id" bigserial not null primary key, "student_record_id" bigint not null, "program_id" bigint not null, "role" varchar(32) not null, "start_date" date not null, "end_date" date null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "student_record_programs" add constraint "student_record_programs_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "student_record_programs" add constraint "student_record_programs_program_id_foreign" foreign key ("program_id") references "programs" ("id") on delete restrict;

alter table "student_record_programs" add constraint "student_record_programs_student_record_id_program_id_unique" unique ("student_record_id", "program_id");

create table "student_status_changes" ("id" bigserial not null primary key, "student_record_id" bigint not null, "status_change_type_id" bigint not null, "from_status" varchar(32) not null, "to_status" varchar(32) not null, "effective_date" date not null, "term_id" bigint null, "reason" text not null, "status" varchar(32) not null default 'requested', "requested_by_id" bigint null, "requested_at" timestamp(0) with time zone not null, "decided_by_id" bigint null, "decided_at" timestamp(0) with time zone null, "decision_note" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "student_status_changes" add constraint "student_status_changes_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "student_status_changes" add constraint "student_status_changes_status_change_type_id_foreign" foreign key ("status_change_type_id") references "student_status_change_types" ("id") on delete restrict;

alter table "student_status_changes" add constraint "student_status_changes_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete set null;

alter table "student_status_changes" add constraint "student_status_changes_requested_by_id_foreign" foreign key ("requested_by_id") references "users" ("id") on delete set null;

alter table "student_status_changes" add constraint "student_status_changes_decided_by_id_foreign" foreign key ("decided_by_id") references "users" ("id") on delete set null;

create index "student_status_changes_student_record_id_status_index" on "student_status_changes" ("student_record_id", "status");

create index "student_status_changes_status_index" on "student_status_changes" ("status");

create table "advisor_assignments" ("id" bigserial not null primary key, "student_record_id" bigint not null, "instructor_id" bigint not null, "role" varchar(32) not null default 'primary', "start_date" date not null, "end_date" date null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "advisor_assignments" add constraint "advisor_assignments_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "advisor_assignments" add constraint "advisor_assignments_instructor_id_foreign" foreign key ("instructor_id") references "instructors" ("id") on delete restrict;

create index "advisor_assignments_instructor_id_index" on "advisor_assignments" ("instructor_id");

create index "advisor_assignments_student_record_id_index" on "advisor_assignments" ("student_record_id");

ALTER TABLE student_status_change_types ADD CONSTRAINT student_status_change_types_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE student_status_change_types
    ADD CONSTRAINT student_status_change_types_from_statuses_array_check CHECK (jsonb_typeof(from_statuses) = 'array');

ALTER TABLE student_records
    ADD CONSTRAINT student_records_year_level_check CHECK (year_level BETWEEN 1 AND 10),
    ADD CONSTRAINT student_records_tags_array_check CHECK (tags IS NULL OR jsonb_typeof(tags) = 'array'),
    ADD CONSTRAINT student_records_graduation_check CHECK (status <> 'graduated' OR graduation_date IS NOT NULL);

ALTER TABLE student_record_programs ADD CONSTRAINT student_record_programs_period_check CHECK (end_date IS NULL OR end_date >= start_date);

ALTER TABLE advisor_assignments ADD CONSTRAINT advisor_assignments_period_check CHECK (end_date IS NULL OR end_date >= start_date);

CREATE UNIQUE INDEX advisor_assignments_single_primary_unique ON advisor_assignments (student_record_id) WHERE role = 'primary' AND end_date IS NULL;

CREATE UNIQUE INDEX student_status_changes_single_pending_unique ON student_status_changes (student_record_id) WHERE status = 'requested';

SELECT util.enable_audit('student_status_change_types'::regclass);

SELECT util.enable_audit('student_records'::regclass);

SELECT util.enable_audit('student_record_programs'::regclass);

SELECT util.enable_audit('student_status_changes'::regclass);

SELECT util.enable_audit('advisor_assignments'::regclass);

