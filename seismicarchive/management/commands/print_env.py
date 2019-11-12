# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from seismicarchive.models import Configuration
from qualitycontrol.models import QCConfig
from monitoring.models import ArchiveMonitoring
import logging
import os
import sys

logger = logging.getLogger('Status')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
         os.path.dirname(os.path.abspath(__file__)))))
MANAGEMENT_PATH = os.path.join(BASE_DIR, "manage.py")
CRON_LOG = os.path.join(BASE_DIR, "WORKING_DIR", "LOG","cron.log")
PYTHON_PATH = sys.executable
ACTIVATE_PATH = os.path.join(os.path.dirname(PYTHON_PATH),"activate")


class Command(BaseCommand):
    """
    This class defines the print_env command

    It will show the variables executable path and other environment path.
    """
    help = ('Displays all environment variables used by this software')

    def handle(self, *args, **options):

        self.stdout.write(self.style.NOTICE('SIQACO ROOT DIR:') + BASE_DIR)
        self.stdout.write(self.style.NOTICE('PYTHON:') + PYTHON_PATH)
        self.stdout.write(self.style.NOTICE('MANAGE.PY:') + MANAGEMENT_PATH)
        self.stdout.write(self.style.NOTICE('CRONTAB LOG:') + CRON_LOG)
        self.stdout.write(self.style.NOTICE('DATASELECT:') + '/usr/local/bin/dataselect')
        self.stdout.write(self.style.NOTICE('MSI:') + '/usr/local/bin/msi')
        self.stdout.write(self.style.NOTICE('QMERGE:') + '/usr/local/bin/qmerge')
