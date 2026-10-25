"""Options for the demo seeders, set by ``setup_demo`` (original ``App\\Support\\Setup\\DemoOptions``)."""

from __future__ import annotations

import contextvars
import random
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from ninefruits.setup import conf


class DemoRefused(RuntimeError):
    pass


@dataclass
class DemoOptions:
    size: str = "small"
    seed: int | None = None
    rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.size not in conf.DEMO_SIZES:
            raise ImproperlyConfigured(f"Unknown demo size [{self.size}].")
        # Deterministic with --seed; every seeder draws from this generator in a fixed order.
        self.rng = random.Random(self.seed)  # noqa: S311 - demo data, not security

    def student_count(self) -> int:
        return conf.DEMO_SIZES[self.size]

    def scale(self, small_count: int) -> int:
        """Scales a small-size count to the chosen size."""
        return max(1, small_count * self.student_count() // conf.DEMO_SIZES["small"])


_current: contextvars.ContextVar[DemoOptions | None] = contextvars.ContextVar("demo_options", default=None)


def current_options() -> DemoOptions:
    options = _current.get()
    if options is None:
        options = DemoOptions()
        _current.set(options)
    return options


@contextmanager
def use_options(options: DemoOptions) -> Iterator[DemoOptions]:
    token = _current.set(options)
    try:
        yield options
    finally:
        _current.reset(token)


def is_production() -> bool:
    return getattr(settings, "DJANGO_ENV", "production") == "production"


def ensure_not_production() -> None:
    if is_production():
        raise DemoRefused("Demo data cannot be created in production.")
