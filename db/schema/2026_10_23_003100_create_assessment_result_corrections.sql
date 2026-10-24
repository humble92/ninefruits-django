create table "assessment_result_corrections" ("id" bigserial not null primary key, "assessment_result_id" bigint not null, "proposed" jsonb not null, "previous" jsonb not null, "reason" text not null, "status" varchar(16) not null default 'pending', "requested_by_id" bigint not null, "requested_at" timestamp(0) with time zone not null, "decided_by_id" bigint null, "decided_at" timestamp(0) with time zone null, "decision_note" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "assessment_result_corrections" add constraint "assessment_result_corrections_assessment_result_id_foreign" foreign key ("assessment_result_id") references "assessment_results" ("id") on delete cascade;

alter table "assessment_result_corrections" add constraint "assessment_result_corrections_requested_by_id_foreign" foreign key ("requested_by_id") references "users" ("id") on delete restrict;

alter table "assessment_result_corrections" add constraint "assessment_result_corrections_decided_by_id_foreign" foreign key ("decided_by_id") references "users" ("id") on delete restrict;

create index "assessment_result_corrections_status_requested_at_index" on "assessment_result_corrections" ("status", "requested_at");

ALTER TABLE assessment_result_corrections
    ADD CONSTRAINT assessment_result_corrections_status_check CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    ADD CONSTRAINT assessment_result_corrections_decision_check CHECK ((status = 'pending') = (decided_at IS NULL));

CREATE UNIQUE INDEX assessment_result_corrections_single_pending_unique ON assessment_result_corrections (assessment_result_id) WHERE status = 'pending';

SELECT util.enable_audit('assessment_result_corrections'::regclass);

-- @apply policies/assessment_corrections.sql

