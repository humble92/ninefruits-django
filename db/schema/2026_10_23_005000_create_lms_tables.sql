create table "lms_platforms" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "driver" varchar(32) not null default 'null', "base_url" varchar(255) null, "credentials" text null, "options" jsonb not null, "is_active" boolean not null default '0', "should_sync_enrollments" boolean not null default '1', "should_pull_grades" boolean not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "lms_platforms" add constraint "lms_platforms_code_unique" unique ("code");

create table "lms_course_links" ("id" bigserial not null primary key, "lms_platform_id" bigint not null, "section_id" bigint not null, "external_course_id" varchar(128) null, "external_url" varchar(512) null, "status" varchar(16) not null default 'pending', "last_synced_at" timestamp(0) with time zone null, "last_error" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "lms_course_links" add constraint "lms_course_links_lms_platform_id_foreign" foreign key ("lms_platform_id") references "lms_platforms" ("id") on delete cascade;

alter table "lms_course_links" add constraint "lms_course_links_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

alter table "lms_course_links" add constraint "lms_course_links_lms_platform_id_section_id_unique" unique ("lms_platform_id", "section_id");

create table "lms_user_links" ("id" bigserial not null primary key, "lms_platform_id" bigint not null, "user_id" bigint not null, "external_user_id" varchar(128) not null, "last_synced_at" timestamp(0) with time zone null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "lms_user_links" add constraint "lms_user_links_lms_platform_id_foreign" foreign key ("lms_platform_id") references "lms_platforms" ("id") on delete cascade;

alter table "lms_user_links" add constraint "lms_user_links_user_id_foreign" foreign key ("user_id") references "users" ("id") on delete cascade;

alter table "lms_user_links" add constraint "lms_user_links_lms_platform_id_user_id_unique" unique ("lms_platform_id", "user_id");

alter table "lms_user_links" add constraint "lms_user_links_lms_platform_id_external_user_id_unique" unique ("lms_platform_id", "external_user_id");

create table "lms_sync_logs" ("id" bigserial not null primary key, "lms_platform_id" bigint not null, "section_id" bigint null, "enrollment_id" bigint null, "user_id" bigint null, "operation" varchar(32) not null, "status" varchar(16) not null, "message" text null, "payload" jsonb null, "started_at" timestamp(0) with time zone not null, "finished_at" timestamp(0) with time zone null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "lms_sync_logs" add constraint "lms_sync_logs_lms_platform_id_foreign" foreign key ("lms_platform_id") references "lms_platforms" ("id") on delete cascade;

alter table "lms_sync_logs" add constraint "lms_sync_logs_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete set null;

alter table "lms_sync_logs" add constraint "lms_sync_logs_enrollment_id_foreign" foreign key ("enrollment_id") references "enrollments" ("id") on delete set null;

alter table "lms_sync_logs" add constraint "lms_sync_logs_user_id_foreign" foreign key ("user_id") references "users" ("id") on delete set null;

create index "lms_sync_logs_lms_platform_id_started_at_index" on "lms_sync_logs" ("lms_platform_id", "started_at");

create index "lms_sync_logs_section_id_started_at_index" on "lms_sync_logs" ("section_id", "started_at");

ALTER TABLE lms_platforms ADD CONSTRAINT lms_platforms_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE lms_course_links ADD CONSTRAINT lms_course_links_status_check CHECK (status IN ('pending', 'linked', 'failed'));

ALTER TABLE lms_sync_logs ADD CONSTRAINT lms_sync_logs_status_check CHECK (status IN ('queued', 'succeeded', 'failed', 'skipped'));

SELECT util.enable_audit('lms_course_links'::regclass);

SELECT util.enable_audit('lms_user_links'::regclass);

SELECT util.enable_audit('lms_platforms', ARRAY['credentials']);

-- @apply policies/lms.sql

