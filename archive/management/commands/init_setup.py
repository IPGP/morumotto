# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from archive.models import Configuration
from qualitycontrol.models import QCConfig
from monitoring.models import ArchiveMonitoring
import logging

logger = logging.getLogger('Status')

class Command(BaseCommand):
    """
    This class defines the inist_setup command

    It will create the configuration objects for the update (Configuration),
    Quality Control (QCConfig) and Monitoring (ArchiveMonitoring), and also
    instanciate NSLC given after the --nslc_file flag, and sources given after
    the --source_xml_file flag

    It will also clear the WORKING_DIR directory
    """
    help = ('Clean database from all Gaps, Overlaps, Source Availability, '
           'Availability & Online Stats, Requests, Postfiles & Datafiles')

    def add_arguments(self, parser):
        parser.add_argument('config_file', type=str,
                            help='path to the xml file containing your setup')
        parser.add_argument('--nslc_file', type=str,
                            help='path to the file containing all your nslc')
        parser.add_argument('--source_file', type=str,
                            help='path to the xml file containing all your'
                                 'sources')

    def handle(self, *args, **options):
        config_file = options['config_file']
        nslc_file = options['nslc_file']
        source_file = options['source_file']

        # 1) Read config file, parse xml to database

        # 2) Read source_file and parse it to database

        # 3) Read nslc file and pase it to database

        # self.stdout.write(self.style.SUCCESS('Initialisation of software done'))


        self.stdout.write(self.style.ERROR('Not available yet'))
