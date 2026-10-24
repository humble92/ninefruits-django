-- Instructor timetable conflicts. Rooms use an exclusion constraint on section_meetings;
-- instructors are on another table (section_instructors), so triggers on both tables
-- check them. An advisory lock per instructor serializes concurrent assignments, and the
-- error uses SQLSTATE 23P01 (exclusion_violation) like the room constraint.

-- Meeting m of section s conflicts for instructor i when another active section taught by
-- i meets on the same weekday with overlapping times and dates.
CREATE OR REPLACE FUNCTION util.instructor_meeting_conflict(instructor bigint, meeting_section bigint, meeting_weekday smallint, meeting_times int4range, meeting_dates daterange)
    RETURNS bigint
    LANGUAGE sql STABLE
AS $$
    SELECT other.section_id
    FROM section_meetings AS other
    JOIN section_instructors AS si ON si.section_id = other.section_id
    WHERE si.instructor_id = instructor
      AND other.section_id <> meeting_section
      AND other.is_active
      AND other.weekday = meeting_weekday
      AND other.time_range && meeting_times
      AND other.date_range && meeting_dates
    LIMIT 1
$$;

-- Trigger section_meetings_after_write_check_instructors
CREATE OR REPLACE FUNCTION util.section_meetings_check_instructors() RETURNS trigger
    LANGUAGE plpgsql
AS $$
DECLARE
    instructor bigint;
    conflicting bigint;
BEGIN
    IF NOT NEW.is_active THEN
        RETURN NEW;
    END IF;

    FOR instructor IN SELECT instructor_id FROM section_instructors WHERE section_id = NEW.section_id ORDER BY instructor_id LOOP
        PERFORM pg_advisory_xact_lock(hashtextextended('section_instructor:' || instructor, 0));
        conflicting := util.instructor_meeting_conflict(instructor, NEW.section_id, NEW.weekday, NEW.time_range, NEW.date_range);

        IF conflicting IS NOT NULL THEN
            RAISE EXCEPTION 'instructor_conflict instructor=% section=% other_section=%', instructor, NEW.section_id, conflicting
                USING ERRCODE = 'exclusion_violation';
        END IF;
    END LOOP;

    RETURN NEW;
END
$$;

-- Trigger section_instructors_after_write_check_meetings
CREATE OR REPLACE FUNCTION util.section_instructors_check_meetings() RETURNS trigger
    LANGUAGE plpgsql
AS $$
DECLARE
    meeting record;
    conflicting bigint;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('section_instructor:' || NEW.instructor_id, 0));

    FOR meeting IN SELECT * FROM section_meetings WHERE section_id = NEW.section_id AND is_active LOOP
        conflicting := util.instructor_meeting_conflict(NEW.instructor_id, NEW.section_id, meeting.weekday, meeting.time_range, meeting.date_range);

        IF conflicting IS NOT NULL THEN
            RAISE EXCEPTION 'instructor_conflict instructor=% section=% other_section=%', NEW.instructor_id, NEW.section_id, conflicting
                USING ERRCODE = 'exclusion_violation';
        END IF;
    END LOOP;

    RETURN NEW;
END
$$;

-- Trigger sections_after_update_sync_meetings: meetings of a cancelled section stop
-- occupying rooms and instructors; reopening checks them again.
CREATE OR REPLACE FUNCTION util.sections_sync_meeting_activity() RETURNS trigger
    LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE section_meetings SET is_active = (NEW.status <> 'cancelled') WHERE section_id = NEW.id;

    RETURN NEW;
END
$$;
