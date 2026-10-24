create table "term_sessions" ("id" bigserial not null primary key, "term_id" bigint not null, "code" varchar(32) not null, "name" jsonb not null, "start_date" date not null, "end_date" date not null, "is_full_term" boolean not null default '0', "sort_order" integer not null default '0', "created_at" timestamp(0) with time zone null, "updated_at" timestamp(0) with time zone null);

alter table "term_sessions" add constraint "term_sessions_term_id_foreign" foreign key ("term_id") references "terms" ("id") on delete cascade;

alter table "term_sessions" add constraint "term_sessions_term_id_code_unique" unique ("term_id", "code");

alter table "term_sessions" add constraint "term_sessions_id_term_id_unique" unique ("id", "term_id");

ALTER TABLE term_sessions ADD CONSTRAINT term_sessions_name_object_check CHECK (jsonb_typeof(name) = 'object');

ALTER TABLE term_sessions ADD CONSTRAINT term_sessions_order_check CHECK (end_date >= start_date);

CREATE UNIQUE INDEX term_sessions_single_full_term_unique ON term_sessions (term_id) WHERE is_full_term;

-- @apply functions/terms.sql

CREATE TRIGGER term_sessions_before_write_within_term
    BEFORE INSERT OR UPDATE OF term_id, start_date, end_date ON term_sessions
    FOR EACH ROW EXECUTE FUNCTION util.term_sessions_within_term();

alter table "term_windows" add column "term_session_id" bigint null;

create index "term_windows_term_session_id_index" on "term_windows" ("term_session_id");

ALTER TABLE term_windows ADD CONSTRAINT term_windows_term_session_id_foreign FOREIGN KEY (term_session_id, term_id) REFERENCES term_sessions (id, term_id) ON DELETE CASCADE;

INSERT INTO term_sessions (term_id, code, name, start_date, end_date, is_full_term, created_at, updated_at)
SELECT id, 'FULL', '{"en": "Full term", "ko": "전체 학기", "zh_CN": "全学期"}'::jsonb, start_date, end_date, true, now(), now()
FROM terms;

UPDATE term_windows AS w SET term_session_id = s.id
FROM term_sessions AS s
WHERE s.term_id = w.term_id AND s.is_full_term
  AND w.window_type IN ('add_drop', 'withdrawal', 'grade_entry', 'grade_appeal', 'course_evaluation');

ALTER TABLE term_windows ADD CONSTRAINT term_windows_session_check CHECK (
    (window_type IN ('add_drop', 'withdrawal', 'grade_entry', 'grade_appeal', 'course_evaluation')) = (term_session_id IS NOT NULL)
);

SELECT util.enable_audit('term_sessions'::regclass);

