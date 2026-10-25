create table "term_types" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "is_regular" boolean not null default '1', "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "term_types" add constraint "term_types_code_unique" unique ("code");

create table "academic_years" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "start_date" date not null, "end_date" date not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "academic_years" add constraint "academic_years_code_unique" unique ("code");

create table "terms" ("id" bigserial not null primary key, "academic_year_id" bigint not null, "term_type_id" bigint not null, "code" varchar(32) not null, "name" jsonb not null, "start_date" date not null, "end_date" date not null, "status" varchar(32) not null default 'planned', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "terms" add constraint "terms_academic_year_id_foreign" foreign key ("academic_year_id") references "academic_years" ("id") on delete restrict;

alter table "terms" add constraint "terms_term_type_id_foreign" foreign key ("term_type_id") references "term_types" ("id") on delete restrict;

alter table "terms" add constraint "terms_academic_year_id_term_type_id_unique" unique ("academic_year_id", "term_type_id");

alter table "terms" add constraint "terms_code_unique" unique ("code");

create table "term_windows" ("id" bigserial not null primary key, "term_id" bigint not null, "window_type" varchar(64) not null, "name" jsonb null, "opens_at" timestamp(0) with time zone not null, "closes_at" timestamp(0) with time zone not null, "eligibility" jsonb null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "term_windows" add constraint "term_windows_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete cascade;

create index "term_windows_window_type_opens_at_closes_at_index" on "term_windows" ("window_type", "opens_at", "closes_at");

create table "time_slots" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "start_time" time(0) without time zone not null, "end_time" time(0) without time zone not null, "weekdays" jsonb not null, "sort_order" integer not null default '0', "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "time_slots" add constraint "time_slots_code_unique" unique ("code");

ALTER TABLE term_types ADD CONSTRAINT term_types_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE academic_years ADD CONSTRAINT academic_years_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE terms ADD CONSTRAINT terms_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE time_slots ADD CONSTRAINT time_slots_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE term_windows ADD CONSTRAINT term_windows_name_object_check CHECK (name IS NULL OR jsonb_typeof(name) = 'object');

ALTER TABLE academic_years
    ADD COLUMN year_period daterange GENERATED ALWAYS AS (daterange(start_date, end_date, '[]')) STORED,
    ADD CONSTRAINT academic_years_year_period_order_check CHECK (end_date IS NULL OR end_date >= start_date);

ALTER TABLE terms
    ADD COLUMN instruction_period daterange GENERATED ALWAYS AS (daterange(start_date, end_date, '[]')) STORED,
    ADD CONSTRAINT terms_instruction_period_order_check CHECK (end_date IS NULL OR end_date >= start_date);

ALTER TABLE academic_years ADD CONSTRAINT academic_years_no_overlap_excl EXCLUDE USING gist (year_period WITH &&);

ALTER TABLE terms ADD CONSTRAINT terms_no_overlap_excl EXCLUDE USING gist (term_type_id WITH =, instruction_period WITH &&);

ALTER TABLE term_windows ADD CONSTRAINT term_windows_order_check CHECK (closes_at > opens_at);

ALTER TABLE time_slots ADD CONSTRAINT time_slots_order_check CHECK (end_time > start_time);

ALTER TABLE time_slots ADD CONSTRAINT time_slots_weekdays_array_check CHECK (jsonb_typeof(weekdays) = 'array');

SELECT util.enable_audit('term_types'::regclass);

SELECT util.enable_audit('academic_years'::regclass);

SELECT util.enable_audit('terms'::regclass);

SELECT util.enable_audit('term_windows'::regclass);

SELECT util.enable_audit('time_slots'::regclass);

