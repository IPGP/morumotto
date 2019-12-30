# -*- coding: utf-8 -*-
import os
import sys
import logging
import warnings
import obspy
import time
import morumotto.toolbox as toolbox
from glob import glob
from datetime import datetime, timedelta, date
from collections import defaultdict
from django.utils import timezone
from archive import stats
from archive.models import Gap, Overlap, DataFile, NSLC, Network, Station
from .models import ArchiveMonitoring, Stat, ChanPath, CompPath, AverageStat, \
    AverageCompStat
from plugins import structure

logger = logging.getLogger('Monitoring')

class FakeProgress():
    def set_progress(self, start, end):
        return


def get_datafile(key,filename):
    if toolbox.isempty(filename):
        if DataFile.objects.filter(key=key, filename=filename):
            DataFile.objects.filter(key=key, filename=filename).delete()
        return DataFile.objects.none()

    files = DataFile.objects.filter(key=key,filename=filename)
    if files.count() == 1:
        return DataFile.objects.get(key=key,filename=filename)

    else:
        if files.count() > 1:
            # logger.warning("More than one Datafile exists for %s, %s\n"
            #                "Datafiles will be removed and a new one created."
            #                %(key, filename))
            for file in files:
                file.delete()
        now = datetime.utcnow().strftime('%s')
        return DataFile.objects.create(key=key,filename=filename,
                                       modif_time=float(now))


def update_paths():
    for path in ChanPath.objects.all():
        if not Stat.objects.filter(archive_name=path.archive,
                               net=path.net,
                               sta=path.sta,
                               loc=path.loc,
                               chan=path.chan).count():
            path.delete()
    for path in CompPath.objects.all():
        if not Stat.objects.filter(archive_name=path.archive,
                               net=path.net,
                               sta=path.sta,
                               loc=path.loc,
                               comp=path.comp).count():
            path.delete()


def get_stats_from_files(archive, nslc_list, data_format, data_structure,
                         starttime=None, endtime=None,
                         progress_recorder=FakeProgress()):
    """
    Reads database, get all gaps and transform then in daily statistics
    to be able to display them on calendar
    """
    logger.info("Updating daily statistics")
    loop_count = 0
    monitoring = ArchiveMonitoring.objects.first()
    if starttime == None or endtime == None:
        monitoring_start = datetime(year=monitoring.start_year, month=1, day=1)
        monitoring_end = (datetime(year=monitoring.end_year, month=12, day=31)
        +timedelta(days=1))
    else:
        monitoring_start = starttime
        monitoring_end = endtime

    file_list = data_structure.get_filelist(
              archive, nslc_list,
              monitoring_start,
              monitoring_end)


    for key, filename in file_list.items():
        # If file doesn't exists, skip this loop and continue to next file

        progress_recorder.set_progress(loop_count, len(file_list))
        loop_count += 1
        datafile = get_datafile(key=key, filename=filename)
        if not datafile:
            continue
        nslc = ".".join(key.split(".")[1:5])
        try:
            # logger.info("Updating statistics for %s" % filename)
            if datafile.modif_time == os.path.getmtime(filename):
                # already in database
                continue
            stream = data_format.read(filename)
            datafile.modif_time = os.path.getmtime(filename)
            datafile.save()
        except (TypeError, IndexError) as err:
            logger.exception("error", err)
            continue

        ss0 = stream[0].stats
        ss1 = stream[-1].stats
        sampling_rate = ss0.sampling_rate
        stream_start = ss0.starttime.datetime
        #timezone.make_aware(ss0.starttime.datetime)
        stream_end = ss1.endtime.datetime
        #timezone.make_aware(ss1.endtime.datetime)
        day_start = datetime(stream_start.year,
                             stream_start.month,
                             stream_start.day)
        day_end = day_start + timedelta(days=1)
        net = ss0.network
        sta = ss0.station
        loc = ss0.location
        chan = ss0.channel
        comp = chan[0:2]

        day = ss0.starttime.datetime.date()
        year = day.strftime('%Y')

        try:
            stats = Stat.objects.get(archive_name=archive,
                                     datafile=datafile,
                                     comp=comp, net=net, sta=sta, loc=loc,
                                     chan=chan, day=day, year=year)
            stats.starttime = stream_start
            stats.endtime = stream_end
            stats.save()
        except:
            if Stat.objects.filter(archive_name=archive, datafile=datafile,
                                   comp=comp, net=net, sta=sta, loc=loc,
                                   chan=chan, day=day, year=year).count() > 1:
                Stat.objects.filter(archive_name=archive, datafile=datafile,
                                    comp=comp, net=net, sta=sta, loc=loc,
                                    chan=chan, day=day, year=year).delete()
            stats = Stat.objects.create(archive_name=archive, datafile=datafile,
                                        comp=comp, net=net, sta=sta, loc=loc,
                                        chan=chan, day=day, year=year,
                                        starttime=stream_start,
                                        endtime=stream_end)

        new_path, created = ChanPath.objects.get_or_create(
                          archive=archive, net=net, sta=sta,
                          loc=loc, chan=chan)

        new_comp_path, created = CompPath.objects.get_or_create(
                               archive=archive, net=net,
                               sta=sta, loc=loc, comp=comp)

        gaps, overlaps = data_format.get_stats(stream)
        gapspan = sum(g[6] for g in gaps)
        n_edges_gaps=0
        if stream_start > day_start:
            span = (stream_start - day_start).total_seconds()
            # Cheking that the gap between day start and stream start is bigger
            # than a sample's length, ie. that it's bigger than
            # 1 / sampling rate
            if span > float(1 / sampling_rate):
                gapspan += span
                n_edges_gaps += 1
        if stream_end < day_end:
            span = (day_end - stream_end).total_seconds()
            # Same as above
            if span > float(1 / sampling_rate):
                gapspan += span
                n_edges_gaps += 1
        overlapspan = sum(o[6] for o in overlaps)
        stats.ngaps = len(gaps) + n_edges_gaps
        stats.noverlaps = len(overlaps)
        stats.timestamp = ss0.starttime.strftime('%s')
        if float(gapspan)/60 > 1:
            stats.gap_span = int(float(gapspan)/60)
        else:
            stats.gap_span = round(float(gapspan)/60,3)
        if float(overlapspan/60) > 1:
            stats.overlap_span = -int(float(overlapspan/60))
        else:
            stats.overlap_span = -round(float(overlapspan/60),3)

        stats.save()
    update_paths()



def average_stats(monitoring, progress_recorder=FakeProgress()):
    AverageCompStat.objects.all().delete()
    # compute network average:
    networks = [net.name for net in monitoring.networks.all()]
    stations = [sta.name for sta in monitoring.stations.all()]
    components_list = [comp.name for comp in
                       monitoring.components.filter(view_status="Component") ]
    others_list = [comp.name for comp in
                   monitoring.components.filter(view_status="Other") ]
    enabled_monitoring = [sta.name for sta in monitoring.stations.all()]
    archive = monitoring.archive
    start_year = monitoring.start_year
    end_year = monitoring.end_year
    years = range(int(start_year),int(end_year)+1,1) # pas encore pris en compte

    loop_count = 0
    for net in networks:
        stats = Stat.objects.filter(archive_name=archive, net=net,
                                    sta__in=stations)
        average_gap = defaultdict(float)
        average_overlap = defaultdict(float)
        average_gap_comp = defaultdict(lambda: defaultdict(float))
        average_overlap_comp = defaultdict(lambda: defaultdict(float))
        nsta = defaultdict(int)
        nsta_comp = defaultdict(lambda: defaultdict(int))
        for dailystats in stats:
            # if dailystats.av_new == True:
            if dailystats.comp in components_list:
                comp = dailystats.comp
            else:
                comp = "other"
            av_t = dailystats.day
            # print("av_t:",av_t)
            av_timestamp = av_t.strftime('%s')
            average_gap[av_timestamp] += dailystats.gap_span
            average_overlap[av_timestamp] += dailystats.overlap_span
            average_gap_comp[comp][av_timestamp] += dailystats.gap_span
            average_overlap_comp[comp][av_timestamp] += dailystats.overlap_span
            nsta[av_timestamp] += 1
            nsta_comp[comp][av_timestamp] += 1
            # dailystats.av_new = False

        for timestamp in sorted(average_gap.keys()):
            if not AverageStat.objects.filter(archive_name=archive,
                a_timestamp=timestamp, net=net).exists():
                av_stats = AverageStat(archive_name=archive, net=net)
                av_stats.a_timestamp = timestamp
                av_gapspan = average_gap[timestamp] / nsta[timestamp]

                if av_gapspan > 1:
                    av_stats.a_gap = int(av_gapspan)
                else:
                    av_stats.a_gap = round(av_gapspan,3)
                av_overlapspan = average_overlap[timestamp] / nsta[timestamp]
                if av_overlapspan > 1:
                    av_stats.a_overlap = int(av_overlapspan)
                else:
                    av_stats.a_overlap = round(av_overlapspan,3)

                av_stats.save()
                # print("av stats updated")
            else:
                whichdate = time.strftime(
                          "%Y-%m-%d %H:%M:%S",
                          time.localtime(AverageStat.objects.filter(
                            archive_name=archive,
                            a_timestamp=timestamp,
                            net=net).first().a_timestamp))
                continue
        # Average by component
        for component in monitoring.components.all():
            if component.name in components_list:
                comp = component.name
            else:
                comp = "other"
            for timestamp in sorted(average_gap_comp[comp].keys()):
                if not (AverageCompStat.objects.filter(archive_name=archive,
                    a_comp_timestamp=timestamp, net=net, comp=comp).exists()):
                    av_comp_stats = AverageCompStat(
                                  archive_name=archive,
                                  a_comp_timestamp=timestamp,
                                  net=net,
                                  comp=comp)
                    av_comp_gap = (average_gap_comp[comp][timestamp] /
                                   nsta_comp[comp][timestamp])
                    if av_comp_gap > 1 :
                        av_comp_stats.a_comp_gap = int(av_comp_gap)
                    else:
                        av_comp_stats.a_comp_gap = round(av_comp_gap,3)

                    av_comp_overlap = (average_overlap_comp[comp][timestamp] /
                                           nsta_comp[comp][timestamp])
                    if av_comp_overlap > 1 :
                        av_comp_stats.a_comp_overlap = int(av_comp_overlap)
                    else:
                        av_comp_stats.a_comp_overlap = round(av_comp_overlap,3)
                    av_comp_stats.save()
                else:
                    continue
        loop_count += 1
        progress_recorder.set_progress(loop_count, len(networks))


def update_average_stats(networks, stations,
    components, archive, start_year, end_year):
    """
    This method is used within the admin interface, to update statistics for
    a given set of Networks/Stations/Components, only if configuration changes
    """
    AverageCompStat.objects.all().delete()
    networks = [net.name for net in networks]
    stations = [sta.name for sta in stations]
    components_list = [comp.name for comp in
                       components.filter(view_status="Component") ]
    others_list = [comp.name for comp in
                   components.filter(view_status="Other") ]
    years = range(int(start_year),int(end_year)+1,1)

    for net in networks:
        stats = Stat.objects.filter(archive_name=archive, net=net,
                                    sta__in=stations)
        average_gap = defaultdict(float)
        average_overlap = defaultdict(float)
        average_gap_comp = defaultdict(lambda: defaultdict(float))
        average_overlap_comp = defaultdict(lambda: defaultdict(float))
        nsta = defaultdict(int)
        nsta_comp = defaultdict(lambda: defaultdict(int))
        for dailystats in stats:
            if dailystats.comp in components_list:
                comp = dailystats.comp
            else:
                comp = "other"
            av_t = dailystats.day
            av_timestamp = av_t.strftime('%s')
            average_gap[av_timestamp] += dailystats.gap_span
            average_overlap[av_timestamp] += dailystats.overlap_span
            average_gap_comp[comp][av_timestamp] += dailystats.gap_span
            average_overlap_comp[comp][av_timestamp] += dailystats.overlap_span
            nsta[av_timestamp] += 1
            nsta_comp[comp][av_timestamp] += 1

        for timestamp in sorted(average_gap.keys()):
            if not AverageStat.objects.filter(archive_name=archive,
                a_timestamp=timestamp, net=net).exists():
                av_stats = AverageStat(archive_name=archive, net=net)
                av_stats.a_timestamp = timestamp
                av_gapspan = average_gap[timestamp] / nsta[timestamp]

                if av_gapspan > 1:
                    av_stats.a_gap = int(av_gapspan)
                else:
                    av_stats.a_gap = round(av_gapspan,3)
                av_overlapspan = average_overlap[timestamp] / nsta[timestamp]
                if av_overlapspan > 1:
                    av_stats.a_overlap = int(av_overlapspan)
                else:
                    av_stats.a_overlap = round(av_overlapspan,3)
                av_stats.save()
                # print("av stats updated")
            else:
                whichdate = time.strftime(
                          "%Y-%m-%d %H:%M:%S",
                          time.localtime(AverageStat.objects.filter(
                            archive_name=archive,
                            a_timestamp=timestamp,
                            net=net).first().a_timestamp))
                continue
        # Average by component
        for component in components:
            if component.name in components_list:
                comp = component.name
            else:
                comp = "other"
            for timestamp in sorted(average_gap_comp[comp].keys()):
                if not AverageCompStat.objects.filter(archive_name=archive,
                    a_comp_timestamp=timestamp, net=net, comp=comp).exists():
                    av_comp_stats = AverageCompStat(
                                  archive_name=archive,
                                  a_comp_timestamp=timestamp,
                                  net=net,
                                  comp=comp)
                    av_comp_gap = (average_gap_comp[comp][timestamp] /
                                   nsta_comp[comp][timestamp])
                    if av_comp_gap > 1 :
                        av_comp_stats.a_comp_gap = int(av_comp_gap)
                    else:
                        av_comp_stats.a_comp_gap = round(av_comp_gap,3)

                    av_comp_overlap = (average_overlap_comp[comp][timestamp] /
                                           nsta_comp[comp][timestamp])
                    if av_comp_overlap > 1 :
                        av_comp_stats.a_comp_overlap = int(av_comp_overlap)
                    else:
                        av_comp_stats.a_comp_overlap = round(av_comp_overlap,3)
                    av_comp_stats.save()
                else:
                    continue
