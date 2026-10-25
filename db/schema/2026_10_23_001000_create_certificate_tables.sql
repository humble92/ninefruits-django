create table "certificate_types" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "audience" varchar(16) not null default 'any', "has_grades" boolean not null default '0', "has_photo" boolean not null default '0', "is_active" boolean not null default '1', "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "certificate_types" add constraint "certificate_types_code_unique" unique ("code");

create table "certificate_templates" ("id" bigserial not null primary key, "certificate_type_id" bigint not null, "locale" varchar(8) not null, "title" varchar(160) not null, "body" text not null, "footer" text null, "signer" varchar(160) null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "certificate_templates" add constraint "certificate_templates_certificate_type_id_foreign" foreign key ("certificate_type_id") references "certificate_types" ("id") on delete cascade;

alter table "certificate_templates" add constraint "certificate_templates_certificate_type_id_locale_unique" unique ("certificate_type_id", "locale");

create table "certificate_number_sequences" ("prefix" varchar(64) not null, "last_value" bigint not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "certificate_number_sequences" add primary key ("prefix");

create table "certificate_issues" ("id" bigserial not null primary key, "student_record_id" bigint not null, "certificate_type_id" bigint not null, "locale" varchar(8) not null, "serial_number" varchar(64) not null, "verification_code" varchar(40) not null, "purpose" varchar(200) null, "copies" smallint not null default '1', "status" varchar(16) not null default 'issued', "issued_at" timestamp(0) with time zone not null, "issued_by_id" bigint null, "pdf_checksum" varchar(64) null, "revoked_at" timestamp(0) with time zone null, "revoked_by_id" bigint null, "revocation_reason" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "certificate_issues" add constraint "certificate_issues_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete restrict;

alter table "certificate_issues" add constraint "certificate_issues_certificate_type_id_foreign" foreign key ("certificate_type_id") references "certificate_types" ("id") on delete restrict;

alter table "certificate_issues" add constraint "certificate_issues_issued_by_id_foreign" foreign key ("issued_by_id") references "users" ("id") on delete set null;

alter table "certificate_issues" add constraint "certificate_issues_revoked_by_id_foreign" foreign key ("revoked_by_id") references "users" ("id") on delete set null;

create index "certificate_issues_student_record_id_issued_at_index" on "certificate_issues" ("student_record_id", "issued_at");

alter table "certificate_issues" add constraint "certificate_issues_serial_number_unique" unique ("serial_number");

alter table "certificate_issues" add constraint "certificate_issues_verification_code_unique" unique ("verification_code");

ALTER TABLE certificate_types ADD CONSTRAINT certificate_types_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE certificate_types
    ADD CONSTRAINT certificate_types_audience_check CHECK (audience IN ('any', 'enrolled', 'graduated'));

ALTER TABLE certificate_issues
    ADD CONSTRAINT certificate_issues_status_check CHECK (status IN ('issued', 'revoked')),
    ADD CONSTRAINT certificate_issues_copies_check CHECK (copies BETWEEN 1 AND 20),
    ADD CONSTRAINT certificate_issues_revoked_check CHECK ((status = 'revoked') = (revoked_at IS NOT NULL));

SELECT util.enable_audit('certificate_types'::regclass);

SELECT util.enable_audit('certificate_templates'::regclass);

SELECT util.enable_audit('certificate_issues'::regclass);

