# -*- coding: utf-8 -*-
import os
import logging
from obspy.clients.fdsn import Client
from datetime import datetime
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template import loader
from morumotto import toolbox, cronjobs
from plugins import structure, format
from .forms import GetMetadataForm, MetadataFolderForm, MetadataWSForm,\
    MetadataSVNForm, MetadataForm, MetadataUniqueForm, MetadataDatesForm,\
    NSLCYearForm, MetadataYearForm
from .models import Metadata, LastUpdate, QCConfig
from archive.models import Configuration, NSLC
from .qc import md_from_dir, md_from_webservice, \
    md_from_svn, md_check
from plugins.metadata_format import DatalessSEED
from plugins.format import miniSEED


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
            md_from_dir(config, dirname)
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
            try:
                md_from_webservice(config,Client(client))
                last_update.update_method = "web_service"
                last_update.options = client
                last_update.time = datetime.now()
                last_update.save()
                cronjobs.get_mdata_create_cronjob()
            except ValueError as err:
                messages.error(request,"The FDSN service base URL `%s`"
                               " is not a valid URL" %client)
                logger.exception(err)
    else:
        ws_form = MetadataWSForm()
    if request.POST.get("svn_update"):
        svn_form = MetadataSVNForm(request.POST)
        if svn_form.is_valid():
            svn_address = svn_form.cleaned_data.get('svn_address')
            username = svn_form.cleaned_data.get('username')
            password = svn_form.cleaned_data.get('password')
            md_from_svn(config, svn_address, username, password)
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
    if QCConfig.objects.count() == 0:
        logger.error("no QC configuration")
        return HttpResponseRedirect('/home/init_qcconfig')
    config = QCConfig.objects.first()
    metadata = Metadata.objects.none()
    if request.POST.get("check_metadata"):
        form = MetadataDatesForm(request.POST)
        if form.is_valid():
            metadata_list = form.cleaned_data.get('metadata_list')
            starttime = form.cleaned_data.get('starttime')
            endtime = form.cleaned_data.get('endtime')
            md_check(config, metadata_list, starttime, endtime)
    else:
        form = MetadataDatesForm()
    context = { "form" : form }
    context["metadata_report"] = metadata
    return render(request, 'qualitycontrol/check_metadata.html', context)


def map_stations(request):
    metadata = Metadata.objects.none()
    if request.POST.get("display_stations"):
        form = MetadataForm(request.POST)
        if form.is_valid():
            metadata = form.cleaned_data.get('nslc_list')
    else:
        form = MetadataForm()
    context = { "form" : form }
    context["metadata"] = metadata
    context["online"] = toolbox.is_online()
    return render(request, 'qualitycontrol/map_stations.html', context)


def plot_response(request):
    if QCConfig.objects.count() == 0:
        logger.error("no QC configuration")
        return HttpResponseRedirect('/home/init_qcconfig')
    config = QCConfig.objects.first()
    extension = "svg"
    figure = False
    filename = None
    metadata = Metadata.objects.none()
    md_format = config.get_metadata_format()
    if request.POST.get("plot_resp"):
        form = MetadataUniqueForm(request.POST)
        if form.is_valid():
            metadata = form.cleaned_data.get('nslc')
            starttime = form.cleaned_data.get('starttime')
            filename = metadata.nslc.code
            output = PLOT_DIR + filename + ".resp." + extension
            figure = md_format.resp_plot(metadata,output)
    else:
        form = MetadataUniqueForm()
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
        form = MetadataDatesForm(request.POST)
        if form.is_valid():
            metadata_list = form.cleaned_data.get('metadata_list')
            starttime = form.cleaned_data.get('starttime')
            endtime = form.cleaned_data.get('endtime')
            # Check encoding (= config.compression_format)
            # Check blocking (= config.blocksize)
            # Check encoding is big endian in data & metadata
            # Check sample rate in data and metadata
    else:
        form = MetadataDatesForm()
    context = { "form" : form }
    context["metadata_vs_data_report"] = metadata
    return render(request, 'qualitycontrol/metadata_vs_data.html', context)

def check_data(request):
    metadata = Metadata.objects.none()
    if request.POST.get("check_data"):
        form = MetadataDatesForm(request.POST)
        if form.is_valid():
            metadata_list = form.cleaned_data.get('metadata_list')
            starttime = form.cleaned_data.get('starttime')
            endtime = form.cleaned_data.get('endtime')
            datafiles = DataFiles.objects.filter(nslc__in=metadata.nslc)
            print(datafiles)
            #  Check NET CODE
            #  Check data list
            #  Data before start of metadata ?
            #  Check Name = N.S.L.C in metadata
            #  Check Channels names

    else:
        form = MetadataDatesForm()
    context = { "form" : form }
    context["data_report"] = metadata
    return render(request, 'qualitycontrol/check_data.html', context)

def plot_completion(request):
    extension = "svg"
    figure = False
    filename = None

    if Configuration.objects.count() == 0:
        logger.error("no QC configuration")
        return HttpResponseRedirect('/home/init_qcconfig')
    config = Configuration.objects.first()
    archive = config.archive
    nslc = config.nslc.none()
    data_format = config.get_data_format()
    struct = config.struct_type
    if request.POST.get("plot_complt"):
        form = NSLCYearForm(request.POST)
        if form.is_valid():
            nslc = form.cleaned_data.get('nslc')
            year = str(form.cleaned_data.get('year')).split('-')[0]
            filename = nslc.code
            output = PLOT_DIR + filename + ".complt." + extension
            figure = data_format.plot_completion(nslc.code, year,
                                                 output,archive,struct)
    else:
        form = NSLCYearForm()
    context = { "form" : form }
    context["nslc"] = nslc
    context["figure"] = figure
    context["extension"] = extension
    context["filename_id"] = filename
    context["plotdir"] = os.path.join("WORKING_DIR/", "PLOT/")
    return render(request, 'qualitycontrol/plot_completion.html', context)
