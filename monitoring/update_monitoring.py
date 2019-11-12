# -*- coding: utf-8 -*-
import os
import sys
import logging
import warnings
import obspy
import time
import siqaco.toolbox as toolbox
from glob import glob
from datetime import datetime, timedelta, date
from collections import defaultdict
from django.utils import timezone
from seismicarchive import stats
from seismicarchive.models import Gap, Overlap, DataFile, NSLC, Network, Station
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
        progress_recorder.set_progress(loop_count, len(networks))
        loop_count += 1
        stats = Stat.objects.filter(archive_name=archive, net=net,
                                    sta__in=stations)
        print(stats)
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
    years = range(int(start_year),int(end_year)+1,1) # pas encore pris en compte

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


##################################OLD STUFF#####################################
# def update_stats_from_files(progress_recorder,starttime=None,endtime=None):
#     monitoring = ArchiveMonitoring.objects.first()
#     if starttime == None:
#         monitoring_start = datetime(year=monitoring.start_year, month=1, day=1)
#     else:
#         monitoring_start = starttime
#
#     if endtime == None:
#         monitoring_end = (datetime(year=monitoring.end_year, month=12, day=31)
#                           +timedelta(days=1))
#     else:
#         monitoring_end = endtime
#
#     net_list = [net for net in monitoring.networks.all()]
#     sta_list = [sta for sta in monitoring.stations.all()]
#     nslc_list = [nslc for nslc in NSLC.objects.filter(net__in=net_list,
#                                                       sta__in=sta_list)]
#     archive = monitoring.archive
#     max_gaps = 10 #a modif
#
#     datastructure = monitoring.get_data_structure()
#     dataformat = monitoring.get_data_format()
#     file_list = datastructure.get_filelist(archive, nslc_list,
#                                            monitoring_start, monitoring_end)
#     gapsoverlaps = stats.get_gapsoverlaps(archive, nslc_list, dataformat,
#                                           file_list, max_gaps,
#                                           monitoring_start, monitoring_end)
#
#     get_daily_stats(progress_recorder,monitoring_start, monitoring_end)

def get_datafile_old(nslc, archive, date, data_structure, data_format):
    """
    Returns the datafile for the given set of nslc, archive, date
    If it doesn't exists, returns an empty query set.

    Only works for SDS archive
    """

    year = date.strftime('%Y')
    jday = date.strftime('%j')
    net, sta, loc, chan = nslc.code.split('.')
    key = "%s.%s.%s.%s.%s.%s" %(year, net, sta, loc, chan, jday)

    channelpath = data_structure.get_path(archive, nslc.code, year)
    filepattern = data_structure.get_filepattern(nslc.code, jday , year)
    try:
        filename = glob(os.path.join(channelpath, filepattern))[0]
        modif_time = os.path.getmtime(filename)
        datafile, created = DataFile.objects.get_or_create(
                          key=key, filename=filename, modif_time=modif_time)
        return datafile
    except:
        logger.error("No data found for %s"
                     %os.path.join(channelpath, filepattern))
        return None


def get_daily_stats(progress_recorder, starttime=None, endtime=None):
    """
    Reads database, get all gaps and transform then in daily statistics
    to be able to display them on calendar
    """
    logger.info("Computing daily statistics")
    monitoring = ArchiveMonitoring.objects.first()
    if starttime == None or endtime == None:
        monitoring_start = datetime(year=monitoring.start_year, month=1, day=1)
        monitoring_end = (datetime(year=monitoring.end_year, month=12, day=31)
                          +timedelta(days=1))
    else:
        monitoring_start = starttime
        monitoring_end = endtime

    archive = monitoring.archive
    data_structure = monitoring.get_data_structure()
    data_format = monitoring.get_data_format()

    network_list = [net for net in monitoring.networks.all()]
    station_list = [sta for sta in monitoring.stations.all()]
    nslc_list = [n for n in NSLC.objects.filter(net__in=network_list,
                                                sta__in=station_list)]
    gap_list = Gap.objects.filter(archive=archive,
                                  starttime__lte=monitoring_end,
                                  endtime__gte=monitoring_start)
    overlap_list = Overlap.objects.filter(archive=archive,
                                          starttime__lte=monitoring_end,
                                          endtime__gte=monitoring_start)
    loop_count = 0

    for nslc in nslc_list:
        net, sta, loc, chan = nslc.code.split(".")
        comp = chan[0:2]
        span = defaultdict(lambda: defaultdict(list))
        for date in daterange(monitoring_start, monitoring_end):
            day_start = datetime(date.year,date.month,date.day)
            day_end = day_start + timedelta(days=1)
            day_gaps = Gap.objects.filter(nslc=nslc,
                                          archive=archive,
                                          endtime__gte=day_start,
                                          starttime__lte=day_end)

            day_overlaps = Overlap.objects.filter(nslc=nslc,
                                                  archive=archive,
                                                  endtime__gte=day_start,
                                                  starttime__lte=day_end)
            datafile = get_datafile(nslc, archive, day_start,
                                    data_structure, data_format)
            if not datafile:
                logger.warning("Warning No file found in archive %s for NSLC %s"
                               " for the date : %s" %(archive, nslc, day_start))
                continue

            # If we didn't found any gaps for the given day, we read stream and
            # compute statistics from stream
            if day_gaps.count() == 0:
                get_stats_from_file(archive, datafile.filename, data_format)

            for gap in day_gaps:
                gapspan = gap.endtime - gap.starttime

                span[day_start]["gaps"].append(gapspan.total_seconds())
                loop_count += 1
                progress_recorder.set_progress(loop_count,
                    2*(len(gap_list)+len(overlap_list)))

            for overlap in overlap_list:
                overlapspan = overlap.endtime - overlap.starttime

                span[day_start]["overlaps"].append(overlapspan.total_seconds())
                loop_count += 1
                progress_recorder.set_progress(loop_count,
                    2*(len(gap_list)+len(overlap_list)))

        for date in sorted(span.keys()):
            datafile = get_datafile(nslc, archive, date,
                                    data_structure, data_format)
            gapspan = sum(d for d in span[date]["gaps"])
            overlapspan = sum(d for d in span[date]["overlaps"])
            jday = date.strftime('%j')
            year = date.strftime('%Y')
            starttime = date
            endtime = date + timedelta(days=1)

            stats, created = Stat.objects.get_or_create(
                           archive_name=archive, datafile=datafile, comp=comp,
                           net=net,sta=sta,loc=loc,chan=chan, day=date,
                           year=year, starttime=starttime, endtime=endtime,
                           )
            # monitoring_paths(monitoring, archive, net, sta, loc, chan, comp)
            new_path, created = ChanPath.objects.get_or_create(
                              archive=archive, net=net, sta=sta,
                              loc=loc, chan=chan)
            new_comp_path, created = CompPath.objects.get_or_create(
                                   archive=archive, net=net,
                                   sta=sta, loc=loc, comp=comp)

            stats.ngaps = len(span[date]["gaps"])
            stats.noverlaps = len(span[date]["overlaps"])

            stats.timestamp = starttime.strftime('%s')
            stats.gap_span = int(float(gapspan)/60)
            stats.overlap_span = -int(float(overlapspan/60))

            stats.save()
            loop_count += 1
            progress_recorder.set_progress(loop_count,
                2*(len(gap_list)+len(overlap_list)))




def get_stats_from_files_old(progress_recorder):
    # OLD
    # Only works for sds and seed files.
    monitoring = ArchiveMonitoring.objects.first()
    archive = monitoring.archive
    net_list = [net.name for net in monitoring.networks.all()]
    sta_list = [sta.name for sta in monitoring.stations.all()]
    comp_list = [comp.name for comp in monitoring.components.all()]
    channelpaths = browse_sds(monitoring)
    loop_count = 0
    for channelpath in channelpaths:
        split_path = channelpath.split(os.sep)
        channel = split_path[-1]
        station = split_path[-2]
        network = split_path[-3]
        year = split_path[-4]
        obs = split_path[-5]
        net, created = Network.objects.get_or_create(name=network)
        if created:
            monitoring.networks.add(net)
            monitoring.save()
        sta, created = Station.objects.get_or_create(network=net, name=station)
        if created:
            monitoring.stations.add(sta)
            monitoring.save()
        mseedfpattern = '%s.%s.??.%s.D.%s.???' % (network, station, channel, year)
        for mseedfile in glob(os.path.join(channelpath, mseedfpattern)):
            if isempty(mseedfile):
                # logging.warning(mseedfile)
                # logging.warning('file is empty')
                continue

            print("basename : ",os.path.basename(mseedfile))

            location = os.path.basename(mseedfile).split('.')[3]
            nslc = '{0}.{1}.{2}.{3}'.format(network, station, location, channel)
            jday = mseedfile.split(".")[-1]
            key = '%s.%s.%s.%s.%s.%s' %(year, network, station, location, channel, jday)
            modif_time = os.path.getmtime(mseedfile)

            if DataFile.objects.filter(key=key, filename=mseedfile).count() == 1:
                datafile = DataFile.objects.get(
                                    key=key, filename=mseedfile)
                datafile.modif_time = modif_time
                datafile.save()
            else:
                datafile = DataFile(key=key, filename=mseedfile,modif_time=modif_time)
                datafile.save()
            with warnings.catch_warnings(record=True) as w:
                try:
                    if not Stat.objects.filter(archive_name=archive,
                                                datafile=datafile).exists():
                        # si fichier a été mis à jour il faut le "relire" --> UPDATE FLAG
                        # print("Insert %s in database" %mseedfile)
                        st = obspy.read(mseedfile)

                        # status = UpdateStatStatus(status="Insert %s in database" %mseedfile)
                        # status.save()
                        # print("status in if ", status)
                    else:
                        # print('already in DB : ',Stat.objects.filter(archive_name=archive, filename=mseedfile))
                        continue
                except (TypeError, IndexError) as err:
                    # logging.warning(mseedfile)
                    logger.error(err)
                    # progress_recorder.set_progress(i + 1, len(channelpaths))
                    # i += 1
                    continue
                # if len(w) > 0:
                #     print("len w > 0")
                #     continue
                    # logging.warning(mseedfile)
                    # logging.warning(w[-1].message)

            ss0 = st[0].stats
            ss1 = st[-1].stats
            comp = os.path.basename(mseedfile).split('.')[3][0:2]

            # A MODIF
            if ss0.station not in sta_list:
                continue

            net = ss0.network
            sta = ss0.station
            loc = ss0.location
            chan = ss0.channel
            jday = str(ss0.starttime._get_julday())
            year = str(ss0.starttime._get_year())
            day_start = datetime.strptime(year+jday, '%Y%j')
            day_end = day_start + timedelta(days=1)
            starttime = ss0.starttime.datetime
            endtime = ss1.endtime.datetime

            day = ss0.starttime.datetime.date()
            year = day.strftime('%Y')

            stats, created = Stat.objects.get_or_create(
                           archive_name=archive, datafile=datafile, comp=comp,
                           net=net,sta=sta,loc=loc,chan=chan, day=day,
                           year=year, starttime=starttime, endtime=endtime,
                           )
            stats.datafile.modif_time = modif_time
            # stats.save()

            # if stats.datafile.modif_time != modif_time:
            #     # file has changed, we need to update statistics
            #     stats.delete()
            #     stats = Stat(archive_name=archive, datafile=datafile,
            #                   comp=comp, sta=sta, net=net, chan=chan,
            #                   loc=loc)


            new_path, created = ChanPath.objects.get_or_create(
                              archive=archive, net=net, sta=sta,
                              loc=loc, chan=chan)
            new_comp_path, created = CompPath.objects.get_or_create(
                                   archive=archive, net=net,
                                   sta=sta, loc=loc, comp=comp)

            # if not ChanPath.objects.filter(archive=archive, net=net, sta=sta,
            #                                 loc=loc, chan=chan).exists():
            #     if monitoring.stations.get(network__name=net, name=sta).view_status=="MonitoringEnabled":
            #         path = ChanPath(archive=archive, net=net, sta=sta, loc=loc,
            #                          chan=chan)
            #         path.save()
            #     else:
            #         ChanPath.objects.filter(archive=archive, net=net, sta=sta,
            #                                  loc=loc, chan=chan).delete()
            #
            # if not CompPath.objects.filter(archive=archive, net=net, sta=sta,
            #                                 loc=loc, comp=comp).exists():
            #     if monitoring.stations.get(network__name=net, name=sta).view_status=="MonitoringEnabled":
            #         path = CompPath(archive=archive, net=net, sta=sta, loc=loc,
            #                          comp=comp)
            #         path.save()
            #     else:
            #         CompPath.objects.filter(archive=archive, sta=sta, net=net,
            #                                  loc=loc, comp=comp).delete()

            gaps_overlaps = st.get_gaps()
            # Store file modification time, to check if mseedfile has changed
            # stats.modif_time = os.path.getmtime(mseedfile)
            # stats.datafile = datafile
            # stats.starttime = ss0.starttime.datetime #timezone.make_aware(ss0.starttime.datetime)
            # stats.endtime = ss1.endtime.datetime #timezone.make_aware(ss1.endtime.datetime)
            # .strftime('%Y-%m-%d %H:%M:%S')
            # stats.save()
            gaps = [g for g in gaps_overlaps if g[6] > 0]
            gapspan = sum(g[6] for g in gaps)

            n_edges_gaps=0
            if starttime > day_start:
                span = starttime - day_start
                gapspan += span.total_seconds()
                n_edges_gaps += 1
            if endtime < day_end:
                span = day_end - endtime
                gapspan += span.total_seconds()
                n_edges_gaps += 1

            # for g in gaps:
            #     gap = Gap(station = ss0.station, network = ss0.network,
            #                channel = ss0.channel, location = ss0.location)
            #     gap.starttime = timezone.make_aware(g[4].datetime)
            #     gap.endtime = timezone.make_aware(g[5].datetime)
            #
            #     gap.status = "new"
                # gap.save()

            overlaps = [o for o in gaps_overlaps if o[6] < 0]
            overlapspan = sum(o[6] for o in overlaps)

            # for o in overlaps:
            #     overlap = Overlap(station = ss0.station, network = ss0.network,
            #                        channel = ss0.channel, location = ss0.location)
            #     overlap.starttime = timezone.make_aware(o[4].datetime)
            #     overlap.endtime = timezone.make_aware(o[5].datetime)
            #     overlap.leap_second = False
                # overlap.save()
            stats.ngaps = len(gaps) + n_edges_gaps
            stats.noverlaps = len(overlaps)
            stats.timestamp = ss0.starttime.strftime('%s')
            stats.gap_span = int(float(gapspan)/60)
            stats.overlap_span = -int(float(overlapspan/60))


            stats.save()

        loop_count += 1
        progress_recorder.set_progress(loop_count, len(channelpaths))
    # status = UpdateStatStatus(status="All channel statistics updated")
    # status.save()





def browse_sds(monitoring):


    archive = monitoring.archive
    start_year = monitoring.start_year
    end_year = monitoring.end_year
    years = range(int(start_year),int(end_year)+1,1)
    paths = [glob(os.path.join(archive, str(_year), '*')) for _year in years]
    # ...and flatten it
    paths = [p for l in paths for p in l]
    # Create list of stationpaths...
    # ('*' is station name)
    stationpaths = [glob(os.path.join(p, '*')) for p in paths]
    # ...and flatten it
    stationpaths = [sp for l in stationpaths for sp in l]
    # Create list of channelpaths...
    # ('???.?' is channel name)
    channelpaths = [glob(os.path.join(sp, '???.?')) for sp in stationpaths]


    # ...and flatten it

    return [cp for l in channelpaths for cp in l]


def update_components(components_list, others_list, disabled_list, monitoring):
    """
    This method updates the "view_status" field of the components

    The view_status field can be modified by the users in order to classify if
    they want to disable some components from the graphical interface that they
    don't want to monitor, or to group some components in an "Others" field
    (for example thermal and pressure sensors)

    PARAMETERS:
    components_list : list of components we want to display as is
    others_list : list of components we want to group as "others"
    disabled_list : list of components we don't want to display

    monitoring : a Monitoring instance, which contains all the components of our
    system

    RETURNS:
    Boolean : True if an update has been made to one or more "view_status" field
              False if no changes has been made


    """
    monitoring_comp = [comp.name for comp in monitoring.components.filter(view_status="Component") ]
    monitoring_others = [comp.name for comp in monitoring.components.filter(view_status="Other") ]
    monitoring_disabled = [comp.name for comp in monitoring.components.filter(view_status="Disabled") ]
    if (components_list != monitoring_comp or
        others_list != monitoring_others or
        disabled_list != monitoring_disabled):
        for comp in monitoring.components.all():
            if comp.name in components_list:
                comp.view_status = "Component"
                comp.save()
            elif comp.name in others_list:
                comp.view_status = "Other"
                comp.save()
            elif comp.name in disabled_list:
                comp.view_status = "Disabled"
                comp.save()
        return True
    else:
        return False

def update_stations(enabled_monitoring, disabled_monitoring, monitoring):
    """
    This method updates the "view_status" field of the stations

    The view_status field can be modified by the users in order to classify if
    they want to disable the monitoring of some stations from the graphical
    interface that they don't want to monitor

    PARAMETERS:
    enabled_monitoring : list of stations we want to display as is
    disabled_monitoring : list of stations we don't want to monitor

    monitoring : a Monitoring instance, which contains all the components of our
    system

    RETURNS:
    Boolean : True if an update has been made to one or more "view_status" field
              False if no changes has been made


    """
    monitoring_mon_en = [sta.name for sta in monitoring.stations.filter(view_status="MonitoringEnabled") ]
    monitoring_mon_dis = [sta.name for sta in monitoring.stations.filter(view_status="MonitoringDisabled") ]
    if (enabled_monitoring != monitoring_mon_en or
        disabled_monitoring != monitoring_mon_dis):
        for sta in monitoring.stations.all():
            if sta.name in enabled_monitoring:
                sta.view_status = "MonitoringEnabled"
                sta.save()
            elif sta.name in disabled_monitoring:
                sta.view_status = "MonitoringDisabled"
                sta.save()
        return True
    else:
        return False


def clean_db():
    Stat.objects.all().delete()
    # for stats in Stat.objects.all():
    #     stats.av_new = False # we can compute average on all statistics again.
    AverageStat.objects.all().delete()
    AverageCompStat.objects.all().delete()


def update_db():
    get_stats()
    average_stats()
