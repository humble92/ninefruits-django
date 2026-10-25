create table "settings" ("id" bigserial not null primary key, "group" varchar(255) not null, "name" varchar(255) not null, "locked" boolean not null default '0', "payload" jsonb not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "settings" add constraint "settings_group_name_unique" unique ("group", "name");

SELECT util.enable_audit('settings');

