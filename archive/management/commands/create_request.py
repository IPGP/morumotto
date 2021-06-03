# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from archive.models import Configuration, Source, Gap, NSLC, \
    Network, Station, Location, Channel
from archive import update, stack, stats
from datetime import *
import logging
import os

logger = logging.getLogger('Status')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR")


class Command(BaseCommand):
    """
    This class defines the create_request command for django manager

    You can now call
    python manage.py create_request --starttime 2019-05-23T00:00:00Z
    --endtime 2019-05-24T00:00:00Z

    --starttime and --endtime are optional. If not set, we use
    the ones in configuration
    """
    help = 'Update data according to the time window defined in config'

    def add_arguments(self, parser):
        parser.add_argument('--starttime', type=str,
                            help='Starttime,'
                            'format must be like "1977-04-22T06:00:00Z"', )
        parser.add_argument('--endtime', type=str,
                            help='Endtime,'
                            'format must be like "1977-04-22T06:00:00Z"', )
        parser.add_argument('--nslc_list', nargs='+', type=str,
                            help='NSLC you want to update')
        parser.add_argument('--source_list', nargs='+', type=str,
                            help='Sources you want to use')

    def handle(self, *args, **options):
        try:
            config = Configuration.objects.first()
        except:
            raise CommandError("No Configuration found, please initialize "
                               "software first")

        source_list = Source.objects.filter(name__in=options["source_list"])
        nslc_codes_toget = options["nslc_list"]
        # HANDLE WILDCARDS :
        for nslc in nslc_codes_toget:
            nslc_codes = list()
            n,s,l,c = nslc.split('.')

            if n=="*":
                net_list = Network.objects.all()
            elif "?" in n:
                net_list = Network.objects.filter(
                         name__contains=n.replace("?",""))
            else:
                net_list = Network.objects.filter(name=n)

            if s=="*":
                sta_list = Station.objects.filter(network__in=net_list)
            elif "?" in s:
                sta_list = Station.objects.filter(network__in=net_list,
                         name__contains=s.replace("?",""))
            else:
                sta_list = Station.objects.filter(network__in=net_list,
                         name=s)

            if l=="*":
                loc_list = Location.objects.filter()
            elif "?" in l:
                loc_list = Location.objects.filter(name__contains=l.replace("?",""))
            else:
                loc_list = Location.objects.filter(name=l)

            if c=="*":
                chan_list = Channel.objects.filter()
            elif "?" in c:
                chan_list = Channel.objects.filter(name__contains=c.replace("?",""))
            else:
                chan_list = Channel.objects.filter(name=c)


            nslc_codes_toget.remove(nslc)
            nslc_codes.extend([nslc.code for nslc in NSLC.objects.filter(
                                 net__in=net_list,
                                 sta__in=sta_list,
                                 loc__in=loc_list,
                                 chan__in=chan_list)])

        nslc_list = NSLC.objects.filter(code__in=nslc_codes)
        try:
            starttime = datetime.strptime(options['starttime'],
                                          "%Y-%m-%dT%H:%M:%SZ")
            endtime = datetime.strptime(options['endtime'],
                                          "%Y-%m-%dT%H:%M:%SZ")
        except:
            raise CommandError("Wrong format for window starttime or endtime."
                         "Must be YYYY-mm-ddTHH:MM:SSZ")


        if not source_list.count():
            source_list = None
        workspace = WORKING_DIR
        update.update_source_infos(
                 nslc_list, source_list,
                 starttime, endtime,
                 workspace)

        gap_id = list()
        for nslc in nslc_list:
            gap, created = Gap.objects.get_or_create(
                         nslc=nslc, archive=config.archive,
                         starttime=starttime, endtime=endtime)
            file_list = stats.get_datafiles(nslc,starttime,endtime)
            for file in file_list:
                gap.files.add(file)
            gap.save()
            gap_id.append(gap.id)
        gap_list = Gap.objects.filter(pk__in=gap_id)
        stack.create_requests(config, gap_list, source_list)

        self.stdout.write(self.style.SUCCESS('Successfully created requests'))
