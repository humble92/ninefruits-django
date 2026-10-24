create table "features" ("id" bigserial not null primary key, "name" varchar(255) not null, "scope" varchar(255) not null, "value" text not null, "created_at" timestamp(0) without time zone null, "updated_at" timestamp(0) without time zone null);

alter table "features" add constraint "features_name_scope_unique" unique ("name", "scope");

