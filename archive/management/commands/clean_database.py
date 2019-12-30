# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from archive.models import Gap, GapList, Overlap, DataFile, \
    SourceAvailability, SourceAvailabilityStat, \
    SourceOnlineStat, Postfile, Request
import logging
import os

logger = logging.getLogger('Status')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR")

class Command(BaseCommand):
    """
    This class defines the clean_database command

    It will remove all Gaps, Overlaps, Source Availability, Availability &
    Online Stats, Requests, Postfiles & Datafiles.

    It will also clear the WORKING_DIR directory
    """
    help = ('Clean database from all Gaps, Overlaps, Source Availability, '
           'Availability & Online Stats, Requests, Postfiles & Datafiles')

    def add_arguments(self, parser):
        parser.add_argument('-i', '--ignore', nargs='+', type=str,
                            help='Objects you want to keep in the database')


    def handle(self, *args, **options):
        ignore = options['ignore']
        class_list = [Gap, GapList, Overlap, DataFile,
                      SourceAvailability, SourceAvailabilityStat,
                      SourceOnlineStat, Postfile, Request]
        for cls_ in class_list:
            if not ignore:
                # print("cls_name", cls_.__name__)
                cls_.objects.all().delete()
            elif cls_.__name__ not in ignore:
                cls_.objects.all().delete()
        try:
            if os.path.exists(WORKING_DIR):
                if len(os.listdir(WORKING_DIR) ) != 0:
                    shutil.rmtree(WORKING_DIR)
        except:
            raise CommandError("Can't remove WORKING DIR")
        self.stdout.write(self.style.SUCCESS('Successfully cleaned database'))
