# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from celery.task.control import inspect
from celery import chain, chord, group
from .forms import NewRequestForm, SourceForm, WindowForm
from .models import Request, Configuration, Gap, Source
from .update import update_source_infos
from morumotto import tasks, cronjobs
from monitoring import update_monitoring
from . import update, stats, stack


logger = logging.getLogger('Status')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR")

class FakeProgress():
    def set_progress(self, start, end):
        return
fake_progress = FakeProgress()

@login_required
def update_view(request):
    if Configuration.objects.count() == 0:
        configuration = Configuration()
        configuration.save()
    config = Configuration.objects.first()

    # view where user can update DB from a selected config and Setup
    celery_status = tasks.get_celery_worker_status()
    context = {'task_id': 0}
    context['celery_status'] = celery_status
    context['config_id'] = config.id


    window_form = WindowForm(instance=config)

    if(request.POST.get('celery_update_archive')):
        window_form = WindowForm(request.POST)
        if window_form.is_valid():
            config.f_analysis = window_form.cleaned_data["f_analysis"]
            config.w_analysis = window_form.cleaned_data["w_analysis"]
            config.l_analysis = window_form.cleaned_data["l_analysis"]
            config.granularity_type = window_form.cleaned_data["granularity_type"]
            config.save()

        context["display_archive"] = True
        result = tasks.update_archive.delay()
        context['task_id'] = result.task_id


    if(request.POST.get('exec_stack')):
        context["display_stack"] = True
        requests = Request.objects.filter(status__in=["new", "retry"])
        jobs = tasks.execute_stack.delay(config.id)
        # if config.n_request == 1 :
        #     # For 1 task processing all requests :
        #     jobs = tasks.execute_stack.delay(config.id)
        # else:
        #     # For multitasking, display progress bar will not work
        #     jobs = tasks.execute_requests.delay(config_id=config.id)
        context['task_id_stack'] = jobs.task_id

    if(request.POST.get("restart_cronjobs")):
        cronjobs.stop_cronjobs()
        cronjobs.start_cronjobs()
    context["window_form"] = window_form
    return render(request, 'archive/index.update.html', context)


@login_required
def newrequest(request):
    # View to create requests
    if Configuration.objects.count() == 0:
        logger.error("no configuration")
        return HttpResponseRedirect('/home/init_networks')
    config = Configuration.objects.first()
    qs = config.nslc.all()
    # source_qs = config.source.all()
    new_request = NewRequestForm()
    source_form = SourceForm()
    if(request.POST.get('addRequest')):
        # This is the form to configure the Monitoring model,
        # except for the components field
        new_request = NewRequestForm(request.POST)
        source_form = SourceForm(request.POST)
        if new_request.is_valid():
            nslc_list = new_request.cleaned_data["nslc_list"]
            starttime = new_request.cleaned_data["starttime"]
            endtime = new_request.cleaned_data["endtime"]
            force_source = new_request.cleaned_data["force_source"]
            if source_form.is_valid():
                source_list = source_form.cleaned_data["source_list"]
                if not source_list.count():
                    source_list = None
            workspace = WORKING_DIR
            if source_list:
                update = update_source_infos(
                         nslc_list, source_list,
                         starttime, endtime,
                         workspace)
            else:
                update = update_source_infos(
                         nslc_list, config.sources.all(),
                         starttime, endtime,
                         workspace)

            if force_source:
                gap_id = list()
                # If we want to force data from selected sources :
                for nslc in nslc_list:

                    Gap.objects.filter(archive=config.archive,
                                       starttime=starttime,
                                       endtime=endtime,
                                       status__in=["in_process","archived","retry"],
                                       nslc=nslc).delete()
                    gap, created = Gap.objects.get_or_create(
                                 nslc=nslc, archive=config.archive,
                                 starttime=starttime, endtime=endtime, status="new")
                    file_list = stats.get_datafiles(nslc,starttime,endtime)
                    for file in file_list:
                        gap.files.add(file)
                    gap.save()
                    gap_id.append(gap.id)
                # gap_list = Gap.objects.filter(
                #          nslc__in=nslc_list, archive=config.archive,
                #          starttime=starttime, endtime=endtime)
                gap_list = Gap.objects.filter(pk__in=gap_id)
                stack.create_requests(config, gap_list, source_list)
            else:
                # If we want to fill gaps in final archive :
                archive = config.archive
                max_gaps = config.max_gaps_by_analysis
                data_format = config.get_data_format()
                data_structure = config.get_data_structure()

                gap_list, overlap_list = stats.get_gapsoverlaps(
                                         archive, nslc_list,
                                         data_format, data_structure, max_gaps,
                                         starttime, endtime)
                gap_qs = gap_list.filter(starttime__lte=endtime,
                                         endtime__gte=starttime,
                                         status__in=["new"],
                                         archive=archive,
                                         nslc__in=nslc_list)
                stack.create_requests(config, gap_qs)
        # else:
            # Uncomment to have a blank request when reload page :
            # new_request = NewRequestForm()
            # source_form = SourceForm()

    new_request.fields["nslc_list"].queryset = qs
    context = {"request_form": new_request}
    context["source_form"] = source_form
    return render(request, 'archive/index.newrequest.html', context)


def stack_view(request):
    # view which shows the stack state
    # first : just view of what's going on
    # second : allows user to generate custom request, modify request, delete request etc.
    request_stack = Request.objects.all()
    if(request.POST.get('request_to_delete')):
        requests_to_delete = request.POST.getlist('request_to_delete')
        for id in requests_to_delete:
            try:
                Request.objects.get(pk=id).delete()
            except:
                logger.exception("Can't delete request n°%s" %id)

    return render(request, 'archive/index.stack_view.html', {"request_stack": request_stack})
