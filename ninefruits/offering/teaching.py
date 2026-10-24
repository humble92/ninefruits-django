"""Extra columns of the portal teaching page (original ``my-teaching`` table): later phases add
their links per section (attendance, grade entry, evaluation results, LMS)::

    from ninefruits.offering.teaching import register_column
    register_column("attendance", _("Attendance"), lambda request, section: format_html(...))
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest


@dataclass(frozen=True)
class TeachingColumn:
    key: str
    header: Any
    render: Callable[[HttpRequest, Any], str]
    order: int = 100


_columns: dict[str, TeachingColumn] = {}


def register_column(key: str, header: Any, render: Callable[[HttpRequest, Any], str], order: int = 100) -> None:
    _columns[key] = TeachingColumn(key, header, render, order)


def unregister_column(key: str) -> None:
    _columns.pop(key, None)


def columns() -> list[TeachingColumn]:
    return sorted(_columns.values(), key=lambda column: (column.order, column.key))
