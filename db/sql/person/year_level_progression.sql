CREATE TABLE year_level_rules (
    id bigserial PRIMARY KEY,
    name jsonb NOT NULL,
    basis varchar(16) NOT NULL CHECK (basis IN ('credits', 'terms', 'manual')),
    thresholds jsonb NOT NULL CHECK (jsonb_typeof(thresholds) = 'array'),
    is_default boolean NOT NULL DEFAULT false,
    created_at timestamptz,
    updated_at timestamptz
);

CREATE UNIQUE INDEX year_level_rules_single_default ON year_level_rules (is_default) WHERE is_default;

ALTER TABLE programs ADD COLUMN year_level_rule_id bigint REFERENCES year_level_rules(id) ON DELETE RESTRICT;
CREATE INDEX programs_year_level_rule_id_index ON programs (year_level_rule_id);

CREATE TABLE year_level_runs (
    id bigserial PRIMARY KEY,
    term_id bigint NOT NULL REFERENCES terms(id) ON DELETE RESTRICT,
    cutoff_date date NOT NULL,
    status varchar(16) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'applied', 'canceled')),
    scheduled_at timestamptz,
    applied_at timestamptz,
    approved_by_id bigint REFERENCES users(id) ON DELETE RESTRICT,
    created_at timestamptz,
    updated_at timestamptz
);

CREATE UNIQUE INDEX year_level_runs_active_term ON year_level_runs (term_id) WHERE status IN ('draft', 'scheduled');
CREATE INDEX year_level_runs_due ON year_level_runs (scheduled_at) WHERE status = 'scheduled';

CREATE TABLE year_level_changes (
    id bigserial PRIMARY KEY,
    year_level_run_id bigint NOT NULL REFERENCES year_level_runs(id) ON DELETE RESTRICT,
    student_record_id bigint NOT NULL REFERENCES student_records(id) ON DELETE RESTRICT,
    program_id bigint NOT NULL REFERENCES programs(id) ON DELETE RESTRICT,
    from_level smallint NOT NULL CHECK (from_level BETWEEN 1 AND 10),
    to_level smallint NOT NULL CHECK (to_level BETWEEN 2 AND 10 AND to_level > from_level),
    rule_name varchar(255) NOT NULL,
    basis varchar(16) NOT NULL CHECK (basis IN ('credits', 'terms')),
    measured_value numeric(10,1) NOT NULL,
    outcome varchar(16) CHECK (outcome IN ('applied', 'stale', 'excluded')),
    UNIQUE (year_level_run_id, student_record_id)
);

ALTER TABLE year_level_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY year_level_rules_read ON year_level_rules FOR SELECT USING (
    (SELECT util.has_permission('student_records.manage'))
    OR (SELECT util.has_permission('programs.manage'))
    OR cardinality((SELECT util.permission_scope_ids('programs.manage', 'org_unit'))) > 0
    OR cardinality((SELECT util.permission_scope_ids('programs.manage', 'program'))) > 0
);
CREATE POLICY year_level_rules_manage ON year_level_rules FOR ALL
    USING ((SELECT util.has_permission('institution_settings.manage')))
    WITH CHECK ((SELECT util.has_permission('institution_settings.manage')));
CREATE POLICY year_level_rules_system ON year_level_rules FOR ALL
    USING ((SELECT util.is_system_context())) WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE year_level_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY year_level_runs_staff ON year_level_runs FOR ALL
    USING ((SELECT util.has_permission('student_records.manage')))
    WITH CHECK ((SELECT util.has_permission('student_records.manage')));
CREATE POLICY year_level_runs_system ON year_level_runs FOR ALL
    USING ((SELECT util.is_system_context())) WITH CHECK ((SELECT util.is_system_context()));

ALTER TABLE year_level_changes ENABLE ROW LEVEL SECURITY;
CREATE POLICY year_level_changes_staff ON year_level_changes FOR ALL
    USING ((SELECT util.has_permission('student_records.manage')))
    WITH CHECK ((SELECT util.has_permission('student_records.manage')));
CREATE POLICY year_level_changes_system ON year_level_changes FOR ALL
    USING ((SELECT util.is_system_context())) WITH CHECK ((SELECT util.is_system_context()));

SELECT util.enable_audit('year_level_rules');
SELECT util.enable_audit('year_level_runs');
SELECT util.enable_audit('year_level_changes');
