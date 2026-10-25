# unfold.forms: only the dialog form base this project subclasses.

from typing import Any

from django import forms
from django.http import HttpRequest

class BaseDialogForm(forms.Form):
    form_before_template: str | None
    form_after_template: str | None
    request: HttpRequest
    object_id: int | str | None
    def __init__(self, request: HttpRequest, object_id: int | str | None = None, *args: Any, **kwargs: Any) -> None: ...
    def get_before_template_context(
        self, request: HttpRequest, object_id: int | str | None = None
    ) -> dict[str, Any]: ...
    def get_after_template_context(
        self, request: HttpRequest, object_id: int | str | None = None
    ) -> dict[str, Any]: ...
