alter table "audit"."record_changes" add column "row_hash" char(64) null;

alter table "audit"."record_changes" add column "chain_hash" char(64) null;

alter table "audit"."record_changes" add column "sealed_at" timestamp(0) with time zone null;

alter table "audit"."activity_log" add column "row_hash" char(64) null;

alter table "audit"."activity_log" add column "chain_hash" char(64) null;

alter table "audit"."activity_log" add column "sealed_at" timestamp(0) with time zone null;

alter table "audit"."security_events" add column "row_hash" char(64) null;

alter table "audit"."security_events" add column "chain_hash" char(64) null;

alter table "audit"."security_events" add column "sealed_at" timestamp(0) with time zone null;

-- @apply triggers/audit_chain.sql

CREATE TRIGGER record_changes_before_insert_row_hash BEFORE INSERT ON audit.record_changes FOR EACH ROW EXECUTE FUNCTION audit.set_row_hash();

SELECT set_config('app.audit_maintenance', 'on', true);

UPDATE audit.record_changes AS t SET row_hash = audit.row_hash_of(to_jsonb(t)) WHERE row_hash IS NULL;

CREATE TRIGGER activity_log_before_insert_row_hash BEFORE INSERT ON audit.activity_log FOR EACH ROW EXECUTE FUNCTION audit.set_row_hash();

SELECT set_config('app.audit_maintenance', 'on', true);

UPDATE audit.activity_log AS t SET row_hash = audit.row_hash_of(to_jsonb(t)) WHERE row_hash IS NULL;

CREATE TRIGGER security_events_before_insert_row_hash BEFORE INSERT ON audit.security_events FOR EACH ROW EXECUTE FUNCTION audit.set_row_hash();

SELECT set_config('app.audit_maintenance', 'on', true);

UPDATE audit.security_events AS t SET row_hash = audit.row_hash_of(to_jsonb(t)) WHERE row_hash IS NULL;

