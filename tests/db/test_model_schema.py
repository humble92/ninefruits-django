"""Models describe the schema created from db/schema/ (domain migrations are state only, see
ninefruits/core/management/commands/makemigrations.py). This test fails when a model field and
its column disagree, so a state-only migration can never drift from the database."""

import pytest
from django.apps import apps
from django.db import connection, models

TYPE_FAMILIES = {
    "AutoField": {"integer"},
    "BigAutoField": {"bigint"},
    "SmallAutoField": {"smallint"},
    "IntegerField": {"integer"},
    "PositiveIntegerField": {"integer"},
    "BigIntegerField": {"bigint"},
    "PositiveBigIntegerField": {"bigint"},
    "SmallIntegerField": {"smallint"},
    "PositiveSmallIntegerField": {"smallint"},
    "BooleanField": {"boolean"},
    "CharField": {"character varying", "character", "text"},
    "EmailField": {"character varying"},
    "SlugField": {"character varying"},
    "URLField": {"character varying"},
    "TextField": {"text", "character varying"},
    "DateField": {"date"},
    "DateTimeField": {"timestamp with time zone", "timestamp without time zone"},
    "TimeField": {"time without time zone"},
    "DecimalField": {"numeric"},
    "FloatField": {"double precision", "real"},
    "JSONField": {"jsonb", "json"},
    "UUIDField": {"uuid"},
    "GenericIPAddressField": {"inet", "character varying"},
    "BinaryField": {"bytea"},
    "DurationField": {"interval"},
    "DateRangeField": {"daterange"},
    "DateTimeRangeField": {"tstzrange"},
    "ArrayField": {"ARRAY"},
}


def _columns(table: str) -> dict[str, tuple[str, bool, int | None]]:
    schema, _, name = table.rpartition('"."') if '"."' in table else ("public", "", table)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type, is_nullable = 'YES', character_maximum_length "
            "FROM information_schema.columns WHERE table_schema = %s AND table_name = %s",
            [schema or "public", name],
        )
        return {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}


def _ninefruits_models() -> list[type[models.Model]]:
    return [
        model
        for model in apps.get_models()
        if model.__module__.startswith("ninefruits.") and not model._meta.proxy and not model._meta.swapped
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("model", _ninefruits_models(), ids=lambda m: m._meta.label)
def test_model_matches_table(model: type[models.Model]) -> None:
    columns = _columns(model._meta.db_table)
    assert columns, f"{model._meta.db_table} does not exist"
    problems = []
    for field in model._meta.concrete_fields:
        column = field.column
        if column not in columns:
            problems.append(f"{column}: no such column")
            continue
        data_type, nullable, max_length = columns[column]
        internal = field.get_internal_type()
        if isinstance(field, models.ForeignKey | models.OneToOneField):
            internal = (
                field.target_field.get_internal_type().replace("Auto", "Integer").replace("BigInteger", "BigInteger")
            )
            if internal == "BigIntegerField" or internal == "BigIntegerField":
                pass
        family = TYPE_FAMILIES.get(internal) or TYPE_FAMILIES.get(type(field).__name__)
        if internal in ("BigIntegerField",) or field.get_internal_type() == "ForeignKey":
            family = family or {"bigint"}
        if family and data_type not in family:
            problems.append(f"{column}: {internal} but column is {data_type}")
        if field.null != nullable and not field.primary_key and not getattr(field, "generated", False):
            problems.append(f"{column}: null={field.null} but column nullable={nullable}")
        if internal == "CharField" and max_length is not None and field.max_length != max_length:
            problems.append(f"{column}: max_length={field.max_length} but column length {max_length}")
    assert problems == [], f"{model._meta.label}: " + "; ".join(problems)
