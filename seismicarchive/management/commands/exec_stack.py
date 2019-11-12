# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from seismicarchive.models import Configuration
from seismicarchive import stack
import logging

logger = logging.getLogger('Status')

class Command(BaseCommand):
    """
    This class defines the exec_stack command for django manager.

    You can now call
    python manage.py exec_stack

    It will execute all 'new' or 'in_process' requests in stack
    """

    help = 'Update data according to the time window defined in config'

    def handle(self, *args, **options):
        try:
            config = Configuration.objects.first()
        except:
            raise CommandError("No Configuration found, please initialize "
                               "software first")

        stack.execute_stack(config)
        self.stdout.write(self.style.SUCCESS('Successfully executed stack'))
