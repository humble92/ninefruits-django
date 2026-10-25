create table "notifications" ("id" uuid not null, "type" varchar(255) not null, "notifiable_type" varchar(255) not null, "notifiable_id" bigint not null, "data" text not null, "read_at" timestamp(0) with time zone null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

create index "notifications_notifiable_type_notifiable_id_index" on "notifications" ("notifiable_type", "notifiable_id");

alter table "notifications" add primary key ("id");

