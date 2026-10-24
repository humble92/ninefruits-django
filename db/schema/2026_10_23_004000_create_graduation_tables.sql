create table "degree_audits" ("id" bigserial not null primary key, "student_record_id" bigint not null, "curriculum_requirement_set_id" bigint null, "program_role" varchar(16) not null, "program_id" bigint not null, "term_id" bigint null, "is_satisfied" boolean not null, "earned_credits" decimal(5, 1) not null, "required_credits" decimal(5, 1) null, "cumulative_gpa" decimal(4, 2) null, "result" jsonb not null, "audited_at" timestamp(0) with time zone not null, "audited_by_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "degree_audits" add constraint "degree_audits_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete restrict;

alter table "degree_audits" add constraint "degree_audits_curriculum_requirement_set_id_foreign" foreign key ("curriculum_requirement_set_id") references "curriculum_requirement_sets" ("id") on delete restrict;

alter table "degree_audits" add constraint "degree_audits_program_id_foreign" foreign key ("program_id") references "programs" ("id") on delete restrict;

alter table "degree_audits" add constraint "degree_audits_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete restrict;

alter table "degree_audits" add constraint "degree_audits_audited_by_id_foreign" foreign key ("audited_by_id") references "users" ("id") on delete set null;

create index "degree_audits_student_record_id_program_role_audited_at_index" on "degree_audits" ("student_record_id", "program_role", "audited_at");

create table "degree_requirement_waivers" ("id" bigserial not null primary key, "student_record_id" bigint not null, "curriculum_requirement_id" bigint not null, "reason" text not null, "status" varchar(16) not null default 'pending', "requested_by_id" bigint null, "requested_at" timestamp(0) with time zone not null, "decided_by_id" bigint null, "decided_at" timestamp(0) with time zone null, "decision_note" text null, "lifted_by_id" bigint null, "lifted_at" timestamp(0) with time zone null, "lift_reason" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "degree_requirement_waivers" add constraint "degree_requirement_waivers_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete cascade;

alter table "degree_requirement_waivers" add constraint "degree_requirement_waivers_curriculum_requirement_id_foreign" foreign key ("curriculum_requirement_id") references "curriculum_requirements" ("id") on delete cascade;

alter table "degree_requirement_waivers" add constraint "degree_requirement_waivers_requested_by_id_foreign" foreign key ("requested_by_id") references "users" ("id") on delete set null;

alter table "degree_requirement_waivers" add constraint "degree_requirement_waivers_decided_by_id_foreign" foreign key ("decided_by_id") references "users" ("id") on delete set null;

alter table "degree_requirement_waivers" add constraint "degree_requirement_waivers_lifted_by_id_foreign" foreign key ("lifted_by_id") references "users" ("id") on delete set null;

create index "degree_requirement_waivers_student_record_id_status_index" on "degree_requirement_waivers" ("student_record_id", "status");

create table "degree_number_sequences" ("prefix" varchar(64) not null, "last_value" bigint not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "degree_number_sequences" add primary key ("prefix");

ALTER TABLE degree_audits
    ADD CONSTRAINT degree_audits_role_check CHECK (program_role IN ('primary', 'second_major', 'minor'));

ALTER TABLE degree_requirement_waivers
    ADD CONSTRAINT degree_requirement_waivers_status_check CHECK (status IN ('pending', 'approved', 'rejected', 'lifted')),
    ADD CONSTRAINT degree_requirement_waivers_decision_check CHECK ((status = 'pending') = (decided_at IS NULL)),
    ADD CONSTRAINT degree_requirement_waivers_lift_check CHECK ((status = 'lifted') = (lifted_at IS NOT NULL));

CREATE UNIQUE INDEX degree_requirement_waivers_open_unique ON degree_requirement_waivers (student_record_id, curriculum_requirement_id) WHERE status IN ('pending', 'approved');

SELECT util.enable_audit('degree_requirement_waivers'::regclass);

-- @apply policies/graduation.sql

