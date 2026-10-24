alter table "programs" add column "allows_second_major" boolean not null default '0';

alter table "programs" add column "allows_minor" boolean not null default '0';

create table "additional_program_requests" ("id" bigserial not null primary key, "student_record_id" bigint not null, "program_id" bigint not null, "org_unit_id" bigint not null, "role" varchar(16) not null, "term_id" bigint not null, "status" varchar(16) not null default 'requested', "statement" text null, "requested_by_id" bigint null, "requested_at" timestamp(0) with time zone not null, "decided_by_id" bigint null, "decided_at" timestamp(0) with time zone null, "decision_note" text null, "student_record_program_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "additional_program_requests" add constraint "additional_program_requests_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "additional_program_requests" add constraint "additional_program_requests_program_id_foreign" foreign key ("program_id") references "programs" ("id") on delete restrict;

alter table "additional_program_requests" add constraint "additional_program_requests_org_unit_id_foreign" foreign key ("org_unit_id") references "org_units" ("id") on delete restrict;

alter table "additional_program_requests" add constraint "additional_program_requests_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete restrict;

alter table "additional_program_requests" add constraint "additional_program_requests_requested_by_id_foreign" foreign key ("requested_by_id") references "users" ("id") on delete set null;

alter table "additional_program_requests" add constraint "additional_program_requests_decided_by_id_foreign" foreign key ("decided_by_id") references "users" ("id") on delete set null;

alter table "additional_program_requests" add constraint "additional_program_requests_student_record_program_id_foreign" foreign key ("student_record_program_id") references "student_record_programs" ("id") on delete set null;

create index "additional_program_requests_student_record_id_status_index" on "additional_program_requests" ("student_record_id", "status");

create index "additional_program_requests_org_unit_id_status_index" on "additional_program_requests" ("org_unit_id", "status");

ALTER TABLE additional_program_requests
    ADD CONSTRAINT additional_program_requests_role_check CHECK (role IN ('second_major', 'minor')),
    ADD CONSTRAINT additional_program_requests_status_check CHECK (status IN ('requested', 'approved', 'rejected', 'cancelled'));

CREATE UNIQUE INDEX additional_program_requests_single_pending_unique ON additional_program_requests (student_record_id, program_id) WHERE status = 'requested';

ALTER TABLE student_record_programs ADD CONSTRAINT student_record_programs_role_check CHECK (role IN ('second_major', 'minor'));

alter table "student_record_programs" drop constraint "student_record_programs_student_record_id_program_id_unique";

CREATE UNIQUE INDEX student_record_programs_current_unique ON student_record_programs (student_record_id, program_id) WHERE end_date IS NULL;

-- @apply policies/additional_programs.sql

SELECT util.enable_audit('additional_program_requests'::regclass);

