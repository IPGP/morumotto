# -*- coding: utf-8 -*-
import time
import subprocess
import logging
import multiprocessing
from datetime import datetime, timedelta
from celery import shared_task
from celery_progress.backend import ProgressRecorder
from celery.decorators import periodic_task
# from django_celery_beat.models import PeriodicTask, IntervalSchedule
# from celery_progress.backend import ProgressRecorder
from seismicarchive import stack, stats, updatearchive
from seismicarchive.models import NSLC, Network, Station, Location, Channel, \
    Configuration
from monitoring import update_monitoring
from monitoring.models import ArchiveMonitoring

logger = logging.getLogger('Status')


# In this file we implement the functions that requires an asynchronous execution
@shared_task(bind=True,ignore_result=True)
def update_statistics(self, monitoring_config_id):
    progress_recorder = ProgressRecorder(self)

    monitoring_config = ArchiveMonitoring.objects.get(pk=monitoring_config_id)
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
        archive, nslc_qs, data_format, data_structure,
        progress_recorder=progress_recorder)
    # update_monitoring.get_daily_stats(progress_recorder)
    update_monitoring.average_stats(monitoring_config,
                                    progress_recorder=progress_recorder)
    return 'All statistics are up-to-date'

@shared_task(bind=True)
def update_archive(self):
    progress_recorder = ProgressRecorder(self)
    running = updatearchive.update(progress_recorder)
    return 'Archive updated'


@shared_task(bind=True)
def execute_stack(self, config_id):
    progress_recorder = ProgressRecorder(self)
    config = Configuration.objects.get(pk=config_id)
    running = stack.execute_stack(config,progress_recorder)
    return 'All requests have been processed'


def get_celery_worker_status():
    # this function is just used to check whether celery is launched.
    # it only works with RabbitMQ, not Redis
    ERROR_KEY = "ERROR"
    try:
        from celery.task.control import inspect
        insp = inspect()

        # p = multiprocessing.Process(target=insp.stats())
        # d = p.start()
        #
        # # Wait for 10 seconds or until process finishes
        # p.join(10)
        # print(p)
        # If thread is still active
        # if p.is_alive():
        #     print "running... let's kill it..."
        #
        #     # Terminate
        #     p.terminate()
        #     p.join()


        d = insp.stats() #old method
        if not d:
            d = { ERROR_KEY: 'Celery not running.' }
    except IOError as e:
        from errno import errorcode
        msg = "Error connecting to the backend: " + str(e)
        if len(e.args) > 0 and errorcode.get(e.args[0]) == 'ECONNREFUSED':
            msg += ' Check that the RabbitMQ server is running.'
        d = { ERROR_KEY: msg }
    except ImportError as e:
        d = { ERROR_KEY: str(e)}
    return d


def launch_celery():
    result = subprocess.run(['celery -A siqaco worker -l info'],
                            stdout=subprocess.PIPE, shell=True)


def launch_periodic_celery():
    result = subprocess.run(['celery -A siqaco beat -l info -S django'],
                            # OR: ['celery -A siqaco beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler'],
                            stdout=subprocess.PIPE, shell=True)


def kill_celery():
    result = subprocess.run(['pkill -f "celery worker"'],
                            stdout=subprocess.PIPE, shell=True)


# @shared_task(bind=True)
# def add_stations_to_db(self):
#     progress_recorder = ProgressRecorder(self)
#     # là on va lancer le script fdsn pour rajouter les paths et les stations automatiquement
#     return "Stations added to DB successfully"
