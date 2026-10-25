ALTER TABLE term_evaluations ALTER COLUMN minimum_response_percent SET DEFAULT 25;

update "term_evaluations" set "minimum_response_percent" = 25 where "minimum_response_percent" = 0 and "results_published_at" is null;

