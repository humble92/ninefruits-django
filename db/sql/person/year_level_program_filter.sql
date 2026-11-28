ALTER TABLE year_level_runs ADD COLUMN program_id bigint
    REFERENCES programs(id) ON DELETE RESTRICT;

CREATE INDEX year_level_changes_run_program_index
    ON year_level_changes (year_level_run_id, program_id);
