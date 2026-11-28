from celery import shared_task
from django.core.management import call_command

from ninefruits.core.tasks import SystemTask, single_instance
from ninefruits.person.actions.year_levels import ManageYearLevels


@shared_task(name="person.apply_year_levels", base=SystemTask)
@single_instance("person.apply_year_levels")
def apply_year_levels() -> None:
    if ManageYearLevels().due().exists():
        call_command("students_apply_year_levels", verbosity=0)
