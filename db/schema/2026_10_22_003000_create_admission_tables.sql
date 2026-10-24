create table "admission_cycles" ("id" bigserial not null primary key, "code" varchar(64) not null, "name" jsonb not null, "description" jsonb null, "opens_at" timestamp(0) with time zone not null, "closes_at" timestamp(0) with time zone null, "is_published" boolean not null default '0', "should_release_decisions_immediately" boolean not null default '0', "offer_response_days" smallint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "admission_cycles" add constraint "admission_cycles_code_unique" unique ("code");

create table "application_number_sequences" ("admission_cycle_id" bigint not null, "last_value" integer not null default '0');

alter table "application_number_sequences" add constraint "application_number_sequences_admission_cycle_id_foreign" foreign key ("admission_cycle_id") references "admission_cycles" ("id") on delete cascade;

alter table "application_number_sequences" add primary key ("admission_cycle_id");

create table "admission_cycle_programs" ("id" bigserial not null primary key, "admission_cycle_id" bigint not null, "program_id" bigint not null, "capacity" integer null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "admission_cycle_programs" add constraint "admission_cycle_programs_admission_cycle_id_foreign" foreign key ("admission_cycle_id") references "admission_cycles" ("id") on delete cascade;

alter table "admission_cycle_programs" add constraint "admission_cycle_programs_program_id_foreign" foreign key ("program_id") references "programs" ("id") on delete restrict;

alter table "admission_cycle_programs" add constraint "admission_cycle_programs_admission_cycle_id_program_id_unique" unique ("admission_cycle_id", "program_id");

create table "admission_cycle_document_types" ("id" bigserial not null primary key, "admission_cycle_id" bigint not null, "document_type_id" bigint not null, "is_required" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "admission_cycle_document_types" add constraint "admission_cycle_document_types_admission_cycle_id_foreign" foreign key ("admission_cycle_id") references "admission_cycles" ("id") on delete cascade;

alter table "admission_cycle_document_types" add constraint "admission_cycle_document_types_document_type_id_foreign" foreign key ("document_type_id") references "lookup_values" ("id") on delete restrict;

alter table "admission_cycle_document_types" add constraint "admission_cycle_document_types_admission_cycle_id_document_type_id_unique" unique ("admission_cycle_id", "document_type_id");

create table "applications" ("id" bigserial not null primary key, "application_number" varchar(80) null, "admission_cycle_id" bigint not null, "person_id" bigint not null, "program_id" bigint not null, "org_unit_id" bigint not null, "admission_type_id" bigint null, "status" varchar(32) not null default 'draft', "previous_school_name" varchar(255) null, "previous_school_country_id" bigint null, "previous_graduation_date" date null, "personal_statement" text null, "submitted_at" timestamp(0) with time zone null, "review_started_at" timestamp(0) with time zone null, "decided_by_id" bigint null, "decided_at" timestamp(0) with time zone null, "decision_note" text null, "decision_released_at" timestamp(0) with time zone null, "offer_expires_at" timestamp(0) with time zone null, "responded_at" timestamp(0) with time zone null, "withdrawn_at" timestamp(0) with time zone null, "withdrawal_reason" text null, "student_record_id" bigint null, "matriculated_at" timestamp(0) with time zone null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "applications" add constraint "applications_admission_cycle_id_foreign" foreign key ("admission_cycle_id") references "admission_cycles" ("id") on delete restrict;

alter table "applications" add constraint "applications_person_id_foreign" foreign key ("person_id") references "people" ("id") on delete restrict;

alter table "applications" add constraint "applications_program_id_foreign" foreign key ("program_id") references "programs" ("id") on delete restrict;

alter table "applications" add constraint "applications_org_unit_id_foreign" foreign key ("org_unit_id") references "org_units" ("id") on delete restrict;

alter table "applications" add constraint "applications_admission_type_id_foreign" foreign key ("admission_type_id") references "lookup_values" ("id") on delete set null;

alter table "applications" add constraint "applications_previous_school_country_id_foreign" foreign key ("previous_school_country_id") references "countries" ("id") on delete set null;

alter table "applications" add constraint "applications_decided_by_id_foreign" foreign key ("decided_by_id") references "users" ("id") on delete set null;

alter table "applications" add constraint "applications_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete restrict;

create index "applications_person_id_index" on "applications" ("person_id");

create index "applications_admission_cycle_id_status_index" on "applications" ("admission_cycle_id", "status");

create index "applications_org_unit_id_status_index" on "applications" ("org_unit_id", "status");

create index "applications_program_id_status_index" on "applications" ("program_id", "status");

alter table "applications" add constraint "applications_application_number_unique" unique ("application_number");

alter table "applications" add constraint "applications_student_record_id_unique" unique ("student_record_id");

ALTER TABLE admission_cycles ADD CONSTRAINT admission_cycles_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE admission_cycles ADD CONSTRAINT admission_cycles_description_object_check CHECK (description IS NULL OR jsonb_typeof(description) = 'object');

ALTER TABLE admission_cycles ADD CONSTRAINT admission_cycles_period_check CHECK (closes_at IS NULL OR closes_at > opens_at);

ALTER TABLE admission_cycle_programs ADD CONSTRAINT admission_cycle_programs_capacity_check CHECK (capacity IS NULL OR capacity >= 0);

ALTER TABLE applications
    ADD CONSTRAINT applications_status_check CHECK (status IN ('draft', 'submitted', 'under_review', 'admitted', 'rejected', 'confirmed', 'withdrawn', 'expired')),
    -- A number exactly when submitted; every state after a draft needs one,
    -- except withdrawing or expiring a draft.
    ADD CONSTRAINT applications_number_check CHECK ((submitted_at IS NULL) = (application_number IS NULL)),
    ADD CONSTRAINT applications_submitted_check CHECK (status IN ('draft', 'expired', 'withdrawn') OR submitted_at IS NOT NULL),
    ADD CONSTRAINT applications_matriculated_check CHECK (student_record_id IS NULL OR status = 'confirmed');

CREATE UNIQUE INDEX applications_single_open_unique ON applications (person_id, admission_cycle_id) WHERE status NOT IN ('withdrawn', 'rejected', 'expired');

SELECT util.enable_audit('admission_cycles'::regclass);

SELECT util.enable_audit('admission_cycle_programs'::regclass);

SELECT util.enable_audit('admission_cycle_document_types'::regclass);

SELECT util.enable_audit('applications'::regclass);

