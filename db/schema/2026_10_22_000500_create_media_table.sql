create table "media" ("id" bigserial not null primary key, "model_type" varchar(255) not null, "model_id" bigint not null, "uuid" uuid null, "collection_name" varchar(255) not null, "name" varchar(255) not null, "file_name" varchar(255) not null, "mime_type" varchar(255) null, "disk" varchar(255) not null, "conversions_disk" varchar(255) null, "size" bigint not null, "manipulations" json not null, "custom_properties" json not null, "generated_conversions" json not null, "responsive_images" json not null, "order_column" integer null, "created_at" timestamp(0) without time zone null, "updated_at" timestamp(0) without time zone null);

create index "media_model_type_model_id_index" on "media" ("model_type", "model_id");

alter table "media" add constraint "media_uuid_unique" unique ("uuid");

create index "media_order_column_index" on "media" ("order_column");

