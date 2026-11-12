"""Filipino date and number formats (Django ships none; values follow CLDR ``fil``, as Babel)."""

DATE_FORMAT = "F j, Y"
TIME_FORMAT = "g:i A"
DATETIME_FORMAT = "F j, Y g:i A"
YEAR_MONTH_FORMAT = "F Y"
MONTH_DAY_FORMAT = "F j"
SHORT_DATE_FORMAT = "n/j/Y"
SHORT_DATETIME_FORMAT = "n/j/Y g:i A"
FIRST_DAY_OF_WEEK = 0  # Sunday
DATE_INPUT_FORMATS = ["%m/%d/%Y", "%Y-%m-%d"]
DATETIME_INPUT_FORMATS = ["%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
DECIMAL_SEPARATOR = "."
THOUSAND_SEPARATOR = ","
NUMBER_GROUPING = 3
