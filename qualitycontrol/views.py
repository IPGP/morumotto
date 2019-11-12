# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.template import loader
from siqaco import toolbox
from plugins import structure, format
from .forms import GetMetadataForm, MetadataFolderForm, MetadataWSForm,\
    MetadataSVNForm, NSLCForm, NSLCUniqueForm
from .models import Metadata, LastUpdate, QCConfig
from .qc import metadata_from_dir, metadata_from_webservice, \
    metadata_from_svn
from plugins.metadata_format import DatalessSEED
from plugins.format import miniSEED
from siqaco import cronjobs



BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLOT_DIR =  os.path.join(BASE_DIR, "WORKING_DIR", "PLOT/")

logger = logging.getLogger('Status')

def qc_menu(request):
    return render(request, 'qualitycontrol/qc_menu.html')


def status(request):
    if LastUpdate.objects.count() == 0:
        last_update = "Never"
    else:
        last_update = LastUpdate.objects.first()

    if(request.POST.get("stop_cron")):
        cronjobs.stop_cronjobs()

    if(request.POST.get("start_cron")):
        try:
            cronjobs.start_cronjobs()
        except:
            logger.exception("Print can't restart cronjobs")

    context = {"last_update" : last_update }
    context["crontab_status"] = cronjobs.get_mdata_cronjob_status()
    return render(request, 'qualitycontrol/status.html', context)


@login_required
def update_metadata(request):
    if QCConfig.objects.count() == 0:
        logger.error("no QC configuration")
        return HttpResponseRedirect('/home/init_qcconfig')
    config = QCConfig.objects.first()
    if LastUpdate.objects.count() == 0:
        last_update = LastUpdate()
        last_update.save()
    else:
        last_update = LastUpdate.objects.first()

    if request.POST.get("folder_update"):
        dir_form = MetadataFolderForm(request.POST)
        if dir_form.is_valid():
            dirname = dir_form.cleaned_data.get('dir')
            metadata_from_dir(config, dirname)
            last_update.update_method = "local_dir"
            last_update.options = dirname
            last_update.time = datetime.now()
            last_update.save()
            cronjobs.get_mdata_create_cronjob()
    else:
        dir_form = MetadataFolderForm()
    if request.POST.get("ws_update"):
        ws_form = MetadataWSForm(request.POST)
        if ws_form.is_valid():
            client = ws_form.cleaned_data.get('client')
            metadata_from_webservice(config,client)
            last_update.update_method = "web_service"
            last_update.options = client
            last_update.time = datetime.now()
            last_update.save()
            cronjobs.get_mdata_create_cronjob()
    else:
        ws_form = MetadataWSForm()
    if request.POST.get("svn_update"):
        svn_form = MetadataSVNForm(request.POST)
        if svn_form.is_valid():
            svn_address, username, password  = svn_form.cleaned_data.get('svn_address','username', 'password')
            # username = svn_form.cleaned_data.get('username')
            # password = svn_form.cleaned_data.get('password')
            metadata_from_svn(config, svn_address, username, password)
            last_update.update_method = "svn"
            last_update.options = "%s,%s,%s" %(svn_address, username, password)
            last_update.time = datetime.now()
            last_update.save()
            cronjobs.get_mdata_create_cronjob()
    else:
        svn_form = MetadataSVNForm()

    # last_update.time = datetime.now()
    # last_update.save()
    context = {"dir_form" : dir_form }
    context["ws_form"] = ws_form
    context["svn_form"] = svn_form
    return render(request, 'qualitycontrol/update_metadata.html', context)


def check_metadata(request):
    metadata = Metadata.objects.none()
    if request.POST.get("check_metadata"):
        form = NSLCForm(request.POST)
        if form.is_valid():
            metadata = form.cleaned_data.get('nslc_list')
            # Metadata check HERE
    else:
        form = NSLCForm()
    context = { "form" : form }
    context["metadata_report"] = metadata
    return render(request, 'qualitycontrol/check_metadata.html', context)


def map_stations(request):
    metadata = Metadata.objects.none()
    if request.POST.get("display_stations"):
        form = NSLCForm(request.POST)
        if form.is_valid():
            metadata = form.cleaned_data.get('nslc_list')
    else:
        form = NSLCForm()
    context = { "form" : form }
    context["metadata"] = metadata
    context["online"] = toolbox.is_online()
    return render(request, 'qualitycontrol/map_stations.html', context)


def plot_response(request):
    extension = "svg"
    figure = False
    filename = None
    metadata = Metadata.objects.none()
    dataless = DatalessSEED()
    if request.POST.get("plot_resp"):
        form = NSLCUniqueForm(request.POST)
        if form.is_valid():
            metadata = form.cleaned_data.get('nslc')
            filename = metadata.nslc.code
            output = PLOT_DIR + filename + ".resp." + extension
            figure = dataless.resp_plot(metadata,output)
    else:
        form = NSLCUniqueForm()
    context = { "form" : form }
    context["metadata"] = metadata
    context["figure"] = figure
    context["extension"] = extension
    context["filename_id"] = filename
    context["plotdir"] = os.path.join("WORKING_DIR/", "PLOT/")
    return render(request, 'qualitycontrol/plot_response.html', context)

def metadata_vs_data(request):
    metadata = Metadata.objects.none()
    if request.POST.get("check_metadata_vs_data"):
        form = NSLCForm(request.POST)
        if form.is_valid():
            metadata = form.cleaned_data.get('nslc_list')
            # metadata vs data check here
    else:
        form = NSLCForm()
    context = { "form" : form }
    context["metadata_vs_data_report"] = metadata
    return render(request, 'qualitycontrol/metadata_vs_data.html', context)

def check_data(request):
    metadata = Metadata.objects.none()
    if request.POST.get("check_data"):
        form = NSLCForm(request.POST)
        if form.is_valid():
            metadata = form.cleaned_data.get('nslc_list')
            # Check data here
    else:
        form = NSLCForm()
    context = { "form" : form }
    context["data_report"] = metadata
    return render(request, 'qualitycontrol/check_data.html', context)

def plot_completion(request):
    extension = "svg"
    figure = False
    filename = None
    metadata = Metadata.objects.none()
    seed = miniSEED()

    if request.POST.get("plot_complt"):
        form = NSLCUniqueForm(request.POST)
        if form.is_valid():
            metadata = form.cleaned_data.get('nslc')
            filename = metadata.nslc.code
            output = PLOT_DIR + filename + ".complt." + extension
            figure = seed.completion(metadata,output) # Not implemented yet
    else:
        form = NSLCUniqueForm()
    context = { "form" : form }
    context["metadata"] = metadata
    context["figure"] = figure
    context["extension"] = extension
    context["filename_id"] = filename
    context["plotdir"] = os.path.join("WORKING_DIR/", "PLOT/")
    return render(request, 'qualitycontrol/plot_completion.html', context)
