from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Course
from .serializers import CourseSerializer


class CourseViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows courses to be viewed or edited.
    """
    queryset = Course.objects.all().order_by('-created')
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
