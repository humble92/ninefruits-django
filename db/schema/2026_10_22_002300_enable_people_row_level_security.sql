-- @apply functions/people.sql

ALTER TABLE people ADD COLUMN created_by_id bigint DEFAULT util.current_user_id() REFERENCES users (id) ON DELETE SET NULL;

-- @apply policies/student_records.sql

-- @apply policies/people.sql

