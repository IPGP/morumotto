# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from archive.models import Configuration, Request
from archive import stack
from morumotto import tasks
import logging
from sys import exit
from signal import signal, SIGINT
from functools import partial
from time import sleep
from datetime import datetime

logger = logging.getLogger('Status')



# in case of CTRL-C, doesn't work really well...
def signal_handler(request, config, signal, frame):
    print("User interruption of execution...")
    logger.exception("Failed request %s on %s"
                     %(request.pk, datetime.now()))
    request.status = "failed"
    request.save()
    request.gap.status = "in_process"
    request.gap.save()
    if config.request_lifespan_type == "n":
        request.timeout += 1
        if request.timeout == config.request_lifespan:
            request.status = ("on_hold, number of retry exceeded")
        else:
            request.status = "retry"
    elif config.request_lifespan_type == "p":
        remaining = (datetime.now() -request.timeout).total_seconds()
        if remaining == 0:
            request.status = ("on_hold, request lifespan timed out")
        else:
            request.status = "retry"
    request.save()
    raise CommandError("Execution interrupted by user, current "
                       "request (id = %s) status has been set to 'failed' "
                       %request.pk)


class Command(BaseCommand):
    """
    This class defines the exec_stack command for django manager.

    You can now call
    python manage.py exec_stack

    It will execute all 'new' or 'in_process' requests in stack
    """

    help = 'Update data according to the time window defined in config'



    def handle(self, *args, **options):
        try:
            config = Configuration.objects.first()
        except:
            raise CommandError("No Configuration found, please initialize "
                               "software first")
        celery_status = tasks.get_celery_worker_status()
        if 'ERROR' in celery_status:
            raise CommandError("Error in celery %s "
                               "\n Restart your celery daemon : "
                               "sudo supervisorctl restart "
                               "morumotto:morumotto_celery" %celery_status)
        else:
            jobs = tasks.execute_stack.delay(config.id)
            # HANDLE MULTITASKING : use lines 73 to 79 instead of 71
            # if config.n_request == 1 :
            #     # For 1 task processing all requests :
            #     jobs = tasks.execute_stack.delay(config.id)
            # else:
            #     # For multitasking, display progress bar will not work
            #     jobs = tasks.execute_requests.delay(config_id=config.id)
            self.stdout.write(self.style.SUCCESS('Stack execution done'))
