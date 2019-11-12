# -*- coding: utf-8 -*-
import sys
import inspect
import importlib
import logging
from django.core.management.base import BaseCommand, CommandError
from logdb.models import StatusLog, MonitoringLog, UpdateLog, QCLog, \
    StatsLog, StackLog

logger = logging.getLogger('Status')

class Command(BaseCommand):
    """
    This class defines the clean_log command to clean all the logs from database

    It will remove all StatusLog, MonitoringLog, UpdateLog, QCLog, StatsLog,
    StackLog from logs.

    It will also clear the WORKING_DIR directory
    """
    help = ('Clean database from all StatusLog, MonitoringLog, UpdateLog, '
           'QCLog, StatsLog, StackLog')

    def add_arguments(self, parser):
        parser.add_argument('-i', '--ignore', nargs='+', type=str,
                            help='Logs you want to keep')


    def handle(self, *args, **options):
        ignore = options['ignore']
        log_class = [cls[0] for cls in
                     inspect.getmembers(sys.modules["logdb.models"],
                                        inspect.isclass)
                     if cls[1].__module__==sys.modules["logdb.models"].__name__]

        log_messages = list()
        for log in log_class:
            module = importlib.import_module("logdb.models")
            cls_ = getattr(module, log)
            if not ignore:
                cls_.objects.all().delete()
            elif cls_.__name__ not in ignore:
                cls_.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Successfully removed all logs'))
