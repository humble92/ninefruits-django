"""Pagination of list endpoints: ``?limit=`` (default 100, at most 1,000) and ``?offset=``."""

from __future__ import annotations

from rest_framework.pagination import LimitOffsetPagination as BaseLimitOffsetPagination


class LimitOffsetPagination(BaseLimitOffsetPagination):
    default_limit = 100
    max_limit = 1000
