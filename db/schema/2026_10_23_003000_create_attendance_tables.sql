create table "class_meetings" ("id" bigserial not null primary key, "section_id" bigint not null, "section_meeting_id" bigint null, "meeting_date" date not null, "start_time" time(0) without time zone not null, "end_time" time(0) without time zone not null, "room_id" bigint null, "status" varchar(16) not null default 'scheduled', "topic" varchar(200) null, "cancel_reason" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "class_meetings" add constraint "class_meetings_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

alter table "class_meetings" add constraint "class_meetings_section_meeting_id_foreign" foreign key ("section_meeting_id") references "section_meetings" ("id") on delete set null;

alter table "class_meetings" add constraint "class_meetings_room_id_foreign" foreign key ("room_id") references "rooms" ("id") on delete restrict;

alter table "class_meetings" add constraint "class_meetings_section_id_meeting_date_start_time_unique" unique ("section_id", "meeting_date", "start_time");

create table "attendance_records" ("id" bigserial not null primary key, "class_meeting_id" bigint not null, "enrollment_id" bigint not null, "status" varchar(16) not null, "note" varchar(200) null, "recorded_by_id" bigint null, "recorded_at" timestamp(0) with time zone not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "attendance_records" add constraint "attendance_records_class_meeting_id_foreign" foreign key ("class_meeting_id") references "class_meetings" ("id") on delete cascade;

alter table "attendance_records" add constraint "attendance_records_enrollment_id_foreign" foreign key ("enrollment_id") references "enrollments" ("id") on delete cascade;

alter table "attendance_records" add constraint "attendance_records_recorded_by_id_foreign" foreign key ("recorded_by_id") references "users" ("id") on delete set null;

alter table "attendance_records" add constraint "attendance_records_class_meeting_id_enrollment_id_unique" unique ("class_meeting_id", "enrollment_id");

create index "attendance_records_enrollment_id_index" on "attendance_records" ("enrollment_id");

ALTER TABLE class_meetings
    ADD CONSTRAINT class_meetings_status_check CHECK (status IN ('scheduled', 'cancelled')),
    ADD CONSTRAINT class_meetings_time_check CHECK (start_time < end_time),
    ADD CONSTRAINT class_meetings_cancel_check CHECK ((status = 'cancelled') = (cancel_reason IS NOT NULL));

ALTER TABLE attendance_records
    ADD CONSTRAINT attendance_records_status_check CHECK (status IN ('present', 'late', 'absent', 'excused'));

SELECT util.enable_audit('class_meetings'::regclass);

SELECT util.enable_audit('attendance_records'::regclass);

-- @apply functions/attendance.sql

-- @apply policies/attendance.sql

