create table "buildings" ("id" bigserial not null primary key, "code" varchar(32) not null, "name" jsonb not null, "address" text null, "is_active" boolean not null default '1', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "buildings" add constraint "buildings_code_unique" unique ("code");

create table "rooms" ("id" bigserial not null primary key, "building_id" bigint not null, "code" varchar(32) not null, "name" jsonb null, "room_type_id" bigint null, "org_unit_id" bigint null, "capacity" integer null, "is_schedulable" boolean not null default '1', "is_active" boolean not null default '1', "note" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "rooms" add constraint "rooms_building_id_foreign" foreign key ("building_id") references "buildings" ("id") on delete restrict;

alter table "rooms" add constraint "rooms_room_type_id_foreign" foreign key ("room_type_id") references "lookup_values" ("id") on delete set null;

alter table "rooms" add constraint "rooms_org_unit_id_foreign" foreign key ("org_unit_id") references "org_units" ("id") on delete set null;

alter table "rooms" add constraint "rooms_building_id_code_unique" unique ("building_id", "code");

ALTER TABLE buildings ADD CONSTRAINT buildings_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE rooms ADD CONSTRAINT rooms_name_object_check CHECK (name IS NULL OR jsonb_typeof(name) = 'object');

ALTER TABLE rooms ADD CONSTRAINT rooms_capacity_check CHECK (capacity IS NULL OR capacity >= 0);

SELECT util.enable_audit('buildings'::regclass);

SELECT util.enable_audit('rooms'::regclass);

