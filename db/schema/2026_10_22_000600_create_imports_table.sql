create table "imports" ("id" bigserial not null primary key, "completed_at" timestamp(0) with time zone null, "file_name" varchar(255) not null, "file_path" varchar(255) not null, "importer" varchar(255) not null, "processed_rows" integer not null default '0', "total_rows" integer not null, "successful_rows" integer not null default '0', "user_id" bigint not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "imports" add constraint "imports_user_id_foreign" foreign key ("user_id") references "users" ("id") on delete cascade;

