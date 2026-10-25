alter table "grade_scale_items" add column "applies_to" varchar(16) not null default 'graded';

UPDATE grade_scale_items SET applies_to = 'pass_fail' WHERE NOT counts_in_gpa;

ALTER TABLE grade_scale_items ADD CONSTRAINT grade_scale_items_applies_to_check CHECK (applies_to IN ('graded', 'pass_fail', 'both'));

alter table "enrollments" add column "grade_scale_id" bigint null;

alter table "enrollments" add constraint "enrollments_grade_scale_id_foreign" foreign key ("grade_scale_id") references "grade_scales" ("id") on delete restrict;

alter table "enrollments" add column "score" decimal(5, 2) null;

alter table "enrollments" add column "grade_points" decimal(4, 2) null;

alter table "enrollments" add column "counts_in_gpa" boolean null;

alter table "enrollments" add column "grade_entered_at" timestamp(0) with time zone null;

alter table "enrollments" add column "grade_entered_by_id" bigint null;

alter table "enrollments" add constraint "enrollments_grade_entered_by_id_foreign" foreign key ("grade_entered_by_id") references "users" ("id") on delete set null;

alter table "enrollments" add column "grade_submitted_at" timestamp(0) with time zone null;

alter table "enrollments" add column "grade_submitted_by_id" bigint null;

alter table "enrollments" add constraint "enrollments_grade_submitted_by_id_foreign" foreign key ("grade_submitted_by_id") references "users" ("id") on delete set null;

alter table "enrollments" add column "grade_finalized_at" timestamp(0) with time zone null;

alter table "enrollments" add column "grade_finalized_by_id" bigint null;

alter table "enrollments" add constraint "enrollments_grade_finalized_by_id_foreign" foreign key ("grade_finalized_by_id") references "users" ("id") on delete set null;

create table "grade_change_requests" ("id" bigserial not null primary key, "enrollment_id" bigint not null, "from_grade_code" varchar(8) null, "to_grade_code" varchar(8) not null, "to_score" decimal(5, 2) null, "reason" text not null, "status" varchar(16) not null default 'pending', "requested_by_id" bigint not null, "requested_at" timestamp(0) with time zone not null, "decided_by_id" bigint null, "decided_at" timestamp(0) with time zone null, "decision_note" text null, "applied_at" timestamp(0) with time zone null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "grade_change_requests" add constraint "grade_change_requests_enrollment_id_foreign" foreign key ("enrollment_id") references "enrollments" ("id") on delete restrict;

alter table "grade_change_requests" add constraint "grade_change_requests_requested_by_id_foreign" foreign key ("requested_by_id") references "users" ("id") on delete restrict;

alter table "grade_change_requests" add constraint "grade_change_requests_decided_by_id_foreign" foreign key ("decided_by_id") references "users" ("id") on delete restrict;

create index "grade_change_requests_status_requested_at_index" on "grade_change_requests" ("status", "requested_at");

create table "term_records" ("id" bigserial not null primary key, "student_record_id" bigint not null, "term_id" bigint not null, "attempted_credits" decimal(5, 1) not null default '0', "earned_credits" decimal(5, 1) not null default '0', "gpa_credits" decimal(5, 1) not null default '0', "grade_points_total" decimal(8, 2) not null default '0', "term_gpa" decimal(5, 3) null, "cumulative_attempted_credits" decimal(6, 1) not null default '0', "cumulative_earned_credits" decimal(6, 1) not null default '0', "cumulative_gpa_credits" decimal(6, 1) not null default '0', "cumulative_grade_points_total" decimal(9, 2) not null default '0', "cumulative_gpa" decimal(5, 3) null, "academic_standing" varchar(32) null, "warning_count" integer not null default '0', "is_honors" boolean not null default '0', "honors_rank" integer null, "calculated_at" timestamp(0) with time zone not null, "closed_at" timestamp(0) with time zone null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "term_records" add constraint "term_records_student_record_id_foreign" foreign key ("student_record_id") references "student_records" ("id") on delete restrict;

alter table "term_records" add constraint "term_records_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete restrict;

alter table "term_records" add constraint "term_records_student_record_id_term_id_unique" unique ("student_record_id", "term_id");

create index "term_records_term_id_academic_standing_index" on "term_records" ("term_id", "academic_standing");

ALTER TABLE enrollments
    ADD CONSTRAINT enrollments_score_check CHECK (score IS NULL OR score BETWEEN 0 AND 100),
    ADD CONSTRAINT enrollments_grade_check CHECK (
        (grade_status = 'none' AND grade_code IS NULL)
        OR (grade_status = 'draft')
        OR (grade_status IN ('submitted', 'finalized') AND grade_code IS NOT NULL AND grade_scale_id IS NOT NULL)
    ),
    ADD CONSTRAINT enrollments_finalized_check CHECK ((grade_status = 'finalized') = (status = 'completed'));

ALTER TABLE grade_change_requests
    ADD CONSTRAINT grade_change_requests_status_check CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    ADD CONSTRAINT grade_change_requests_score_check CHECK (to_score IS NULL OR to_score BETWEEN 0 AND 100),
    -- Separation of duties: nobody approves their own request.
    ADD CONSTRAINT grade_change_requests_second_person_check CHECK (decided_by_id IS NULL OR decided_by_id <> requested_by_id),
    ADD CONSTRAINT grade_change_requests_decision_check CHECK ((status = 'pending') = (decided_at IS NULL)),
    ADD CONSTRAINT grade_change_requests_applied_check CHECK (applied_at IS NULL OR status = 'approved');

CREATE UNIQUE INDEX grade_change_requests_single_pending_unique ON grade_change_requests (enrollment_id) WHERE status = 'pending';

ALTER TABLE term_records ALTER COLUMN term_gpa TYPE numeric, ALTER COLUMN cumulative_gpa TYPE numeric;

ALTER TABLE term_records
    ADD CONSTRAINT term_records_gpa_check CHECK ((term_gpa IS NULL OR term_gpa BETWEEN 0 AND 10) AND (cumulative_gpa IS NULL OR cumulative_gpa BETWEEN 0 AND 10)),
    ADD CONSTRAINT term_records_standing_check CHECK (academic_standing IS NULL OR academic_standing IN ('good', 'warning', 'dismissal_review')),
    ADD CONSTRAINT term_records_credits_check CHECK (earned_credits <= attempted_credits AND gpa_credits <= attempted_credits);

-- @apply triggers/grades.sql

SELECT util.enable_audit('grade_change_requests'::regclass);

SELECT util.enable_audit('term_records'::regclass);

