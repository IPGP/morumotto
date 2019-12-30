# -*- coding: utf-8 -*-
import time
import subprocess
import logging
import multiprocessing
from datetime import datetime, timedelta
from itertools import zip_longest
from celery import shared_task, task, group, chain
from celery_progress.backend import ProgressRecorder
from celery.decorators import periodic_task
# from django_celery_beat.models import PeriodicTask, IntervalSchedule
# from celery_progress.backend import ProgressRecorder
from archive import stack, stats, update
from archive.models import NSLC, Network, Station, Location, Channel, \
    Configuration, Request
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
    running = update.update(progress_recorder)
    return 'Archive updated'


@shared_task(bind=True)
def execute_stack(self,config_id):
    try:
        progress_recorder = ProgressRecorder(self)
        config = Configuration.objects.get(pk=config_id)
        loop_count=0
        requests = Request.objects.filter(status__in=["new", "retry"])
        for request in requests:
            result = stack.execute_request(request, config)
            loop_count += 1
            progress_recorder.set_progress(loop_count, len(requests))
        return 'All requests have been processed'
    # try:
    #     config = Configuration.objects.get(pk=config_id)
    #     requests_list = [req.pk for req in Request.objects.filter(status__in=["new", "retry"])]
    #     i = 0
    #     print("hello")
    #     job = execute_requests.delay([],config.id,0,0)
    #     for i in range(0,len(requests_list)/config.n_requests,config.n_requests):
    #         job = group(execute_requests.s(requests_list[i:i+config.n_requests], config.id, i, n_requests))
    #         job.apply_async()
    #     return job
    except:
        logger.exception("Error in celery task")


@shared_task(bind=True)
def execute_request(self, request_id, config_id=None):
    request = Request.objects.get(pk=request_id)
    config = Configuration.objects.get(pk=config_id)
    result = stack.execute_request(request, config)
    return 'Request %s processed, exit status %s' %(request.pk, request.status)


@shared_task(bind=True)
def execute_requests(self,config_id=None):
    progress_recorder = ProgressRecorder(self)

    config = Configuration.objects.get(pk=config_id)
    n_parallel = config.n_request
    requests = Request.objects.filter(status__in=["new", "retry"])
    request_list = [ ( req.id, config_id ) for req in requests ]

    result = group(execute_request.chunks( request_list, n_parallel )).delay()
    progress_recorder.set_progress( len(request_list), len(request_list) )
    return "All requests processed !"


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
    result = subprocess.run(['celery -A morumotto worker -l info'],
                            stdout=subprocess.PIPE, shell=True)


def launch_periodic_celery():
    result = subprocess.run(['celery -A morumotto beat -l info -S django'],
                            # OR: ['celery -A morumotto beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler'],
                            stdout=subprocess.PIPE, shell=True)


def kill_celery():
    result = subprocess.run(['pkill -f "celery worker"'],
                            stdout=subprocess.PIPE, shell=True)


# @shared_task(bind=True)
# def add_stations_to_db(self):
#     progress_recorder = ProgressRecorder(self)
#     # là on va lancer le script fdsn pour rajouter les paths et les stations automatiquement
#     return "Stations added to DB successfully"
