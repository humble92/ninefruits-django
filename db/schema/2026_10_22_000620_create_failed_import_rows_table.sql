create table "failed_import_rows" ("id" bigserial not null primary key, "data" jsonb not null, "import_id" bigint not null, "validation_error" text null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "failed_import_rows" add constraint "failed_import_rows_import_id_foreign" foreign key ("import_id") references "imports" ("id") on delete cascade;

