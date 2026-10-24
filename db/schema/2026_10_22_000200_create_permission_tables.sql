create table "permissions" ("id" bigserial not null primary key, "name" varchar(255) not null, "guard_name" varchar(255) not null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "permissions" add constraint "permissions_name_guard_name_unique" unique ("name", "guard_name");

create table "roles" ("id" bigserial not null primary key, "name" varchar(255) not null, "guard_name" varchar(255) not null, "display_name" jsonb not null, "description" jsonb null, "persona" varchar(255) null, "is_system" boolean not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "roles" add constraint "roles_name_guard_name_unique" unique ("name", "guard_name");

alter table "roles" add constraint "roles_persona_unique" unique ("persona");

ALTER TABLE roles ADD CONSTRAINT roles_display_name_object_check CHECK (jsonb_typeof(display_name) = 'object');

create table "model_has_permissions" ("permission_id" bigint not null, "model_type" varchar(255) not null, "model_id" bigint not null);

alter table "model_has_permissions" add constraint "model_has_permissions_permission_id_foreign" foreign key ("permission_id") references "permissions" ("id") on delete cascade;

create index "model_has_permissions_model_id_model_type_index" on "model_has_permissions" ("model_id", "model_type");

alter table "model_has_permissions" add primary key ("permission_id", "model_id", "model_type");

create table "model_has_roles" ("role_id" bigint not null, "model_type" varchar(255) not null, "model_id" bigint not null);

alter table "model_has_roles" add constraint "model_has_roles_role_id_foreign" foreign key ("role_id") references "roles" ("id") on delete cascade;

create index "model_has_roles_model_id_model_type_index" on "model_has_roles" ("model_id", "model_type");

alter table "model_has_roles" add primary key ("role_id", "model_id", "model_type");

create table "role_has_permissions" ("permission_id" bigint not null, "role_id" bigint not null);

alter table "role_has_permissions" add constraint "role_has_permissions_permission_id_foreign" foreign key ("permission_id") references "permissions" ("id") on delete cascade;

alter table "role_has_permissions" add constraint "role_has_permissions_role_id_foreign" foreign key ("role_id") references "roles" ("id") on delete cascade;

alter table "role_has_permissions" add primary key ("permission_id", "role_id");

create table "role_assignments" ("id" bigserial not null primary key, "user_id" bigint not null, "role_id" bigint not null, "scope_type" varchar(32) not null, "scope_id" bigint null, "starts_at" timestamp(0) with time zone null, "ends_at" timestamp(0) with time zone null, "reason" text null, "assigned_by_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "role_assignments" add constraint "role_assignments_user_id_foreign" foreign key ("user_id") references "users" ("id") on delete cascade;

alter table "role_assignments" add constraint "role_assignments_role_id_foreign" foreign key ("role_id") references "roles" ("id") on delete cascade;

alter table "role_assignments" add constraint "role_assignments_assigned_by_id_foreign" foreign key ("assigned_by_id") references "users" ("id") on delete set null;

create index "role_assignments_user_id_role_id_index" on "role_assignments" ("user_id", "role_id");

ALTER TABLE role_assignments
    ADD CONSTRAINT role_assignments_scope_check
        CHECK ((scope_type = 'global') = (scope_id IS NULL)),
    ADD CONSTRAINT role_assignments_period_check
        CHECK (starts_at IS NULL OR ends_at IS NULL OR starts_at < ends_at);

SELECT util.enable_audit('permissions');

SELECT util.enable_audit('roles');

SELECT util.enable_audit('role_has_permissions');

SELECT util.enable_audit('role_assignments');

-- @apply functions/authorization.sql

