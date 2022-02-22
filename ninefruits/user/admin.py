from django.contrib import admin

from user.models import Profile, Student, AbsentStudent, Applicant, Graduate, TotalStudent, Professor, Staff

# Register your models here.

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'id_no', 'profile_type')
    list_filter = ('sex', 'profile_type')
    search_fields = ['id_no', 'user__first_name', 'user__last_name']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    pass


@admin.register(AbsentStudent)
class AbsentStudentmentAdmin(admin.ModelAdmin):
    pass


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    pass


@admin.register(Graduate)
class GraduateAdmin(admin.ModelAdmin):
    pass


@admin.register(TotalStudent)
class TotalStudentAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    pass


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    pass
