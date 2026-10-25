create table "people" ("id" bigserial not null primary key, "family_name" varchar(255) not null, "given_name" varchar(255) null, "name_variants" jsonb null, "birth_date" date null, "gender" varchar(16) null, "nationality_country_id" bigint null, "ethnicity_id" bigint null, "email" varchar(255) null, "phone" varchar(32) null, "address" text null, "postal_code" varchar(16) null, "national_id_encrypted" text null, "national_id_hash" char(64) null, "passport_number_encrypted" text null, "passport_number_hash" char(64) null, "merged_into_person_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "people" add constraint "people_nationality_country_id_foreign" foreign key ("nationality_country_id") references "countries" ("id") on delete set null;

alter table "people" add constraint "people_ethnicity_id_foreign" foreign key ("ethnicity_id") references "lookup_values" ("id") on delete set null;

alter table "people" add constraint "people_merged_into_person_id_foreign" foreign key ("merged_into_person_id") references "people" ("id") on delete set null;

create index "people_family_name_given_name_index" on "people" ("family_name", "given_name");

create index "people_birth_date_index" on "people" ("birth_date");

create index "people_national_id_hash_index" on "people" ("national_id_hash");

create index "people_passport_number_hash_index" on "people" ("passport_number_hash");

create table "guardians" ("id" bigserial not null primary key, "person_id" bigint not null, "relationship" varchar(32) not null, "full_name" varchar(255) not null, "phone" varchar(32) null, "email" varchar(255) null, "address" text null, "is_primary_contact" boolean not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "guardians" add constraint "guardians_person_id_foreign" foreign key ("person_id") references "people" ("id") on delete cascade;

create index "guardians_person_id_index" on "guardians" ("person_id");

create table "instructors" ("id" bigserial not null primary key, "person_id" bigint not null, "employee_number" varchar(32) not null, "org_unit_id" bigint not null, "employment_type" varchar(32) not null, "academic_title" jsonb null, "hire_date" date null, "end_date" date null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "instructors" add constraint "instructors_person_id_foreign" foreign key ("person_id") references "people" ("id") on delete restrict;

alter table "instructors" add constraint "instructors_org_unit_id_foreign" foreign key ("org_unit_id") references "org_units" ("id") on delete restrict;

create index "instructors_org_unit_id_index" on "instructors" ("org_unit_id");

alter table "instructors" add constraint "instructors_person_id_unique" unique ("person_id");

alter table "instructors" add constraint "instructors_employee_number_unique" unique ("employee_number");

ALTER TABLE people ADD CONSTRAINT people_name_variants_object_check CHECK (name_variants IS NULL OR jsonb_typeof(name_variants) = 'object');

ALTER TABLE instructors ADD CONSTRAINT instructors_academic_title_object_check CHECK (academic_title IS NULL OR jsonb_typeof(academic_title) = 'object');

ALTER TABLE people ADD CONSTRAINT people_not_merged_into_self_check CHECK (merged_into_person_id IS NULL OR merged_into_person_id <> id);

ALTER TABLE instructors ADD CONSTRAINT instructors_period_check CHECK (end_date IS NULL OR hire_date IS NULL OR end_date >= hire_date);

CREATE INDEX people_name_search_index ON people USING gin ((family_name || ' ' || coalesce(given_name, '') || ' ' || util.i18n_search_text(name_variants)) gin_trgm_ops);

SELECT util.enable_audit('people', ARRAY['national_id_encrypted', 'passport_number_encrypted']);

SELECT util.enable_audit('guardians'::regclass);

SELECT util.enable_audit('instructors'::regclass);

