# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import logging
from crontab import CronTab
from qualitycontrol.models import LastUpdate
from seismicarchive.models import Configuration

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANAGEMENT_PATH = os.path.join(BASE_DIR, "manage.py")
CRON_LOG = os.path.join(BASE_DIR, "WORKING_DIR", "LOG","cron.log")
PYTHON_PATH = sys.executable
ACTIVATE_PATH = os.path.join(os.path.dirname(PYTHON_PATH),"activate")
logger = logging.getLogger('Status')


def get_mdata_create_cronjob():
    """
    Removes older job to update metadata and creates new one
    """
    cron = CronTab(user=True)
    cron.remove_all(comment="get_mdata") # In case it already exists
    update_md = os.path.join(BASE_DIR,"siqaco",
                             "metadata_update.py")
    command = ("cd %s && %s manage.py shell < %s >> %s  2>&1"
               %(BASE_DIR, PYTHON_PATH, update_md, CRON_LOG))
    md_job = cron.new(command=command,comment='get_mdata')
    md_job.setall("0 0 * * *")
    cron.write()


def get_mdata_cronjob_status():
    """
    Checks the crontab, returns True if a cronjob is running for the update
    of metadata, else False
    """
    cron = CronTab(user=True)
    for job in cron:
        if job.comment =="get_mdata":
            return job.is_enabled()
    return False


def get_data_create_cronjob(config):
    """
    Removes older job to update metadata and creates new one
    """

    gran = config.granularity_type
    frq = config.f_analysis

    cron = CronTab(user=True)
    cron.remove_all(comment="window_update")
    update_data = os.path.join(BASE_DIR,"scheduler", "#window_update.py")
    command = ("cd %s && %s %s window_update >> %s  2>&1"
               %(BASE_DIR, PYTHON_PATH, MANAGEMENT_PATH, CRON_LOG))

    data_job = cron.new(command=command,comment='window_update')
    if gran == 'daily':
        data_job.setall("0 0 */%s * *" %(frq))
    else:
        # data_job.setall("* * * * *")
        data_job.setall("0 */%s * * *" %(frq))
    cron.write()
    logger.info("start cronjob for fetching data")


def get_data_cronjob_status():
    """
    Checks the crontab, returns True if a cronjob is running, else False
    """
    cron = CronTab(user=True)
    for job in cron:
        if job.comment == "window_update":
            return job.is_enabled()
    return False

def change_crontab(obj):
    pass



def start_cronjobs():
    logger.info("start crons")
    config = Configuration.objects.first()
    get_data_create_cronjob(config)
    get_mdata_create_cronjob()

def stop_cronjobs():
    logger.info("stop crons")
    cron = CronTab(user=True)
    for job in cron:
        if job.comment == "window_update":
            job.enable(False)
        elif job.comment == "get_mdata":
            job.enable(False)
    cron.write()
