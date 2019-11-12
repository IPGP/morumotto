# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from seismicarchive.models import Configuration
from seismicarchive import updatearchive
import logging

logger = logging.getLogger('Status')

class Command(BaseCommand):
    """
    This class defines the update command for django manager. You can now call
    python manage.py window_update --window_starttime 2019-05-23T00:00:00Z
    --window_endtime 2019-05-24T00:00:00Z

    --window_starttime and --window_endtime are optional. If not set, we use
    the ones in configuration
    """
    help = 'Update data according to the time window defined in config'

    def add_arguments(self, parser):
        parser.add_argument('-s', '--window_starttime', type=str,
                            help='Window starttime,'
                            'format must be like "1977-04-22T06:00:00Z"', )
        parser.add_argument('-e', '--window_endtime', type=str,
                            help='Window endtime,'
                            'format must be like "1977-04-22T06:00:00Z"', )

    def handle(self, *args, **options):
        if not Configuration.objects.all().count():
            raise CommandError("No Configuration found, please initialize "
                               "software first")

        window_starttime = options['window_starttime']
        window_endtime = options['window_endtime']

        if window_starttime and window_endtime:
            try:
                starttime = datetime.strptime(window_starttime, "%Y-%m-%dT%H:%M:%SZ")
                endtime = datetime.strptime(window_endtime, "%Y-%m-%dT%H:%M:%SZ")
            except:
                raise CommandError("Wrong format for window starttime or endtime."
                             "Must be YYYY-mm-ddTHH:MM:SSZ")
        else:
            starttime = None
            endtime = None

        updatearchive.update(starttime=starttime,endtime=endtime)

        self.stdout.write(self.style.SUCCESS('Successfully updated archive'))
