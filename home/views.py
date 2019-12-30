# -*- coding: utf-8 -*-
import os
import logging
import importlib
import sys
import inspect
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from obspy.clients.fdsn import Client as fdsnClient
from .initialisation import nslc_from_webservice, nslc_from_stationxml
from .forms import ConfigurationForm, SourceForm, NetworkModelFormset, \
    WebServiceForm, ArchiveMonitoringInitForm, StationXMLForm, QCConfigInitForm
from archive.models import Configuration, Network, Station, Source, NSLC
from qualitycontrol.models import QCConfig
from monitoring.models import ArchiveMonitoring, Component
from morumotto import tasks, cronjobs
from plugins.choices import get_plugin_choices
import morumotto.toolbox as toolbox
# from django_celery_beat.models import PeriodicTask

logger = logging.getLogger('Status')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRON_LOG = os.path.join(BASE_DIR, "WORKING_DIR", "LOG","cron.log")

# def login(request):
#     # login view
#     user="jean"
#     context = {"user": user}
#     return render(request, 'home/login.html', context)
#
#
# def logout(request):
#     # logout view
#     pass


def go_to_home(request):
    # Redirects the root "/" page to home
    # See in morumotto/urls.py
    return HttpResponseRedirect("home")


def flower_redirect(request):
    flower_url = "http://127.0.0.1:5555"
    # CONTROL IF ACCESSIBLE ?
    return redirect(flower_url)


def about(request):
    return render(request, "home/about.html")

def documentation_redirect(request):
    return HttpResponseNotFound("Sorry, docs not available yet :'(")
    # return HttpResponseRedirect('https://readthedocs.org/projects/morumotto')


def index(request):
    if (Configuration.objects.count() == 0 and
        ArchiveMonitoring.objects.count() == 0):
        initialise = True
    else:
        if Configuration.objects.count():
            config = Configuration.objects.first()
            initialise = config.initialisation
        else:
            initialise = False


    if(request.POST.get("start_update")):
        if Configuration.objects.count() == 0:
            config = Configuration()
            config.save()
        cronjobs.get_data_create_cronjob(config)

    elif(request.POST.get("stop_update")):
        cronjobs.stop_cronjobs()


    context = {"initialise": initialise}
    # Crontab status :
    context["running"] = cronjobs.get_data_cronjob_status()
    # Last Cron message :
    if not toolbox.isempty(CRON_LOG):
        with open(CRON_LOG, "r") as cronfile:
            context["last_cron"] = cronfile.readlines()[-1]
            context["last_cron_date"] = datetime.fromtimestamp(
                                      os.path.getmtime(CRON_LOG))
    log_class = [cls[0] for cls in
                 inspect.getmembers(sys.modules["logdb.models"],
                                    inspect.isclass)
                 if cls[1].__module__ == sys.modules["logdb.models"].__name__]

    log_messages = list()
    for log in log_class:
        module = importlib.import_module("logdb.models")
        cls_ = getattr(module, log)
        if cls_.objects.all(): #filter(level=logging.INFO):
            # for message in cls_.objects.filter(
            #     level=logging.INFO).order_by("-id")[0:5]:
            for message in cls_.objects.all().order_by("-id")[0:5]:
                log_messages.append(message)

    context["log_messages"] = log_messages
    if initialise:
        return HttpResponseRedirect('init_welcome')
    else:
        return render(request, 'home/index.html', context)


@login_required
def init_welcome(request):

    context = {"initialise": True}
    context["modal"] = "welcome"

    if(request.POST.get("welcome_next")):
        return HttpResponseRedirect('init_nslc')
    if(request.POST.get("welcome_skip")):
        return HttpResponseRedirect('init_monitoring')

    return render(request, 'home/index.html', context)


@login_required
def init_nslc(request):
    if Configuration.objects.count() == 0:
        configuration = Configuration()
        configuration.save()
    config = Configuration.objects.first()

    context = {"initialise": True}
    context["modal"] = "nslc"
    context["ws_form"] = WebServiceForm()
    context["file_form"] = StationXMLForm()

    # Backend for the NSLC Initialisation modal
    if(request.POST.get("nslc_fdsn")):
        ws_form = WebServiceForm(request.POST)
        if ws_form.is_valid():
            client = ws_form.cleaned_data.get('name')
            custom_url = ws_form.cleaned_data.get('custom_url')
            network_str = ws_form.cleaned_data.get('networks')
            networks = list(network_str.split(","))
            for network in networks:
                net, created = Network.objects.get_or_create(name = network)
                if not config.networks.filter(pk=net.pk).exists():
                    logger.info("adding network %s to config" %net)
                    config.networks.add(net)
                    config.save()
            if custom_url:
                try:
                    nslc_from_webservice(fdsnClient(str(custom_url)), config)
                except:
                    logger.exception("Webservice not available")
            else:
                try:
                    nslc_from_webservice(fdsnClient(str(client)), config)
                except:
                    logger.exception("Webservice not available")


    elif(request.POST.get('nslc_file')):
        form = StationXMLForm(request.POST,request.FILES)
        if form.is_valid():
            print("form valid")
            filename = request.FILES['stationxmlfile']
            try:
                nslc_from_stationxml(filename,config)
            except lxml.etree.XMLSyntaxError:
                logger.exception("No data found for request")
            except:
                logger.exception("Wrong format for StationXML file")

    elif(request.POST.get("nslc_next")):
        if NSLC.objects.count() != 0:
            return HttpResponseRedirect("init_source")
        else:
            context["warning"] = True


    elif(request.POST.get("nslc_prev")):
        return HttpResponseRedirect("init_welcome")

    return render(request, 'home/index.html', context)


@login_required
def import_nslc(request):
    if Configuration.objects.count() == 0:
        configuration = Configuration()
        configuration.save()
    config = Configuration.objects.first()

    context = {"initialise": False}
    context["import"] = True
    context["ws_form"] = WebServiceForm()
    context["file_form"] = StationXMLForm()

    nslc_list = list()
    # Backend for the NSLC Initialisation modal
    if(request.POST.get("nslc_fdsn")):
        ws_form = WebServiceForm(request.POST)
        if ws_form.is_valid():
            client = ws_form.cleaned_data.get('name')
            custom_url = ws_form.cleaned_data.get('custom_url')
            network_str = ws_form.cleaned_data.get('networks')
            networks = list(network_str.split(","))
            for network in networks:
                net, created = Network.objects.get_or_create(name = network)
                if not config.networks.filter(pk=net.pk).exists():
                    logger.info("adding network %s to config" %net)
                    config.networks.add(net)
                    config.save()
            if custom_url:
                try:
                    nslc_list = nslc_from_webservice(
                              fdsnClient(str(custom_url)), config)
                    if nslc_list:
                        messages.success(request, 'NSLC import successfull !')
                    else:
                        messages.error(request, 'NSLC import failed !')
                except:
                    logger.exception("Webservice not available")
                    messages.error(request, 'NSLC import failed !')
            else:
                try:
                    nslc_list = nslc_from_webservice(
                              fdsnClient(str(client)), config)
                    if nslc_list:
                        messages.success(request, 'NSLC import successfull !')
                    else:
                        messages.error(request, 'NSLC import failed !')
                except:
                    logger.exception("Webservice not available")
                    messages.error(request, 'NSLC import failed !')


    elif(request.POST.get('nslc_file')):
        form = StationXMLForm(request.POST,request.FILES)
        if form.is_valid():
            print("form valid")
            filename = request.FILES['stationxmlfile']
            try:
                nslc_list = nslc_from_stationxml(filename,config)
                if nslc_list:
                    messages.success(request, 'NSLC import successfull !')
                else:
                    messages.error(request, 'NSLC import failed !')
            except:
                logger.exception("Wrong format for StationXML file")
                messages.error(request, 'NSLC import failed !')
    return render(request, 'home/index.html', context)



@login_required
def init_source(request):
    # Backend for the Source Initialisation modal
    if Configuration.objects.count() == 0:
        configuration = Configuration()
        configuration.save()
    config = Configuration.objects.first()
    configuration_form = ConfigurationForm(instance=config)
    source = Source.objects.first()

    context = {"initialise": True}
    context["modal"] = "source"

    if(request.POST.get('source_next')):
        source_form = SourceForm(request.POST, instance=source)
        if source_form.is_valid():
            new_source = source_form.save()
            config.sources.add(new_source)
            config.save()


            return HttpResponseRedirect("init_config")
    else:
        source_form = SourceForm(instance=source)

    if(request.POST.get("source_prev")):
        return HttpResponseRedirect("init_nslc")

    context["source_form"] = source_form

    # This part is here to display the correct placeholder.
    SOURCE_CHOICES = get_plugin_choices("source")
    parameters = dict()
    for source_type in SOURCE_CHOICES:
        module = importlib.import_module("plugins.source")
        class_ = getattr(module, source_type[0])
        parameters[source_type[0]] = class_().template
    context["parameters"] = parameters

    return render(request, 'home/index.html', context)


@login_required
def init_config(request):
    # Backend for the Configuration modal
    if Configuration.objects.count() == 0:
        configuration = Configuration()
        configuration.save()
    config = Configuration.objects.first()

    context = {"initialise": True}
    context["modal"] = "config"

    if(request.POST.get("config_next")):
        configuration_form = ConfigurationForm(request.POST, instance=config)
        if configuration_form.is_valid():
            config = configuration_form.save()
            print("ok")
            return HttpResponseRedirect("init_monitoring")
        else:
            logger.exception("errors :",configuration_form.errors)
    else:
        configuration_form = ConfigurationForm(instance=config)

    if(request.POST.get("config_prev")):
        return HttpResponseRedirect("init_source")
    context["configuration_form"] = configuration_form
    return render(request, 'home/index.html', context)


@login_required
def init_monitoring(request):
    # Backend for the Monitoring Initialisation modal
    if Configuration.objects.count():
        archive = Configuration.objects.first().archive
    else:
        archive = ""

    if ArchiveMonitoring.objects.count() == 0:
        monit = ArchiveMonitoring(archive=archive)
        monit.save()
    else:
        monit, created = ArchiveMonitoring.objects.get_or_create(
                            archive=archive)

    context = {"initialise": True}
    context["modal"] = "monitoring"


    if(request.POST.get("monitoring_next")):
        monitoring_form = ArchiveMonitoringInitForm(
                        request.POST, instance=monit)
        if monitoring_form.is_valid():
            monitoring_form.save()
            if not Network.objects.count():
                data_structure = monit.get_data_structure()
                nslc_list = data_structure.nslc_from_archive(archive)
                # print("nslc_list", nslc_list)
                for nslc in nslc_list:
                    n,s,l,c = nslc.split(".")
                    net, created = Network.objects.get_or_create(name = n)
                    sta, created = Station.objects.get_or_create(network = net,
                                                                 name = s)
                    loc, created = Location.objects.get_or_create(name = l)
                    chan, created = Channel.objects.get_or_create(name = c)
                    comp, created = Component.objects.get_or_create(name = c[0:2])
                    nslc, created = NSLC.objects.get_or_create(net=net, sta=sta,
                                                               loc=loc,
                                                               chan=chan)
            for net in Network.objects.all():
                if not monit.networks.filter(pk=net.pk).exists():
                    monit.networks.add(net)
                    monit.save()
            for sta in Station.objects.all():
                if not monit.stations.filter(pk=sta.pk).exists():
                    monit.stations.add(sta)
                    monit.save()
            for comp in Component.objects.all():
                if not monit.components.filter(pk=comp.pk).exists():
                    monit.components.add(comp)
                    monit.save()


        # update_monitoring.get_daily_stats(fake_progress)
        # update_monitoring.average_stats(fake_progress)
        return HttpResponseRedirect("init_qcconfig")
    else:
        monitoring_form = ArchiveMonitoringInitForm(instance=monit)
    if(request.POST.get("monitoring_prev")):
        return HttpResponseRedirect("init_config")

    context["monitoring_form"] = monitoring_form
    return render(request, 'home/index.html', context)


@login_required
def init_qcconfig(request):
    # Backend for the Monitoring Initialisation modal
    if Configuration.objects.count():
        archive = Configuration.objects.first().archive
    else:
        if ArchiveMonitoring.objects.count():
            archive = ArchiveMonitoring.objects.first().archive
        else:
            archive = ""

    if QCConfig.objects.count() == 0:
        qcconfig = QCConfig(archive=archive)
        qcconfig.save()
    else:
        qcconfig, created = QCConfig.objects.get_or_create(
                            archive=archive)

    context = {"initialise": True}
    context["modal"] = "qcconfig"


    if(request.POST.get("qcconfig_next")):
        qcconfig_form = QCConfigInitForm(
                        request.POST, instance=qcconfig)
        if qcconfig_form.is_valid():
            qcconfig_form.save()
        return HttpResponseRedirect("init_finish")
    else:
        qcconfig_form = QCConfigInitForm(instance=qcconfig)
    if(request.POST.get("monitoring_prev")):
        return HttpResponseRedirect("init_monitoring")

    context["qcconfig_form"] = qcconfig_form
    return render(request, 'home/index.html', context)


@login_required
def init_finish(request):
    # END OF INITIALISATION

    context = {"initialise": True}
    context["modal"] = "finish"

    if(request.POST.get("finish_prev")):
        return HttpResponseRedirect("init_qcconfig")

    elif(request.POST.get("finished")):
        context["initialise"] = False
        if Configuration.objects.count():
            config = Configuration.objects.first()
            config.initialisation = False

            #double check
            for net in Network.objects.all():
                config.networks.add(net)
                config.save()
            for sta in Station.objects.all():
                config.stations.add(sta)
                config.save()

            for nslc in NSLC.objects.all():
                config.nslc.add(nslc)
                config.save()

            config.save()
        logger.info("Initialisation done")
        return HttpResponseRedirect("/home")

    return render(request, 'home/index.html', context)
