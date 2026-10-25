create table "countries" ("id" bigserial not null primary key, "code" char(2) not null, "alpha3_code" char(3) not null, "numeric_code" char(3) null, "name" jsonb not null, "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "countries" add constraint "countries_code_unique" unique ("code");

alter table "countries" add constraint "countries_alpha3_code_unique" unique ("alpha3_code");

create table "languages" ("id" bigserial not null primary key, "code" varchar(3) not null, "alpha3_code" char(3) null, "name" jsonb not null, "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "languages" add constraint "languages_code_unique" unique ("code");

create table "lookup_types" ("id" bigserial not null primary key, "code" varchar(64) not null, "name" jsonb not null, "description" jsonb null, "is_system" boolean not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "lookup_types" add constraint "lookup_types_code_unique" unique ("code");

create table "lookup_values" ("id" bigserial not null primary key, "lookup_type_id" bigint not null, "code" varchar(64) not null, "name" jsonb not null, "sort_order" integer not null default '0', "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "lookup_values" add constraint "lookup_values_lookup_type_id_foreign" foreign key ("lookup_type_id") references "lookup_types" ("id") on delete cascade;

alter table "lookup_values" add constraint "lookup_values_lookup_type_id_code_unique" unique ("lookup_type_id", "code");

ALTER TABLE countries ADD CONSTRAINT countries_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE languages ADD CONSTRAINT languages_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE lookup_types ADD CONSTRAINT lookup_types_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE lookup_values ADD CONSTRAINT lookup_values_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE lookup_types ADD CONSTRAINT lookup_types_description_object_check CHECK (description IS NULL OR jsonb_typeof(description) = 'object');

SELECT util.enable_audit('countries'::regclass);

SELECT util.enable_audit('languages'::regclass);

SELECT util.enable_audit('lookup_types'::regclass);

SELECT util.enable_audit('lookup_values'::regclass);

