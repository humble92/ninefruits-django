ALTER TABLE enrollments DROP CONSTRAINT IF EXISTS enrollments_comparison_grade_check;

alter table "enrollments" drop constraint "enrollments_comparison_grade_scale_id_foreign";

alter table "enrollments" drop column "comparison_grade_scale_id";

alter table "enrollments" drop column "comparison_grade_code", drop column "comparison_grade_points";

-- @apply triggers/grades.sql

ALTER TABLE sections ALTER COLUMN evaluation_method SET DEFAULT 'absolute';

alter table "sections" add column "grade_exception_reason" text null;

alter table "sections" add column "grade_exception_by_id" bigint null;

alter table "sections" add constraint "sections_grade_exception_by_id_foreign" foreign key ("grade_exception_by_id") references "users" ("id") on delete set null;

alter table "sections" add column "grade_exception_at" timestamp(0) with time zone null;

ALTER TABLE sections ADD CONSTRAINT sections_grade_exception_check CHECK ((grade_exception_reason IS NULL) = (grade_exception_at IS NULL));

create table "evaluation_method_requests" ("id" bigserial not null primary key, "section_id" bigint not null, "requested_method" varchar(16) not null, "reason" text not null, "status" varchar(16) not null default 'pending', "requested_by_id" bigint not null, "requested_at" timestamp(0) with time zone not null, "decided_by_id" bigint null, "decided_at" timestamp(0) with time zone null, "decision_note" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "evaluation_method_requests" add constraint "evaluation_method_requests_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete restrict;

alter table "evaluation_method_requests" add constraint "evaluation_method_requests_requested_by_id_foreign" foreign key ("requested_by_id") references "users" ("id") on delete restrict;

alter table "evaluation_method_requests" add constraint "evaluation_method_requests_decided_by_id_foreign" foreign key ("decided_by_id") references "users" ("id") on delete restrict;

create index "evaluation_method_requests_status_requested_at_index" on "evaluation_method_requests" ("status", "requested_at");

ALTER TABLE evaluation_method_requests
    ADD CONSTRAINT evaluation_method_requests_method_check CHECK (requested_method IN ('absolute', 'relative')),
    ADD CONSTRAINT evaluation_method_requests_status_check CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    ADD CONSTRAINT evaluation_method_requests_decision_check CHECK ((status = 'pending') = (decided_at IS NULL));

CREATE UNIQUE INDEX evaluation_method_requests_single_pending_unique ON evaluation_method_requests (section_id) WHERE status = 'pending';

SELECT util.enable_audit('evaluation_method_requests'::regclass);

