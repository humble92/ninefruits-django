"""A person's photo from the private storage, for users who may see the person (original
``PersonPhotoController``)."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from ninefruits.media.models import Media
from ninefruits.media.views import PrivateMediaDownloadView
from ninefruits.person.models import Person


class PersonPhotoView(PrivateMediaDownloadView):
    disposition: ClassVar[Literal["attachment", "inline"]] = "inline"
    cache_control: ClassVar[str] = "private, max-age=300"

    def get_media(self, request: HttpRequest, **kwargs: Any) -> Media | None:
        person: Person = get_object_or_404(Person.objects.visible_to(request.user), pk=kwargs["pk"])
        if not request.user.has_perm("view", person):
            raise PermissionDenied
        return person.get_first_media(Person.PHOTO_COLLECTION)
