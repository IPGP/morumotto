# -*- coding: utf-8 -*-
import os
import shutil
import logging
import morumotto.toolbox as toolbox
from glob import glob
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from django.utils.crypto import get_random_string
from .models import NSLC, SourceAvailability, SourceAvailabilityStat, \
    SourceOnlineStat, Configuration, Gap, Overlap, Request
from . import stats, stack
from monitoring import update_monitoring
from monitoring.models import ArchiveMonitoring
from plugins import structure, format, source
logger = logging.getLogger('Update')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR")

class FakeProgress():
    def set_progress(self, start, end):
        return
def analysis_window(config):
    """
    returns a tuple of datetime (starttime, endtime) for the analysis

    Arguments : config is a archive.models.Config instance
    """

    gran_type = config.granularity_type
    frq = config.f_analysis
    wnd = config.w_analysis
    ltn = config.l_analysis

    now = datetime.utcnow()

    # starttime, endtime = (now,now) #default
    if gran_type == 'daily':
        starttime = datetime(year=now.year, month=now.month, day=now.day,
                             hour=00,minute=00,second=00, microsecond=00
                            )-timedelta(days=(ltn+wnd))
        endtime = starttime + timedelta(days=wnd)

    elif gran_type == 'hourly':
        starttime = datetime(year=now.year, month=now.month, day=now.day,
                                 hour=now.hour,minute=00,second=00,
                                 microsecond=00)-timedelta(hours=(ltn+wnd))
        endtime = starttime + timedelta(hours=wnd)
    return (starttime, endtime)



def create_availability_postfile(filename, nslc_list,
        starttime, endtime, source_name):
    """
    This method will create a postfile to get the availability for an a given
    NSLC, from starttime to endtime, and save it to the workspace direcory

    Arguments:
        filename : `str`
                    full path to the file we write to
        nslc_list : `list of archive.models.NSLC`
                  the nslcs we want to fetch
        starttime : `datetime.datetime`
                    A starting time to collect data
        endtime : `datetime.datetime`
                  An ending time to collect data
        source_name : `str`
                    The name of the source

    Returns:
        filename : `str`
                    path and name of the created postfile

    """
    now = datetime.utcnow()

    start = starttime.strftime("%Y-%m-%dT%H:%M:%S")
    end = endtime.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        postfile = open(filename, 'a')
        postfile.write("mergequality=true\n")
        postfile.write("mergesamplerate=true\n")
        postfile.write("format=text\n")
        for nslc in nslc_list:
            net,sta,loc,chan = nslc.code.split('.')
            postfile.write("%s %s %s %s %s %s\n" %(net,sta,loc,chan,start,end))
        postfile.close()
        return filename
    except (OSError) as err:
        logger.exception(err)


def update_availability(source, nslc_list, availability_file,
        starttime, endtime, debug=False):
    """
    Method which creates or updates a archive.models.SourceAvailability
    object with either the inventory found in the inventory file, or with
    N SourceAvailability objects, N being the number of days between starttime
    and endtime,  which are all startting on midnight and ending on midnight
    for all days between starttime and endtime. If  starttime and endtime are
    the same day, it will just create 1 object, if it doesn't exist yet

    """
    existing = SourceAvailability.objects.filter(
             source=source,
             nslc__in=nslc_list,
             starttime__lte=endtime,
             endtime__gte=starttime)

    # 1) If we disabled availability for the given source (meaning the source
    #    will ask for all data between starttime and endtime):
    if not source.availability:

        # Create availability segments for each day from midnight to midnight
        avail_id = list()
        for date in toolbox.datelist(starttime,endtime):
            seg_start = datetime(year=date.year, month=date.month,
                                 day=date.day,hour=00,minute=00,second=00,
                                 microsecond=00)
            seg_end = seg_start + timedelta(days=1)
            for nslc in nslc_list:
                d_avail, created = SourceAvailability.objects.get_or_create(
                                 source=source, nslc=nslc,
                                 starttime=seg_start, endtime=seg_end)
                avail_id.append(d_avail.id)
        # Remove other availability
        if existing.count():
            existing.exclude(id__in=avail_id).delete()
        return
    else:
        # 2) Read availability file got from plugin, store results in list
        avail_dict = defaultdict(list)
        if not availability_file == None:
            if not toolbox.isempty(availability_file):
                if (os.stat(availability_file).st_size != 0):
                    for line in open(availability_file, 'r'):
                        if line[0] == "#":
                            continue
                        (l_nslc,
                        l_starttime,
                        l_endtime) = source.get_plugin().read_availability(line)
                        avail_dict[l_nslc].append(l_starttime)
                        avail_dict[l_nslc].append(l_endtime)
                    # When the file has been read, we simply delete it
                    try:
                        if not debug:
                            os.remove(availability_file)
                    except:
                        logger.exception("Can't remove %s" %availability_file)


        # 3) Modify existing availability with new starttime and endtime:
        for nslc in nslc_list:
            # If inventory is not available from source
            if availability_file == None:
                avail_dict[nslc.code].append(starttime)
                avail_dict[nslc.code].append(endtime)
            # If availability returned no data
            elif not avail_dict.get(nslc.code):
                continue

            # J'adore faire ça putain
            start_times = avail_dict[nslc.code][::2]
            end_times = avail_dict[nslc.code][1::2]
            tuple_list = list(zip(start_times,end_times))
            avail_id = list()
            for starttime, endtime in tuple_list:
                existing = SourceAvailability.objects.filter(source=source,
                     nslc=nslc, starttime__lte=endtime,
                     endtime__gte=starttime).order_by("starttime")
                # Split boundaries:
                if existing.count():
                    if existing.first().starttime < starttime:
                        avail = SourceAvailability.objects.create(
                              source=source,
                              nslc=nslc,
                              starttime=existing.first().endtime,
                              endtime=starttime)
                        existing.first().endtime = starttime
                        existing.first().save()
                        avail_id.append(avail.id)
                        avail_id.append(existing.first().id)

                    if existing.last().endtime < endtime:
                        avail = SourceAvailability.objects.create(
                              source=source, nslc=nslc,
                              starttime=existing.last().endtime,
                              endtime=endtime)
                        existing.last().endtime = starttime
                        existing.last().save()
                        avail_id.append(avail.id)
                        avail_id.append(existing.last().id)

                new_avail = SourceAvailability(source=source, nslc=nslc,
                                               starttime=starttime,
                                               endtime=endtime)
                avail_id.append(new_avail.id)
                new_avail.save()
                if existing.count():
                    existing.exclude(id__in=avail_id).delete()
                # If the availability was not yet put in the DB, we increase
                # the statistics
                data_avail = (endtime - starttime).seconds
                stats, created = SourceAvailabilityStat.objects.get_or_create(
                               day=starttime.date(),
                               source=source,
                               nslc=nslc)
                if created:
                    stats.data_avail=data_avail
                else:
                    stats.data_avail += data_avail
                stats.save()







def update_source_infos(nslc_list, source_list,
        starttime, endtime, workspace,debug=False):
    """
    This method will update all sources infos for a given nslc
    """
    random_id = get_random_string(length=16)
    log = os.path.join(
        workspace,
        "AVAILABILITY",
        "log.availability_%s.txt" %random_id)# datetime.utcnow().strftime('%Y-%m-%dT%H.%M.%S_%f'))
    for source in source_list.iterator():
        source_nslc = [nslc for nslc in nslc_list if nslc in source.nslc.all()]
        plugin = source.get_plugin()
        parameters = source.parameters
        limit_rate = source.limit_rate
        verbose = source.log_level
        connect_infos = plugin.set_connect_infos(parameters,limit_rate)
        # online = online_to_db(source, log)

        # Online informations
        source.is_online = plugin.is_online(parameters,verbose,log)
        source.save()
        online_stats, created = SourceOnlineStat.objects.get_or_create(
                              source=source, day=datetime.today())
        if not source.is_online:
            online_stats.daily_failure += 1
            online_stats.save()

        # Data Availability
        postfile = os.path.join( workspace, "AVAILABILITY",
                                "post.availability_%s.txt"
                                %(random_id))
        availability_postfile = create_availability_postfile(
                              postfile, source_nslc,
                              starttime, endtime,
                              source.name)
        availability_file = plugin.availability(availability_postfile,
                                             workspace, connect_infos,
                                             log, verbose)
        availability = update_availability(source, source_nslc,
                                           availability_file,
                                           starttime, endtime,debug)



def update(progress_recorder=FakeProgress(), starttime=None, endtime=None):
    monitoring = ArchiveMonitoring.objects.first()
    config = Configuration.objects.first()
    nslc_list = [nslc for nslc in config.nslc.all()]
    source_list = config.sources.all()
    archive = config.archive
    max_gaps = config.max_gaps_by_analysis
    blocksize = config.blocksize
    compression = config.compression_format.upper()
    workspace = WORKING_DIR

    data_format = config.get_data_format()
    data_structure = config.get_data_structure()

    if starttime == None or endtime == None:
        starttime, endtime = analysis_window(config)

    print("Start analysis from %s to %s \n" %(starttime,endtime))
    logger.info("Start analysis from %s to %s \n" %(starttime,endtime))

    # 1) Update all sources informations : is online ? + data availability
    update = update_source_infos(
           nslc_list, source_list,
           starttime, endtime,
           workspace, config.debug_mode)

    # # Get all existing files for the given time window
    # file_list = datastructure.get_filelist(
    #           archive, nslc_list,
    #           starttime, endtime)

    # 2) Compute gaps and overlaps from files and analysis window
    gap_list, overlap_list = stats.get_gapsoverlaps(
                             archive, nslc_list,
                             data_format, data_structure, max_gaps,
                             starttime, endtime,progress_recorder)
    # print(gap_list)
    # 3) Create requests
    stack.create_requests(config, gap_list)
    # 4) Execute Stack
    # stack.execute_request(config,progress_recorder)
    # requests = Request.objects.filter(status__in=["new", "retry"])
    # for req in requests:
    #     result = tasks.execute_stack.delay(req, config)
    #     loop_count += 1
    #     progress_recorder.set_progress(loop_count, len(requests))
    requests_id_list = [request.pk for request in
                        Request.objects.filter(
                        status__in=["new", "retry"])]
    jobs = tasks.execute_stack.chunks(
         config.id, requests_id_list, config.n_request)
    jobs.apply_async()

    # 4. bis clean overlaps... ??

    # 5) Clean stack
    # stack.clean(config, log)
    logger.info("Update archive finished")

    # 6) update statistics -> useless ?
    # updated_gap_list = stats.get_gapsoverlaps(
    #                  archive, nslc_list,
    #                  data_format, data_structure,max_gaps,
    #                  starttime, endtime)

    # 7) Updating monitoring
    update_monitoring.get_stats_from_files(archive, nslc_list, data_format,
                                           data_structure, starttime, endtime,
                                           progress_recorder)
    update_monitoring.average_stats(monitoring)

    logger.info("Monitoring updated")
    # except (TypeError, IndexError) as err:
    #     print("error", err)
    #     return 1




# def update_old(progress_recorder):
#     # Gap.objects.all().delete()
#     # GapList.objects.all().delete()
#
#
#     config = Configuration.objects.first()
#     networks = [net.name for net in config.networks.all()]
#     stations = [sta.name for sta in config.stations.all()]
#     # sources = [source.name for source in configuration.sources.all()]
#     nslc_list = [code.nslc for code in config.nslc.all()]
#
#     data_struct = config.struct_type
#     data_format = config.data_format
#     max_gaps = config.max_gaps_by_analysis
#     blocksize = config.blocksize
#     compression = config.compression_format.upper()
#     workspace = config.working_dir
#     gran_type = config.granularity_type
#     frq = config.f_analysis
#     wnd = config.w_analysis
#     ltn = config.l_analysis
#
#     now = datetime.utcnow()
#
#     startday = datetime(
#                      year=now.year, month=now.month,
#                      day=now.day,hour=now.hour,minute=now.minute,
#                      second=now.second,microsecond=now.microsecond
#                      # hour=00,minute=00,
#                      # second=00
#                      )
#
#     #5 : update stats (gaps and overlaps) and source inventory. If discontinuity outside of timelaps : put its status to "hold"
#
#     starttime = startday - timedelta(days=ltn)
#     # endtime = starttime + timedelta(days=wnd)
#     endtime = starttime + timedelta(hours=wnd)
#
#     sds = structure.SDS()
#     channelpaths = sds.browse(config.archive)
#     # stats.get_gapsoverlaps(starttime,channelpaths)
#     # connect_infos = "parameters:service.iris.edu?limit-rate=100k"
#     connect_infos = "client:ws.ipgp.fr?limit-rate=500k"
#
#
#     # create postfile !! attention si le dossier est crée entre temps : pb
#     if not os.path.exists(os.path.join(workspace,"POST")):
#         os.makedirs(os.path.join(workspace,"POST"))
#
#     postfile = os.path.join(workspace,
#                             "POST",
#                             "postfile"+now.strftime('%s')+".txt")
#
#     if not os.path.exists(os.path.join(workspace,"LOG")):
#         os.makedirs(os.path.join(workspace,"LOG"))
#     log = os.path.join(workspace,
#                             "LOG",
#                             "logfile"+now.strftime('%s')+".txt")
#     starttime = starttime.strftime("%Y-%m-%dT%H:%M:%S")
#     endtime = endtime.strftime("%Y-%m-%dT%H:%M:%S")
#     for nslc in nslc_list:
#         r = add_to_postfile(postfile, nslc, starttime, endtime)
#
#     fdsnws = source.FdsnWS()
#     # r = fdsnws.read(nslc, starttime, endtime, workspace,
#     #             data_struct, data_format, connect_infos)
#     r = fdsnws.read(postfile, workspace, data_format, blocksize,
#                     compression, connect_infos, log)
#
#     # on success, remove the postfile
#     if r==0:
#          os.remove(postfile)
#
#     print("result : ", r)
#


    # for source in Source.objects.all():
    #     avail[source] = source.availability()
    #     if avail:
    #         inv[source] = source.inventory()
    #
    # for g in Stat.gaps_list():
    #     build_request(avail,inv,g.starttime, g.endtime)






        # request:
        # data = source.get_data(g.starttime, g.endtime)
        # process request:
        # merge(final_archive, data)

    # monitoring.average_stats(progress_recorder) #update average stats


    # loop_count = 0
    # if struct_type=="sds":
    #     sds.init_archive(fdsnClient("IRIS"))
    #     progress_recorder.set_progress(loop_count, ltn+wnd+2)
    #     loop_count += 1
    #     channelpaths = sds.browse_archive()
    #     for date in toolbox.daterange(starttime, endtime):
    #         print("date:", date)
    #         stats.get_gapsoverlaps(date,channelpaths)
    #         progress_recorder.set_progress(loop_count, ltn+wnd+2)
    #         loop_count += 1
    #         #second iter : statistics done
    #         for source in sources:
    #             print("source :", source)
    #             if source=='fdsnws':
    #                 fdsn.update(date)
    #                 stats.get_gapsoverlaps(date,channelpaths)
    #             elif source=='rt':
    #                 rt.update()
    #         progress_recorder.set_progress(loop_count, ltn+wnd+2)
    #         loop_count += 1


def clean_db():
    Stat.objects.all().delete()
    AverageStat.objects.all().delete()
    AverageCompStat.objects.all().delete()


def update_db(conf):
    print("config choice : ", conf)
    print("getting statistics from archive")
    update_monitoring.get_stats()
    print("getting average statistics from archive")
    update_monitoring.average_stats()
