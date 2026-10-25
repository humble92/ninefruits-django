alter table "users" alter column "name" type varchar(255), alter column "name" drop not null, alter column "name" drop default, alter column "name" drop identity if exists;

alter table "users" add column "person_id" bigint null;

alter table "users" add constraint "users_person_id_foreign" foreign key ("person_id") references "people" ("id") on delete set null;

alter table "users" add column "failed_login_count" integer not null default '0';

alter table "users" add column "locked_until" timestamp(0) with time zone null;

alter table "users" add constraint "users_person_id_unique" unique ("person_id");

comment on column "users"."name" is NULL;

create table "user_identities" ("id" bigserial not null primary key, "user_id" bigint not null, "provider" varchar(64) not null, "subject" varchar(255) not null, "email" varchar(255) null, "linked_at" timestamp(0) with time zone not null, "last_used_at" timestamp(0) with time zone null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "user_identities" add constraint "user_identities_user_id_foreign" foreign key ("user_id") references "users" ("id") on delete cascade;

alter table "user_identities" add constraint "user_identities_provider_subject_unique" unique ("provider", "subject");

alter table "user_identities" add constraint "user_identities_user_id_provider_unique" unique ("user_id", "provider");

create table "account_invitations" ("id" bigserial not null primary key, "person_id" bigint not null, "email" varchar(255) not null, "token_hash" char(64) not null, "expires_at" timestamp(0) with time zone not null, "accepted_at" timestamp(0) with time zone null, "invited_by_id" bigint null, "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "account_invitations" add constraint "account_invitations_person_id_foreign" foreign key ("person_id") references "people" ("id") on delete cascade;

alter table "account_invitations" add constraint "account_invitations_invited_by_id_foreign" foreign key ("invited_by_id") references "users" ("id") on delete set null;

create index "account_invitations_person_id_index" on "account_invitations" ("person_id");

alter table "account_invitations" add constraint "account_invitations_token_hash_unique" unique ("token_hash");

SELECT util.enable_audit('user_identities'::regclass);

SELECT util.enable_audit('account_invitations'::regclass);

