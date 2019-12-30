# -*- coding: utf-8 -*-
import os
import logging
from .models import ArchiveMonitoring, AverageStat, AverageCompStat, Stat, \
    ChanPath, CompPath
from archive.models import SourceAvailability, Gap, NSLC
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from collections import OrderedDict
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.http import HttpResponseRedirect
import morumotto.toolbox as toolbox
from celery.task.control import inspect
from plugins.format import miniSEED
from datetime import datetime
import time
from morumotto import tasks

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR/")
LEAP_SECONDS = toolbox.get_leaps(os.path.join(BASE_DIR, "leapsecond.list"))

logger = logging.getLogger('Status')

def netgaps(request):
    # This is a view for the average gaps statistics of the Network(s)
    if ArchiveMonitoring.objects.count() == 0:
        logger.warning("Monitoring not yet configured")
        return HttpResponseRedirect('/home/init_monitoring')

    monitoring_config = ArchiveMonitoring.objects.first()
    av_stats = AverageStat.objects.all()
    networks = monitoring_config.networks.all()
    stations = [s.name for s in monitoring_config.stations.all()]
    comp_list = set([nslc.chan.name[0:2] for nslc in NSLC.objects.filter(
                 net__in = networks, sta__name__in=stations)])
    av_comp_stats = AverageCompStat.objects.filter(comp__in=comp_list)
    statistics = dict()
    default_path = dict()

    components = monitoring_config.components.filter(name__in=comp_list)
    display_list = [comp.name for comp in
                    monitoring_config.components.filter(view_status="Component")]
    others_list = [comp.name for comp in
                   monitoring_config.components.filter(view_status="Other")]
    archive = monitoring_config.archive
    comp_list = []
    net_list=[]
    for network in networks:

        net = network.name
        net_av_stats = av_stats.filter(archive_name=archive, net=net)

        av_gapslist = OrderedDict(
                    (o.a_timestamp, o.a_gap)
                    for o in net_av_stats)
        ref = str("ref_" + net)
        statistics[ref] = av_gapslist
        first_loop = True
        for component in components:
            if component.name in display_list:
                comp = component.name
            elif component.name in others_list:
                comp = "other"
            else:
                continue
            if av_comp_stats.filter(archive_name=archive,
                                    net=net,
                                    comp=comp).exists():
                net_comp_av_stats = av_comp_stats.filter(net=net, comp=comp)
                comp_av_gapslist = OrderedDict(
                                 (o.a_comp_timestamp, o.a_comp_gap)
                                 for o in net_comp_av_stats)
                ref = "ref_" + net + "_" + comp
                statistics[ref] = comp_av_gapslist
                comp_list.append(comp)
                net_list.append(net)
            if Stat.objects.filter(archive_name=archive,
                                   net=net,
                                   comp=comp).count():
                comp_first = Stat.objects.filter(
                           archive_name=archive,
                           net=net,sta__in=stations,
                           comp=comp).order_by('sta').first()
                default_path[net + "_" + comp] = (comp_first.net + "/"
                                                  + comp_first.sta + "/"
                                                  + comp_first.loc + "/"
                                                  + comp_first.comp)
            if comp == "other" and first_loop:
                others = monitoring_config.components.filter(view_status="Other")
                others_first = others.first()
                comp_first = Stat.objects.filter(
                           archive_name=archive, net=net, sta__in=stations,
                           comp=others_first).order_by('sta').first()
                if comp_first != None:
                    default_path[net + "_" + comp] = (comp_first.net + "/"
                                                      + comp_first.sta + "/"
                                                      + comp_first.loc + "/"
                                                      + comp_first.comp)
                    # avoiding to get through this loop for each comp
                    first_loop = False

    this_year = datetime.utcnow().year
    start_year = monitoring_config.start_year
    end_year = monitoring_config.end_year
    year_list = range(start_year, end_year + 1)


    monitoring_id = monitoring_config.pk
    context = {"year_list": year_list}
    context['monitoring_id'] = monitoring_id

    context['statistics'] = statistics
    context['default_path'] = default_path
    context["net_list"] = sorted(set(net_list))
    context["comp_list"] = sorted(set(comp_list))

    return render(request, 'monitoring/net_gaps.html', context)


def netoverlaps(request):
    # This is a view for the average overlaps statistics of the Network(s)
    if ArchiveMonitoring.objects.count() == 0:
        logger.warning("Monitoring not yet configured")
        return HttpResponseRedirect('/home/init_monitoring')

    monitoring_config = ArchiveMonitoring.objects.first()
    av_stats = AverageStat.objects.all()
    networks = monitoring_config.networks.all()
    stations = [s.name for s in monitoring_config.stations.all()]
    comp_list = set([nslc.chan.name[0:2] for nslc in NSLC.objects.filter(
                 net__in = networks, sta__name__in=stations)])
    av_comp_stats = AverageCompStat.objects.filter(comp__in=comp_list)
    statistics = dict()
    default_path = dict()

    components = monitoring_config.components.filter(name__in=comp_list)
    display_list = [comp.name for comp in
                    monitoring_config.components.filter(view_status="Component")]
    others_list = [comp.name for comp in
                   monitoring_config.components.filter(view_status="Other")]
    archive = monitoring_config.archive
    comp_list = []
    net_list=[]

    for network in networks:
        net = network.name
        net_av_stats = av_stats.filter(archive_name=archive, net=net)
        av_overlapslist = OrderedDict(
                        (o.a_timestamp, o.a_overlap)
                        for o in net_av_stats)
        ref = str("ref_" + net)
        statistics[ref] = av_overlapslist
        first_loop = True
        for component in components:
            if component.name in display_list:
                comp = component.name
            elif component.name in others_list:
                comp = "other"
            else:
                continue
            if av_comp_stats.filter(archive_name=archive,
                                    net=net,
                                    comp=comp).exists():
                net_comp_av_stats = av_comp_stats.filter(net=net, comp=comp)
                comp_av_overlapslist = OrderedDict(
                                     (o.a_comp_timestamp, o.a_comp_overlap)
                                     for o in net_comp_av_stats)
                ref = "ref_" + net + "_" + comp
                statistics[ref] = comp_av_overlapslist
                comp_list.append(comp)
                net_list.append(net)
            if Stat.objects.filter(archive_name=archive,
                                   net=net,
                                   comp=comp).count():
                comp_first = Stat.objects.filter(
                           archive_name=archive, net=net,
                           comp=comp).order_by('sta').first()

                default_path[net + "_" + comp] = (comp_first.net + "/"
                                                  + comp_first.sta + "/"
                                                  + comp_first.loc + "/"
                                                  + comp_first.comp)
            if comp == "other" and first_loop:
                others = monitoring_config.components.filter(view_status="Other")
                others_first = others.first()
                comp_first = Stat.objects.filter(
                           archive_name=archive, net=net, sta__in=stations,
                           comp=others_first).order_by('sta').first()
                if comp_first != None:
                    default_path[net + "_" + comp] = (comp_first.net + "/"
                                                      + comp_first.sta + "/"
                                                      + comp_first.loc + "/"
                                                      + comp_first.comp)
                    # avoiding to get through this loop for each comp
                    first_loop = False

    this_year = datetime.utcnow().year
    start_year = monitoring_config.start_year
    end_year = monitoring_config.end_year
    year_list = range(start_year, end_year + 1)


    monitoring_id = monitoring_config.pk
    context = {"year_list": year_list}
    context["leap_seconds"] = LEAP_SECONDS
    context['monitoring_id'] = monitoring_id
    context['statistics'] = statistics
    context['default_path'] = default_path
    context["net_list"] = sorted(set(net_list))
    context["comp_list"] = sorted(set(comp_list))

    return render(request, 'monitoring/net_overlaps.html', context)


def default_gaps(request):
    if ArchiveMonitoring.objects.count() == 0:
        logger.error("no monitoring")
        return HttpResponseRedirect('/home/init_monitoring')

    monitoring_config = ArchiveMonitoring.objects.first()

    networks = [n.name for n in monitoring_config.networks.all()]
    stations = [s.name for s in monitoring_config.stations.all()]
    print(networks, stations, CompPath.objects.filter(net__in=networks,
                                                   sta__in=stations))
    path = get_list_or_404(CompPath.objects.filter(net__in=networks,
                                                   sta__in=stations))[0]
    redirection="gaps/%s/%s/%s/%s" %(path.net,path.sta,path.loc,path.comp)
    return HttpResponseRedirect(redirection)


def gaps(request, network_id, comp_id, station_id, location_id):
    # This is a view for the average gaps statistics by Station
    if ArchiveMonitoring.objects.count() == 0:
        logger.error("no monitoring")
        return HttpResponseRedirect('/home/init_monitoring')
    monitoring_config = ArchiveMonitoring.objects.first()
    archive = monitoring_config.archive
    stations = [s.name for s in monitoring_config.stations.all()]
    stats = Stat.objects.filter(archive_name=archive, net=network_id,
                                sta__in=stations)
    statistics = dict()
    chan_list = []
    for chan in sorted(set(stats.values_list('chan', flat=True))):
        if stats.filter(net=network_id,
                        sta=station_id,
                        loc=location_id,
                        chan=chan).count():
            gapslist = stats.filter(net=network_id,
                                    sta=station_id,
                                    loc=location_id,
                                    chan=chan)
            gapslist = OrderedDict((o.timestamp, o.gap_span) for o in gapslist)
            ref = ("ref_" + network_id + "_" + station_id
                   + "_" + location_id + "_" + chan)
            statistics[ref] = gapslist
            chan_list.append(chan)

    others = [comp.name for comp in
              monitoring_config.components.filter(view_status="Other") ]
    sta_list = [sta.name for sta in monitoring_config.stations.all()]
    this_year = datetime.utcnow().year
    start_year = monitoring_config.start_year
    end_year = monitoring_config.end_year
    year_list = range(start_year, end_year + 1)
    context = {"year_list": year_list}

    comp_list = sorted([comp for comp in
                        set(stats.values_list('comp', flat=True)) ])
    chan_list = sorted(set(chan_list))
    chan_paths = sorted(OrderedDict((o.chan_path,o.chan_path) for o in
                                    ChanPath.objects.filter(archive=archive,
                                    net=network_id,
                                    sta__in=sta_list)))
    comp_paths = sorted(OrderedDict((o.comp_path,o.comp_path) for o in
                                    CompPath.objects.filter(archive=archive,
                                    net=network_id,
                                    sta__in=sta_list)))



    context["others_list"] = [o for o in others if o in comp_list]
    context["network_id"] = network_id
    context["station_id"] = station_id
    context["comp_id"] = comp_id
    context["location_id"] = location_id

    context["comp_list"] = comp_list
    context["chan_list"] = chan_list

    context["statistics"] = statistics
    context["chan_paths"] = chan_paths
    context["comp_paths"] = comp_paths
    return render(request, 'monitoring/gaps.html', context)


def default_overlaps(request):
    if ArchiveMonitoring.objects.count() == 0:
        logger.error("no monitoring")
        return HttpResponseRedirect('/home/init_monitoring')

    monitoring_config = ArchiveMonitoring.objects.first()

    networks = [n.name for n in monitoring_config.networks.all()]
    stations = [s.name for s in monitoring_config.stations.all()]
    print(networks, stations, CompPath.objects.filter(net__in=networks,
                                                   sta__in=stations))
    path = get_list_or_404(CompPath.objects.filter(net__in=networks,
                                                   sta__in=stations))[0]
    redirection="overlaps/%s/%s/%s/%s" %(path.net,path.sta,path.loc,path.comp)
    return HttpResponseRedirect(redirection)


def overlaps(request, network_id, comp_id, station_id, location_id):
    # This is a view for the average overlaps statistics by Station
    if ArchiveMonitoring.objects.count() == 0:
        logger.error("no monitoring")
        return HttpResponseRedirect('/home/init_monitoring')
    monitoring_config = ArchiveMonitoring.objects.first()
    archive = monitoring_config.archive
    stations = [s.name for s in monitoring_config.stations.all()]
    stats = Stat.objects.filter(archive_name=archive, net=network_id,
                                sta__in=stations)

    statistics = dict()
    chan_list = []
    for chan in sorted(set(stats.values_list('chan', flat=True))):
        if stats.filter(net=network_id,
                        sta=station_id,
                        loc=location_id,
                        chan=chan).count():
            overlapslist = stats.filter(net=network_id,
                                        sta=station_id,
                                        loc=location_id,
                                        chan=chan)
            overlapslist = OrderedDict(
                         (o.timestamp, o.overlap_span)
                         for o in overlapslist)
            ref = ("ref_" + network_id + "_" + station_id + "_"
                   + location_id + "_" + chan)
            statistics[ref] = overlapslist
            chan_list.append(chan)

    others = [comp.name for comp in
              monitoring_config.components.filter(view_status="Other") ]
    sta_list = [sta.name for sta in monitoring_config.stations.all()]
    this_year = datetime.utcnow().year
    start_year = monitoring_config.start_year
    end_year = monitoring_config.end_year
    year_list = range(start_year, end_year + 1)
    context = {"year_list": year_list}
    context["leap_seconds"] = LEAP_SECONDS
    comp_list = sorted([comp for comp in
                        set(stats.values_list('comp', flat=True)) ])
    # chan_list = sorted([chan for chan in
    #                     set(stats.values_list('chan', flat=True)) ])
    chan_list = sorted(set(chan_list))
    chan_paths = sorted(OrderedDict((o.chan_path,o.chan_path) for o in
                                    ChanPath.objects.filter(archive=archive,
                                    net=network_id,
                                    sta__in=sta_list)))
    comp_paths = sorted(OrderedDict((o.comp_path,o.comp_path) for o in
                                    CompPath.objects.filter(archive=archive,
                                    net=network_id,
                                    sta__in=sta_list)))


    context["others_list"] = [o for o in others if o in comp_list]

    context["network_id"] = network_id
    context["station_id"] = station_id
    context["comp_id"] = comp_id
    context["location_id"] = location_id

    context["comp_list"] = comp_list
    context["chan_list"] = chan_list
    context["statistics"] = statistics
    context["chan_paths"] = chan_paths
    context["comp_paths"] = comp_paths

    return render(request, 'monitoring/overlaps.html', context)


def default_availability(request):
    path = get_list_or_404(SourceAvailability.objects.all().order_by('nslc'))[0]
    redirection = "availability/%s/%s/%s/%s" %(path.nslc.net.name,
                                               path.nslc.sta.name,
                                               path.nslc.loc.name,
                                               path.nslc.chan.name[0:2])
    return HttpResponseRedirect(redirection)


def availability(request, network_id, comp_id, station_id, location_id):
    # This is a view for the data availability by Station
    if ArchiveMonitoring.objects.count() == 0:
        logger.error("no monitoring")
        return HttpResponseRedirect('/home/init_monitoring')
    monitoring_config = ArchiveMonitoring.objects.first()
    archive = monitoring_config.archive
    others = [c.name for c in monitoring_config.components.filter(view_status="Other")]

    avail_exists = SourceAvailability.objects.filter(nslc__net__name=network_id)
    source_list = set([a.source for a in
                       avail_exists.filter(nslc__sta__name=station_id,
                                           nslc__loc__name=location_id)])

    nslc_list = set([a.nslc for a in avail_exists])
    chan_list = set([a.nslc for a in
                     avail_exists.filter(nslc__sta__name=station_id,
                                         nslc__loc__name=location_id)])

    comp_list = sorted(set([nslc.chan.name[:-1] for nslc in nslc_list if
                            nslc.chan.name[:-1] not in others]))
    others_list = sorted(set([nslc.chan.name[-1] for nslc in nslc_list if
                              nslc.chan.name[:-1] in others]))

    availability = SourceAvailability.objects.filter(
                 nslc__net__name=network_id,
                 nslc__sta__name=station_id,
                 nslc__loc__name=location_id)
    station_gaps = Gap.objects.filter(
                 archive=archive,
                 nslc__net__name=network_id,
                 nslc__sta__name=station_id,
                 nslc__loc__name=location_id,
                 status__in=["new, in_process"])

    sta_list = [sta.name for sta in monitoring_config.stations.all()
                if SourceAvailability.objects.filter(
                    nslc__sta__name=sta.name).count()
                ]
    chan_paths = sorted(OrderedDict((o.chan_path,o.chan_path) for o in
                                    ChanPath.objects.filter(archive=archive,
                                    net=network_id,
                                    sta__in=sta_list)))
    comp_paths = sorted(OrderedDict((o.comp_path,o.comp_path) for o in
                                    CompPath.objects.filter(archive=archive,
                                    net=network_id,
                                    sta__in=sta_list)))



    this_year = datetime.utcnow().year
    start_year = monitoring_config.start_year
    end_year = monitoring_config.end_year
    year_list = range(start_year, end_year + 1)
    context = {"year_list": year_list}

    context["network_id"] = network_id
    context["station_id"] = station_id
    context["comp_id"] = comp_id
    context["location_id"] = location_id

    context["nslc_list"] = nslc_list
    context["comp_list"] = comp_list
    context["chan_list"] = chan_list
    context["others_list"] = others_list
    context["source_list"] = source_list
    context["chan_paths"] = chan_paths
    context["comp_paths"] = comp_paths

    context["availability"] = availability
    context["station_gaps"] = station_gaps

    return render(request, 'monitoring/availability.html', context)


def stats(request, network_id, station_id, location_id, chan_id):
    # This is a view for all statistics for a given NSLC

    if ArchiveMonitoring.objects.count() == 0:
        logger.error("no monitoring")
        return HttpResponseRedirect('/home/init_monitoring')
    monitoring_config = ArchiveMonitoring.objects.first()
    archive = monitoring_config.archive
    stats_list = Stat.objects.filter(archive_name=archive,
                                     net=network_id,
                                     sta=station_id,
                                     loc=location_id,
                                     chan=chan_id)

    this_year = datetime.utcnow().year
    start_year = monitoring_config.start_year
    end_year = monitoring_config.end_year
    year_list = range(start_year, end_year + 1)
    context = {"year_list": year_list}
    context["stats_list"] = stats_list

    return render(request, 'monitoring/stats.html', context)


def plot(request, year_id, filename_id):
    # This is a view of the plot of an obspy stream
    if ArchiveMonitoring.objects.count() == 0:
        logger.error("no monitoring")
        return HttpResponseRedirect('/home/init_monitoring')
    split_path = filename_id.split(".")
    jday = int(split_path[-1])
    chan = split_path[-3]
    loc = split_path[-4]
    sta = split_path[-5]
    net = split_path[-6]

    date = toolbox.yyyymmdd(year_id,jday)
    monitoring_config = ArchiveMonitoring.objects.first()
    archive = monitoring_config.archive
    stats_list = Stat.objects.filter(
               archive_name=archive, net=net, sta=sta,
               loc=loc, chan=chan, day=date)

    extension = "svg"
    plotdir = os.path.join(WORKING_DIR, "PLOT/")
    if not os.path.exists(plotdir):
        os.makedirs(plotdir)
    plotfilename = plotdir + filename_id + "." + extension
    streamfile = stats_list.first().datafile.filename
    seed = miniSEED()

    # next = Stat.objects.filter(
    #      archive_name=archive, net=net, sta=sta,
    #      loc=loc, chan=chan, day__gt=stats_list.first().day).order_by('day').first()
    # previous = Stat.objects.filter(
    #          archive_name=archive, net=net, sta=sta,
    #          loc=loc, chan=chan, day__lt=stats_list.first().day).order_by('day').first()

    try:
        next = Stat.get_next_by_day(stats_list.first(),archive_name=archive,
         net=net, sta=sta,
         loc=loc, chan=chan)
    except:
        next = []
    try:
        previous = Stat.get_previous_by_day(stats_list.first(),archive_name=archive,
             net=net, sta=sta,
             loc=loc, chan=chan)
    except:
        previous = []

    context = {"filename_id": filename_id}
    context["date"] = date
    context["extension"] = extension
    context["stats_list"] = stats_list
    context["next"] = next
    context["previous"] = previous
    context["display_picture"] = seed.generate_plot(streamfile, plotfilename)
    context["plotdir"] = os.path.join("WORKING_DIR/", "PLOT/")

    return render(request, 'monitoring/plot.html', context)

@login_required
def update_stats(request):
    if ArchiveMonitoring.objects.count() == 0:
        logger.error("no monitoring")
        return HttpResponseRedirect('/home/init_monitoring')
    monitoring_config = ArchiveMonitoring.objects.first()
    context = {'task_id': 0}

    celery_status = tasks.get_celery_worker_status()

    # If a job is already running, get its task_id to display it
    # --> This is time consuming to load page ! Comment what's between ### to
    # accelerate the page.

    ################ Begin comment section ################
    try:
        taskid = list(inspect().active().values())[0][0]['id']
        if taskid:
            context["display_statistics"] = True
            context["task_id"] = taskid
    except:
        # No celery worker found
        pass
    ################ End comment section ##################

    if(request.POST.get('celery_update_monitoring')):
        context["display_statistics"] = True
        result = tasks.update_statistics.delay(monitoring_config.id)

        context['task_id'] = result.task_id

    context['celery_status'] = celery_status

    return render(request, 'monitoring/update_stats.html', context )


# OBSOLETE
# def monitoring_setup(request):
#     # view where user can modify config and ArchiveMonitoring
#     if ArchiveMonitoring.objects.count() == 0:
#         monitoring = ArchiveMonitoring()
#     else:
#         monitoring = ArchiveMonitoring.objects.first()
#     form = ArchiveMonitoringForm(instance=monitoring)
#     if(request.POST.get('validate')):
#         # This is the form to configure the ArchiveMonitoring model,
#         # except for the components field
#         form = ArchiveMonitoringForm(request.POST, instance=monitoring)
#         if form.is_valid():
#             form.save()
#         if form.has_changed():
#             result = tasks.update_statistics.delay()
#
#
#         # This is the customized form to configure the components
#         # Validation of this form is not yet implemented but has to be done
#         components_list = request.POST.getlist('ComponentList')
#         others_list = request.POST.getlist('OthersList')
#         disabled_list = request.POST.getlist('DisabledList')
#         enabled_monitoring = request.POST.getlist('MonitoringEnabledList')
#         disabled_monitoring = request.POST.getlist('MonitoringDisabledList')
#
#         if (update_components(components_list, others_list, disabled_list, monitoring)
#             or update_stations(enabled_monitoring, disabled_monitoring, monitoring)):
#             # If something has changed, we need to compute average stats again
#             result = tasks.update_statistics.delay()
#
#
#     components = [comp.name for comp in monitoring.components.filter(view_status="Component") ]
#     others = [comp.name for comp in monitoring.components.filter(view_status="Other") ]
#     disabled = [comp.name for comp in monitoring.components.filter(view_status="Disabled") ]
#
#     sta_monitoring_enabled = [sta for sta in monitoring.stations.filter(view_status="MonitoringEnabled") ]
#     sta_monitoring_disabled = [sta for sta in monitoring.stations.filter(view_status="MonitoringDisabled") ]
#
#     celery_status = tasks.get_celery_worker_status()
#
#     context = {'form': form}
#     context['celery_status'] = celery_status
#     context["components_list"] = sorted(components)
#     context["others_list"] = sorted(others)
#     context["disabled_list"] = sorted(disabled)
#     context["sta_monitoring_enabled"] = sta_monitoring_enabled
#     context["sta_monitoring_disabled"] = sta_monitoring_disabled
#
#     return render(request, 'monitoring/setup.html', context )


def progress_stats(request):
    # This is a view to show the progress of the current celery process
    context = dict()

    try:
        i = inspect()
        print("active : ", i.active().values())
        if not list(i.active().values())[0]:
            taskid = None
        else:
            taskid = list(i.active().values())[0][0]['id']
            print(taskid)
    except:
        taskid = None
        print("inspect failed")

    if taskid != None:
        context["task_id"] = taskid
    else:
        result = tasks.update_statistics.delay()
        context['task_id'] = result.task_id

    return render(request, 'monitoring/progress_statistics.html', context)



def metrics(request):
    # view which displays all metrics for a given set of data (net, sta or chan)
    # radio button to select which metrics we want to display
    pass
