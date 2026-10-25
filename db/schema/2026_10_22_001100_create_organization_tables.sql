create table "org_unit_types" ("id" bigserial not null primary key, "code" varchar(64) not null, "name" jsonb not null, "is_academic" boolean not null default '1', "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "org_unit_types" add constraint "org_unit_types_code_unique" unique ("code");

create table "org_units" ("id" bigserial not null primary key, "code" varchar(64) not null, "name" jsonb not null, "short_name" jsonb null, "org_unit_type_id" bigint not null, "parent_id" bigint null, "effective_start_date" date not null, "effective_end_date" date null, "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "org_units" add constraint "org_units_org_unit_type_id_foreign" foreign key ("org_unit_type_id") references "org_unit_types" ("id") on delete restrict;

alter table "org_units" add constraint "org_units_parent_id_foreign" foreign key ("parent_id") references "org_units" ("id") on delete restrict;

create index "org_units_parent_id_index" on "org_units" ("parent_id");

alter table "org_units" add constraint "org_units_code_unique" unique ("code");

create table "org_unit_successions" ("id" bigserial not null primary key, "predecessor_org_unit_id" bigint not null, "successor_org_unit_id" bigint not null, "change_type" varchar(32) not null, "effective_date" date not null, "reason" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "org_unit_successions" add constraint "org_unit_successions_predecessor_org_unit_id_foreign" foreign key ("predecessor_org_unit_id") references "org_units" ("id") on delete cascade;

alter table "org_unit_successions" add constraint "org_unit_successions_successor_org_unit_id_foreign" foreign key ("successor_org_unit_id") references "org_units" ("id") on delete cascade;

alter table "org_unit_successions" add constraint "org_unit_successions_predecessor_org_unit_id_successor_org_unit_id_unique" unique ("predecessor_org_unit_id", "successor_org_unit_id");

create table "programs" ("id" bigserial not null primary key, "code" varchar(64) not null, "name" jsonb not null, "degree_title" jsonb null, "degree_level" varchar(32) not null, "org_unit_id" bigint not null, "standard_duration_years" decimal(3, 1) null, "effective_start_date" date not null, "effective_end_date" date null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "programs" add constraint "programs_org_unit_id_foreign" foreign key ("org_unit_id") references "org_units" ("id") on delete restrict;

alter table "programs" add constraint "programs_code_unique" unique ("code");

ALTER TABLE org_unit_types ADD CONSTRAINT org_unit_types_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE org_units ADD CONSTRAINT org_units_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE programs ADD CONSTRAINT programs_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE org_units ADD CONSTRAINT org_units_short_name_object_check CHECK (short_name IS NULL OR jsonb_typeof(short_name) = 'object');

ALTER TABLE programs ADD CONSTRAINT programs_degree_title_object_check CHECK (degree_title IS NULL OR jsonb_typeof(degree_title) = 'object');

ALTER TABLE org_units
    ADD COLUMN effective_period daterange GENERATED ALWAYS AS (daterange(effective_start_date, effective_end_date, '[]')) STORED,
    ADD CONSTRAINT org_units_effective_period_order_check CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date);

ALTER TABLE programs
    ADD COLUMN effective_period daterange GENERATED ALWAYS AS (daterange(effective_start_date, effective_end_date, '[]')) STORED,
    ADD CONSTRAINT programs_effective_period_order_check CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date);

ALTER TABLE org_units ADD CONSTRAINT org_units_not_own_parent_check CHECK (parent_id IS NULL OR parent_id <> id);

ALTER TABLE org_unit_successions ADD CONSTRAINT org_unit_successions_distinct_check CHECK (predecessor_org_unit_id <> successor_org_unit_id);

CREATE INDEX org_units_name_search_index ON org_units USING gin (util.i18n_search_text(name) gin_trgm_ops);

CREATE INDEX programs_name_search_index ON programs USING gin (util.i18n_search_text(name) gin_trgm_ops);

-- @apply functions/org_units.sql

CREATE TRIGGER org_units_before_write_prevent_cycle
BEFORE INSERT OR UPDATE OF parent_id ON org_units
FOR EACH ROW EXECUTE FUNCTION util.org_units_prevent_cycle();

SELECT util.enable_audit('org_unit_types'::regclass);

SELECT util.enable_audit('org_units'::regclass);

SELECT util.enable_audit('org_unit_successions'::regclass);

SELECT util.enable_audit('programs'::regclass);

