"""Demo seeders (original ``database/seeders/Demo``): a fictional university for development,
training and demonstrations. Never in production; accounts use the reserved ``.test`` domain."""

from .options import DemoOptions, current_options, ensure_not_production, use_options

__all__ = ["DemoOptions", "current_options", "ensure_not_production", "use_options"]
