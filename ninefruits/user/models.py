import logging

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.contrib.auth.models import User, UserManager

logger = logging.getLogger(__name__)


class Profile(models.Model):
    PROFILE_TYPES = [
        ('M', 'Administrator'),
        ('P', 'Professor'),
        ('F', 'Staff'),
        ('S', 'Student'),
        ('G', 'Graduate'),
        ('A', 'Applicant'),
        ('L', 'Student on a leave of absence'),
    ]

    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('N', 'Neutral'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    id_no = models.CharField(blank=True, null=True, max_length=16)
    profile_type = models.CharField(blank=True, null=True, max_length=1, choices=PROFILE_TYPES)
    sex = models.CharField(blank=True, null=True, max_length=1, choices=SEX_CHOICES)
    birth_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'user profile'
        verbose_name_plural = 'user profiles'

    def __str__(self):
        return self.user.username


# User Proxy: Student, Graduate, Applicant, AbsentStudent, Professor, Staff

class UserSaveMixin:
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            self.profile
        except ObjectDoesNotExist as e:
            self.create_user_profile()

        logger.debug(f"Profile type: {self.profile.profile_type} -> {self.PROFILE_TYPE}")
        self.profile.profile_type = self.PROFILE_TYPE
        self.profile.save()

    def create_user_profile(self):
        user_profile = apps.get_model('user', 'Profile')
        profile = user_profile()
        profile.user = self
        profile.save()


class CustomUserManager(UserManager):

    def get_queryset(self):
        return super().get_queryset().filter(
            profile__profile_type=self.model.PROFILE_TYPE)


class Student(UserSaveMixin, User):
    PROFILE_TYPE = 'S'
    objects = CustomUserManager()

    class Meta:
        proxy = True


class AbsentStudent(UserSaveMixin, User):
    PROFILE_TYPE = 'L'
    objects = CustomUserManager()

    class Meta:
        proxy = True


class Applicant(UserSaveMixin, User):
    PROFILE_TYPE = 'A'
    objects = CustomUserManager()

    class Meta:
        proxy = True


class Graduate(UserSaveMixin, User):
    PROFILE_TYPE = 'G'
    objects = CustomUserManager()

    class Meta:
        proxy = True


class TotalStudentManager(UserManager):

    def get_queryset(self):
        return super().get_queryset().filter(
            profile__profile_type__in=self.model.PROFILE_TYPES)


class TotalStudent(UserSaveMixin, User):
    PROFILE_TYPES = ['S', 'G', 'A', 'L']
    objects = TotalStudentManager()

    class Meta:
        proxy = True


class Professor(UserSaveMixin, User):
    PROFILE_TYPE = 'P'
    objects = CustomUserManager()

    class Meta:
        proxy = True
        ordering = ('first_name', )


class Staff(UserSaveMixin, User):
    PROFILE_TYPE = 'F'
    objects = CustomUserManager()

    class Meta:
        proxy = True
        ordering = ('first_name', )
        verbose_name_plural = 'staff'
