"""Portal routes of the offering, included in ``ninefruits.portal.urls`` (names ``portal:...``)."""

from __future__ import annotations

from django.urls import path

from ninefruits.offering.views.portal import CourseCatalogView, MyTeachingView, SectionDetailView, SyllabusEditorView

urlpatterns = [
    path("catalog/", CourseCatalogView.as_view(), name="catalog"),
    path("sections/<int:pk>/", SectionDetailView.as_view(), name="section_detail"),
    path("sections/<int:pk>/syllabus/", SyllabusEditorView.as_view(), name="syllabus_edit"),
    path("teaching/", MyTeachingView.as_view(), name="teaching"),
]
