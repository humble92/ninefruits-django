create table "sections" ("id" bigserial not null primary key, "term_id" bigint not null, "term_session_id" bigint not null, "course_id" bigint not null, "course_version_id" bigint not null, "section_code" varchar(16) not null, "org_unit_id" bigint not null, "capacity" integer not null, "status" varchar(16) not null default 'draft', "eligibility" jsonb null, "exclusion" jsonb null, "instruction_language" varchar(16) null, "note" jsonb null, "copied_from_section_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "sections" add constraint "sections_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete restrict;

alter table "sections" add constraint "sections_course_id_foreign" foreign key ("course_id") references "courses" ("id") on delete restrict;

alter table "sections" add constraint "sections_org_unit_id_foreign" foreign key ("org_unit_id") references "org_units" ("id") on delete restrict;

alter table "sections" add constraint "sections_copied_from_section_id_foreign" foreign key ("copied_from_section_id") references "sections" ("id") on delete set null;

alter table "sections" add constraint "sections_term_id_course_id_section_code_unique" unique ("term_id", "course_id", "section_code");

create index "sections_term_id_org_unit_id_index" on "sections" ("term_id", "org_unit_id");

create index "sections_course_version_id_index" on "sections" ("course_version_id");

ALTER TABLE sections ADD CONSTRAINT sections_term_session_id_foreign FOREIGN KEY (term_session_id, term_id) REFERENCES term_sessions (id, term_id) ON DELETE RESTRICT;

ALTER TABLE sections ADD CONSTRAINT sections_course_version_id_foreign FOREIGN KEY (course_version_id, course_id) REFERENCES course_versions (id, course_id) ON DELETE RESTRICT;

create table "section_instructors" ("id" bigserial not null primary key, "section_id" bigint not null, "instructor_id" bigint not null, "role" varchar(16) not null default 'primary', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "section_instructors" add constraint "section_instructors_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

alter table "section_instructors" add constraint "section_instructors_instructor_id_foreign" foreign key ("instructor_id") references "instructors" ("id") on delete restrict;

alter table "section_instructors" add constraint "section_instructors_section_id_instructor_id_unique" unique ("section_id", "instructor_id");

create index "section_instructors_instructor_id_index" on "section_instructors" ("instructor_id");

create table "section_meetings" ("id" bigserial not null primary key, "section_id" bigint not null, "weekday" smallint not null, "start_time" time(0) without time zone not null, "end_time" time(0) without time zone not null, "room_id" bigint null, "start_date" date not null, "end_date" date not null, "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "section_meetings" add constraint "section_meetings_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

alter table "section_meetings" add constraint "section_meetings_room_id_foreign" foreign key ("room_id") references "rooms" ("id") on delete restrict;

create index "section_meetings_section_id_index" on "section_meetings" ("section_id");

create index "section_meetings_room_id_index" on "section_meetings" ("room_id");

create table "section_seat_groups" ("id" bigserial not null primary key, "section_id" bigint not null, "name" jsonb not null, "capacity" integer not null, "eligibility" jsonb null, "releases_at" timestamp(0) with time zone null, "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "section_seat_groups" add constraint "section_seat_groups_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

create index "section_seat_groups_section_id_index" on "section_seat_groups" ("section_id");

create table "syllabi" ("id" bigserial not null primary key, "section_id" bigint not null, "language" varchar(16) not null, "content" jsonb not null, "published_at" timestamp(0) with time zone null, "updated_by_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "syllabi" add constraint "syllabi_section_id_foreign" foreign key ("section_id") references "sections" ("id") on delete cascade;

alter table "syllabi" add constraint "syllabi_updated_by_id_foreign" foreign key ("updated_by_id") references "users" ("id") on delete set null;

alter table "syllabi" add constraint "syllabi_section_id_unique" unique ("section_id");

ALTER TABLE sections ADD CONSTRAINT sections_note_object_check CHECK (note IS NULL OR jsonb_typeof(note) = 'object');

ALTER TABLE section_seat_groups ADD CONSTRAINT section_seat_groups_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE sections
    ADD CONSTRAINT sections_capacity_check CHECK (capacity >= 0),
    ADD CONSTRAINT sections_status_check CHECK (status IN ('draft', 'published', 'cancelled'));

ALTER TABLE section_instructors ADD CONSTRAINT section_instructors_role_check CHECK (role IN ('primary', 'co_instructor', 'assistant'));

ALTER TABLE section_meetings
    ADD COLUMN time_range int4range GENERATED ALWAYS AS (int4range(
        (EXTRACT(HOUR FROM start_time) * 60 + EXTRACT(MINUTE FROM start_time))::int,
        (EXTRACT(HOUR FROM end_time) * 60 + EXTRACT(MINUTE FROM end_time))::int
    )) STORED,
    ADD COLUMN date_range daterange GENERATED ALWAYS AS (daterange(start_date, end_date, '[]')) STORED,
    ADD CONSTRAINT section_meetings_weekday_check CHECK (weekday BETWEEN 1 AND 7),
    ADD CONSTRAINT section_meetings_time_check CHECK (end_time > start_time),
    ADD CONSTRAINT section_meetings_date_check CHECK (end_date >= start_date),
    ADD CONSTRAINT section_meetings_room_excl EXCLUDE USING gist (room_id WITH =, weekday WITH =, time_range WITH &&, date_range WITH &&)
        WHERE (room_id IS NOT NULL AND is_active),
    ADD CONSTRAINT section_meetings_section_excl EXCLUDE USING gist (section_id WITH =, weekday WITH =, time_range WITH &&, date_range WITH &&);

ALTER TABLE section_seat_groups ADD CONSTRAINT section_seat_groups_capacity_check CHECK (capacity >= 0);

ALTER TABLE syllabi ADD CONSTRAINT syllabi_content_object_check CHECK (jsonb_typeof(content) = 'object');

-- @apply functions/sections.sql

CREATE TRIGGER section_meetings_after_write_check_instructors
    AFTER INSERT OR UPDATE OF section_id, weekday, start_time, end_time, start_date, end_date, is_active ON section_meetings
    FOR EACH ROW EXECUTE FUNCTION util.section_meetings_check_instructors();

CREATE TRIGGER section_instructors_after_write_check_meetings
    AFTER INSERT OR UPDATE OF section_id, instructor_id ON section_instructors
    FOR EACH ROW EXECUTE FUNCTION util.section_instructors_check_meetings();

CREATE TRIGGER sections_after_update_sync_meetings
    AFTER UPDATE OF status ON sections
    FOR EACH ROW WHEN (OLD.status IS DISTINCT FROM NEW.status) EXECUTE FUNCTION util.sections_sync_meeting_activity();

SELECT util.enable_audit('sections'::regclass);

SELECT util.enable_audit('section_instructors'::regclass);

SELECT util.enable_audit('section_meetings'::regclass);

SELECT util.enable_audit('section_seat_groups'::regclass);

SELECT util.enable_audit('syllabi'::regclass);

