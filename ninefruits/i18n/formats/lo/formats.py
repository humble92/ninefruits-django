"""Lao date and number formats (Django ships none; values follow CLDR ``lo``, as Babel)."""

DATE_FORMAT = "j F Y"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = "j F Y H:i"
YEAR_MONTH_FORMAT = "F Y"
MONTH_DAY_FORMAT = "j F"
SHORT_DATE_FORMAT = "j/n/Y"
SHORT_DATETIME_FORMAT = "j/n/Y H:i"
FIRST_DAY_OF_WEEK = 0  # Sunday
DATE_INPUT_FORMATS = ["%d/%m/%Y", "%Y-%m-%d"]
DATETIME_INPUT_FORMATS = ["%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3
