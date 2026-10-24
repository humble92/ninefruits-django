-- Trigger term_sessions_before_write_within_term: a session lies within its term.
CREATE OR REPLACE FUNCTION util.term_sessions_within_term() RETURNS trigger
    LANGUAGE plpgsql
AS $$
DECLARE
    term_start date;
    term_end date;
BEGIN
    SELECT start_date, end_date INTO term_start, term_end FROM terms WHERE id = NEW.term_id;

    IF NEW.start_date < term_start OR NEW.end_date > term_end THEN
        RAISE EXCEPTION 'Term session % (% to %) must lie within its term (% to %)', NEW.code, NEW.start_date, NEW.end_date, term_start, term_end
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END
$$;
