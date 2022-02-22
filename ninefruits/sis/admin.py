from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Faculty, Department, BaseSubject, Course, CourseApplication


class CustomUserAdmin(UserAdmin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        UserAdmin.list_display = list(UserAdmin.list_display) + ['profile_type_name']
        UserAdmin.list_filter = list(UserAdmin.list_filter) + ['profile__profile_type']
        UserAdmin.search_fields = list(UserAdmin.search_fields) + ['profile__id_no']

    def profile_type_name(self, obj):
        profile_type_name = None
        if obj.profile:
            for i in range(len(obj.profile.PROFILE_TYPES)):
                if obj.profile.PROFILE_TYPES[i][0] == obj.profile.profile_type:
                    profile_type_name = obj.profile.PROFILE_TYPES[i][1]
        return profile_type_name

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    pass


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty')


@admin.register(BaseSubject)
class BaseSubjectAdmin(admin.ModelAdmin):
    list_display = ('base_code', 'base_name')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'code', 'division', 'department', 'opening_semester')
    list_filter = ('department', 'opening_semester')
    search_fields = ['name', 'subject__base_name', 'code']


@admin.register(CourseApplication)
class CourseApplicationAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'score', 'grade')
    list_filter = ('student', 'course')
    search_fields = ['course__code', 'course__name', 'course__subject__base_name', 'student__username', 'student__profile__id_no']
