# unfold.decorators (django-unfold 0.x). Both decorators return the function they wrap with
# admin attributes added (``action`` wraps it in a permission check with the same call shape),
# so the decorated method keeps its own signature for the type checker.

from collections.abc import Callable, Iterable, Mapping
from typing import Any, overload

from django.db.models.expressions import BaseExpression, Combinable
from django_stubs_ext import StrOrPromise

@overload
def action[F: Callable[..., Any]](function: F, /) -> F: ...
@overload
def action[F: Callable[..., Any]](
    function: None = None,
    *,
    permissions: Iterable[str] | None = None,
    description: StrOrPromise | None = None,
    url_path: str | None = None,
    attrs: dict[str, Any] | None = None,
    icon: str | None = None,
    variant: Any = ...,
    dialog: Any = None,
    extra_options: dict[str, Any] | None = None,
) -> Callable[[F], F]: ...
@overload
def display[F: Callable[..., Any]](function: F, /) -> F: ...
@overload
def display[F: Callable[..., Any]](
    function: None = None,
    *,
    boolean: bool | None = None,
    image: bool | None = None,
    ordering: str | Combinable | BaseExpression | None = None,
    description: StrOrPromise | None = None,
    empty_value: str | None = None,
    dropdown: bool | None = None,
    label: bool | StrOrPromise | Mapping[Any, str] | None = None,
    header: bool | None = None,
    wrapper_class: str | None = None,
    formatting: str | None = None,
) -> Callable[[F], F]: ...
