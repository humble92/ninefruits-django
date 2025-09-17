from rest_framework import serializers

from .models import Course


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name', 'code', 'division', 'opening_semester', 'subject', 'department']
