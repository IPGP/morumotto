# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from monitoring.models import ArchiveMonitoring
from seismicarchive.models import NSLC, Network, Station, Location, Channel
from monitoring import update_monitoring
import logging

logger = logging.getLogger('Status')

class Command(BaseCommand):
    """
    This class defines the update_stats command for django manager.

    You can now call :
    python manage.py update_stats
    or
    python manage.py update_stats --config_id 1
    """
    help = 'Update statistics for monitoring'

    def add_arguments(self, parser):
        parser.add_argument('-c', '--config_id', type=int,
                            help='id for the monitoring configuration', )

    def handle(self, *args, **options):
        try:
            if options['config_id']:
                monitoring_config = ArchiveMonitoring.objects.get(
                                  pk=options['config_id'])
            else:
                monitoring_config = ArchiveMonitoring.objects.first()
        except:
            if options['config_id']:
                raise CommandError( "No Configuration found for id %s "
                                    % config_id )
            else:
                raise CommandError( "No Configuration found. Please initialize "
                                    "monitoring configuration first ")
        archive = monitoring_config.archive
        data_format = monitoring_config.get_data_format()
        data_structure = monitoring_config.get_data_structure()
        net_list = [n for n in monitoring_config.networks.all()]
        sta_list = [s for s in monitoring_config.stations.all()]
        comp_list = [c.name for c in monitoring_config.components.all()]
        chan_list = [c for c in Channel.objects.all() if
                     c.name[0:2] in comp_list]
        nslc_qs = NSLC.objects.filter(
                net__in=net_list,
                sta__in=sta_list,
                chan__in=chan_list)

        update_monitoring.get_stats_from_files(
            archive, nslc_qs, data_format, data_structure)
        # update_monitoring.get_daily_stats(progress_recorder)
        update_monitoring.average_stats(monitoring_config)

        self.stdout.write(self.style.SUCCESS('All statistics are up-to-date'))
