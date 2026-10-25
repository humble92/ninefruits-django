create table "audit"."record_changes" ("id" bigserial not null primary key, "occurred_at" timestamp(0) with time zone not null default CURRENT_TIMESTAMP, "transaction_id" bigint not null default txid_current(), "table_schema" varchar(255) not null, "table_name" varchar(255) not null, "operation" varchar(16) not null, "record_id" varchar(255) null, "old_values" jsonb null, "new_values" jsonb null, "changed_columns" jsonb null, "user_id" bigint null, "actor" varchar(255) null, "request_id" varchar(255) null, "database_user" varchar(255) not null);

create index "audit_record_changes_table_name_record_id_index" on "audit"."record_changes" ("table_name", "record_id");

create index "audit_record_changes_user_id_index" on "audit"."record_changes" ("user_id");

create index "audit_record_changes_occurred_at_index" on "audit"."record_changes" ("occurred_at");

create table "audit"."activity_log" ("id" bigserial not null primary key, "log_name" varchar(255) null, "description" text not null, "subject_type" varchar(255) null, "subject_id" bigint null, "event" varchar(255) null, "causer_type" varchar(255) null, "causer_id" bigint null, "attribute_changes" jsonb null, "properties" jsonb null, "reason" text null, "request_id" varchar(255) null, "ip_address" varchar(45) null, "user_agent" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

create index "activity_log_subject" on "audit"."activity_log" ("subject_type", "subject_id");

create index "activity_log_causer" on "audit"."activity_log" ("causer_type", "causer_id");

create index "audit_activity_log_log_name_index" on "audit"."activity_log" ("log_name");

create index "audit_activity_log_request_id_index" on "audit"."activity_log" ("request_id");

create table "audit"."security_events" ("id" bigserial not null primary key, "occurred_at" timestamp(0) with time zone not null default CURRENT_TIMESTAMP, "type" varchar(255) not null, "user_id" bigint null, "identifier" varchar(255) null, "subject_type" varchar(255) null, "subject_id" bigint null, "properties" jsonb null, "request_id" varchar(255) null, "ip_address" varchar(45) null, "user_agent" text null);

create index "security_events_subject" on "audit"."security_events" ("subject_type", "subject_id");

create index "audit_security_events_occurred_at_index" on "audit"."security_events" ("occurred_at");

create index "audit_security_events_type_index" on "audit"."security_events" ("type");

create index "audit_security_events_user_id_index" on "audit"."security_events" ("user_id");

-- @apply triggers/audit.sql

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON audit.record_changes FROM "app_runtime";

GRANT SELECT, INSERT ON audit.activity_log, audit.security_events TO "app_runtime";

GRANT USAGE ON SEQUENCE audit.activity_log_id_seq, audit.security_events_id_seq TO "app_runtime";

CREATE TRIGGER record_changes_before_change_prevent_modification
BEFORE UPDATE OR DELETE OR TRUNCATE ON audit.record_changes
FOR EACH STATEMENT EXECUTE FUNCTION audit.prevent_modification();

CREATE TRIGGER activity_log_before_change_prevent_modification
BEFORE UPDATE OR DELETE OR TRUNCATE ON audit.activity_log
FOR EACH STATEMENT EXECUTE FUNCTION audit.prevent_modification();

CREATE TRIGGER security_events_before_change_prevent_modification
BEFORE UPDATE OR DELETE OR TRUNCATE ON audit.security_events
FOR EACH STATEMENT EXECUTE FUNCTION audit.prevent_modification();

