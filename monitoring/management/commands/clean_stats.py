# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from monitoring.models import Stat, AverageStat, AverageCompStat,\
    ChanPath, CompPath
from monitoring import update_monitoring
import logging

logger = logging.getLogger('Status')

class Command(BaseCommand):
    """
    This class defines the clean_stats command for django manager.

    You can now call :
    python manage.py clean_stats

    It will delete from database all Stat, AverageStat, AverageCompStat,
    ChanPath & CompPath
    """
    help = ('delete from database all Stat, AverageStat, AverageCompStat,'
            'ChanPath & CompPath')

    def add_arguments(self, parser):
        parser.add_argument('-i', '--ignore', nargs='+', type=str,
                            help='Objects you want to keep in the database')


    def handle(self, *args, **options):
        ignore = options['ignore']
        class_list = [Stat, AverageStat, AverageCompStat, ChanPath, CompPath]
        for cls_ in class_list:
            if not ignore:
                # print("cls_name", cls_.__name__)
                cls_.objects.all().delete()
            elif cls_.__name__ not in ignore:
                cls_.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Successfully cleaned statistics'))
