create table "users" ("id" bigserial not null primary key, "name" varchar(255) not null, "email" varchar(255) not null, "email_verified_at" timestamp(0) with time zone null, "password" varchar(255) not null, "two_factor_secret" text null, "two_factor_recovery_codes" text null, "two_factor_confirmed_at" timestamp(0) with time zone null, "email_mfa_enabled_at" timestamp(0) with time zone null, "mfa_grace_started_at" timestamp(0) with time zone null, "locale" varchar(20) null, "is_active" boolean not null default '1', "last_login_at" timestamp(0) with time zone null, "remember_token" varchar(100) null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "users" add constraint "users_email_unique" unique ("email");

SELECT util.enable_audit('users', ARRAY['password', 'remember_token', 'two_factor_secret', 'two_factor_recovery_codes']);

create table "password_reset_tokens" ("email" varchar(255) not null, "token" varchar(255) not null, "created_at" timestamp(0) with time zone null);

alter table "password_reset_tokens" add primary key ("email");

create table "sessions" ("id" varchar(255) not null, "user_id" bigint null, "ip_address" varchar(45) null, "user_agent" text null, "payload" text not null, "last_activity" integer not null);

alter table "sessions" add primary key ("id");

create index "sessions_user_id_index" on "sessions" ("user_id");

create index "sessions_last_activity_index" on "sessions" ("last_activity");

