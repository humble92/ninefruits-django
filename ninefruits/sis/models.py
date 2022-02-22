from django.db import models
from django_extensions.db.models import TimeStampedModel

from user.models import TotalStudent


class Faculty(TimeStampedModel):
    name = models.CharField(blank=False, null=False, max_length=100)

    class Meta:
        verbose_name_plural = 'faculties'

    def __str__(self):
        return self.name


class Department(TimeStampedModel):
    name = models.CharField(blank=False, null=False, max_length=100)
    faculty = models.ForeignKey(
        'Faculty', null=True, on_delete=models.SET_NULL, related_name="departments"
    )

    def __str__(self):
        return self.name


class BaseSubject(TimeStampedModel):
    base_name = models.CharField(blank=False, null=False, max_length=100)
    base_code = models.CharField(blank=False, null=False, unique=True, max_length=10)

    def __str__(self):
        return self.base_name


class Course(TimeStampedModel):
    code = models.CharField(blank=False, null=False, max_length=10)
    division = models.CharField(blank=False, null=False, default='01', max_length=2)
    opening_semester = models.CharField(blank=False, null=False, max_length=6)
    subject = models.ForeignKey(
        'BaseSubject', null=False, on_delete=models.CASCADE, related_name="courses"
    )
    name = models.CharField(blank=True, null=True, max_length=100)
    department = models.ForeignKey(
        'Department', blank=True, null=True, on_delete=models.SET_NULL, related_name="courses"
    )
    students = models.ManyToManyField(TotalStudent, blank=True)

    def __str__(self):
        return self.name if self.name else self.subject.base_name

    class Meta:
        unique_together = ('code', 'division', 'opening_semester',)
