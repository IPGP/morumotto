# -*- coding: utf-8 -*-
import os
import logging
import tempfile
import shutil
import itertools
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from django.utils.crypto import get_random_string
import siqaco.toolbox as toolbox
from .models import Postfile, SourceAvailability, SourceAvailabilityStat, \
    Request, NSLC, Gap, DataFile



logger = logging.getLogger('Stack')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR/")

class FakeProgress():
    def set_progress(self, start, end):
        return


def add_to_postfile(filename, nslc, starttime, endtime):
    """
    Append to a postfile located by 'filename' a line containing the data we
    want to collect, for a given NSLC, starttime and endtime

    filename : `str`
                The name of the postfile we want to edit
    nscl : `str`
           The Network/Station/Location/Channel code.
           Can contain ? and * wildcards (not recommanded)
           For example : RA.*.H??.00
    starttime : `datetime.datetime`
                A starting time to collect data
    endtime : `datetime.datetime`
              An ending time to collect data

    Returns 0 in case of success
    """
    n,s,l,c = nslc.split('.')
    start = starttime.strftime("%Y-%m-%dT%H:%M:%S")
    end = endtime.strftime("%Y-%m-%dT%H:%M:%S")
    request = "%s %s %s %s %s %s \n" %(n,s,l,c,start,end)

    if toolbox.isempty(filename):
        match = []
    else:
        match = [line for line in open(filename).read() if request in line]

    try:
        if not match:
            postfile = open(filename, 'a')
            postfile.write(request)
            postfile.close()
        return 0
    except (OSError) as err:
        return err


# def compute_diff(gap_starttime, gap_endtime, availability):
#     """
#     ARGS :
#
#     gap_starttime: `datetime.datetime field`
#                     Datetime of the starting of the gap
#
#     gap_endtime :  `datetime.datetime field`
#                     Datetime of the ending of the gap
#
#
#     availability : `seismicarchive.models.SourceAvailability` objects
#                     Must contain segments where the starttime is only greater
#                     or equal to the gap starttime and endtime is only lower
#                     or equal to the gap endtime.
#
#     RETURNS:
#
#     gap_diff :     `list of datetime tuples`
#                    A list of tuples which are (starttime, endtime), each
#                    corresponding to a time segment where data was not available
#                    in between the beginning and the end of our gap.
#                    Of course, if all data was available for our gap, this method
#                    will return []
#
#
#     This method will compute the difference between the availability of a source
#     and a given gap. It works like this :
#
#     We make a list out of all the tuples (segment.start, segment.end) for each
#     segment contained in availability, one segment being a time where the data
#     is available
#
#     So we have this list [seg1start, seg1end, ... , segNstart,segNend].
#     Then, if the first segment starttime is lower or equal to our gap start, we
#     remove it from our list, and on the opposite, if they are different, we add
#     the gap start to our list. We do the same with the last segment endtime if
#     it is greater or equal to the gap ending time.
#
#     Then we have :
#     [gapstart, seg1start, seg1end, ..., segNstart, segNend,gapend]
#     OR
#     [seg1end, ..., segNstart] (for example...)
#
#     We now create tuples out of two following items in the list (zip function),
#     and store them in the gap_diff list, which will be either :
#     [(gapstart,seg1start),(seg1end,seg2start),...,(segN-1end,segNstart),
#     (segNend,gapend)]
#     OR
#     [(seg1end,seg2start),...,(segN-1end,segNstart)] (for example...)
#
#     This list corresponds to the remaining gaps after uploading from the
#     inventory
#
#     """
#     availability_list = []
#     for segment in availability:
#         if segment.starttime > gap_starttime:
#             availability_list.append(gap_starttime)
#             availability_list.append(segment.starttime)
#         if segment.endtime < gap_endtime:
#             availability_list.append(segment.endtime)
#             availability_list.append(gap_endtime)
#
#     start_list = availability_list[::2]
#     end_list = availability_list[1::2]
#     return list(zip(start_list,end_list))


# def build_wildcard_string(config, sta):
#     """
#     Method that creates a string to get MUX data for a given station, according
#     to its channels and loc_id
#     """
#     loc_list = [nslc.loc for nslc in
#                 config.nslc.filter(net=sta.network, sta=sta)]
#     chan_list = [nslc.chan for nslc in
#                  config.nslc.filter(net=sta.network, sta=sta)]
#     if len(loc_list) > 1:
#         loc_wc = "*"
#     else:
#         loc_wc = "??"
#     if len(chan_list) > 1:
#         chan_wc = "*"
#     else:
#         chan_wc = "???"
#     return "%s.%s.%s.%s" %(sta.network.name, sta.name, loc_wc, chan_wc)


def update_availability(source, filename, dataformat):
    """
    This method reads a file in filename which has been downloaded by the source
    "source", get it's start, end, gaps, and updates the corresponding
    SourceAvailability and SourceAvailabilityStats in the database
    """

    stream = dataformat.read(filename)
    gaps, overlaps = dataformat.get_stats(stream)
    stream_start = stream[0].stats.starttime.datetime
    stream_end = stream[-1].stats.endtime.datetime
    day = stream[0].stats.starttime.datetime.date()
    nslc = NSLC.objects.get(net__name=stream[0].stats.network,
                            sta__name=stream[0].stats.station,
                            loc__name=stream[0].stats.location,
                            chan__name=stream[0].stats.channel)
    # We want to update all availability segments that covers the stream we read
    source_avail = SourceAvailability.objects.filter(
                 starttime__lte=stream_end,
                 endtime__gte=stream_start,
                 source=source,
                 nslc=nslc).order_by('-endtime')

    if source_avail.exists():
        # Fill a list containing all data segments: even indexes are starttime
        # of data segments, odd indexes are endtimes of data segments
        segment = list()
        data_avail = list()
        # Copy the availability start and end
        avail_start = source_avail.first().starttime
        avail_end = source_avail.last().endtime

        # If the stream begins after the starting of the availability segment
        # we keep the availability segment
        if avail_start < stream_start:
            segment.append(avail_start)
            segment.append(stream_start)

        # Then between each gap we add segments of data
        segment.append(stream_start)
        for g in gaps:
            gap_start = g[4].datetime
            segment.append(gap_start)
            gap_end = g[5].datetime
            segment.append(gap_end)
        segment.append(stream_end)

        # If the stream end before the ending of the availability segment
        # we keep the availability segment
        if stream_end < avail_end:
            segment.append(avail_start)
            segment.append(stream_start)

        source_avail.delete()

        # See seismicarchive.stats to see how this works
        start_times = segment[::2]
        end_times = segment[1::2]
        intersection = Counter(start_times) & Counter(end_times)
        multiset_start_without_common = Counter(start_times) - intersection
        multiset_end_without_common = Counter(end_times) - intersection

        # recreate list with the indexes
        start_list = list(multiset_start_without_common.elements())
        end_list = list(multiset_end_without_common.elements())
        for starttime, endtime in list(zip(start_list,end_list)):
            avail, created = SourceAvailability.objects.get_or_create(
                           starttime=starttime,
                           endtime=endtime,
                           source=source,
                           nslc=nslc)

            # Updating statistics
            data_avail.append((endtime - starttime).seconds)
        stats ,created = SourceAvailabilityStat.objects.get_or_create(
                       day=day, source=source, nslc=nslc)
        if created:
            stats.data_avail = sum(data_avail)
        else:
            stats.data_avail = (avail_end - avail_start).total_seconds() + sum(data_avail)
        stats.save()

def update_postfiles(postfile, data_filename, data_format):
    """
    Method which reads a data file, and update the corresponding postfile in
    order not to re-ask for data already downloaded from other sources
    """
    # 1) lire filename -> ranger dans segments par nslc
    # 2) remplacer ligne par inverse de segment


    pass


def merge_mux_gaps(gap_list):
    """
    Method which read gap_list and merges together gaps for multiplexed
    stations
    """

    # Create a list only containing multiplexed station's gaps
    gap_id = list()

    # for each gap in this list, find other channels's gap that corresponds
    mux_gap_list = gap_list.filter(nslc__sta__multiplexing=True)
    for gap in mux_gap_list:
        mux_gap = mux_gap_list.filter(nslc__net=gap.nslc.net,
                         nslc__sta=gap.nslc.sta,
                         starttime__lte=gap.endtime,
                         endtime__gte=gap.starttime)
        final_gap = mux_gap.first()
        # Update this gap's starttime and endtime to encompass all gaps in
        # mux_gap_filtered
        final_gap.starttime = min([g.starttime for g in mux_gap])
        final_gap.endtime = max([g.endtime for g in mux_gap])
        # Get the gap's unique id to delete it from the gap_list
        gap_id.append(gap.pk)
        # And keep only the first one
        if final_gap.pk in gap_id: gap_id.remove(final_gap.pk)
    # Remove other gaps:
    # gap_list.filter(id__in=gap_id).delete()


    return gap_list.exclude(id__in=gap_id)


# def merge_gaps(gap_list, config):
#     """
#     Method which merges gaps together if the number of gaps is higher than
#     threshold
#
#     Inputs :
#
#         config : a seismicarchive.Configuration object
#         gap_list : list of `seismicarchive.Gap` objects
#
#     """
#     gap_ids = [g.id for g in gap_list]
#     file_list = list()
#
#     nslc_list = [g.nslc for g in gap_list]
#
#     for nslc in nslc_list:
#         if gap_list.filter(nslc=nslc).count() > config.max_gaps:
#             for g in gap_list.filter(nslc=nslc):
#                 file_list.append(g.files)
#                 gap_ids.pop(g.id)
#             starttime = gap_list.filter(nslc=
#                       nslc).order_by("starttime").first().starttime
#             endtime = gap_list.filter(nslc=
#                     nslc).order_by(-"endtime").first().endtime
#             new_gap = Gap.object.create(nslc=nslc,
#                                         status="new",
#                                         starttime=starttime,
#                                         endtime=endtime,
#                                         archive=config.archive)
#             files = [item for sublist in file_list for item in sublist]
#             for file in files:
#                 new_gap.files.add(file)
#                 new_gap.save()
#             gap_ids.append(new_gap.id)
#     return Gap.objects.filter(id__in=gap_ids)



def create_requests(config, gap_list, source_list=None):
    """
    This method creates requests for all gaps in gap_list

    Input :
        config : a seismicarchive.Configuration object
        gap_list : list of `seismicarchive.Gap` objects
        source_list : forcing the source we want to read, if None (default),
                      request will ask all sources defined for the NSLC
                      according to the configuration

    """

    if config.request_lifespan_type == "n":
        timeout = 0
    elif config.request_lifespan_type == "p":
        timeout = (datetime.now() + timedelta(hours=config.request_lifespan))
    gaps = merge_mux_gaps(gap_list)
    for gap in gaps:
        gap_start = gap.starttime
        gap_end = gap.endtime
        request, created = Request.objects.get_or_create(
                         gap=gap, status="new",
                         timeout=timeout,
                         starttime=gap_start,
                         endtime=gap_end,
                         workspace=WORKING_DIR)

        if not created:
            continue
        request.tempdir = tempfile.mkdtemp(
                        dir=os.path.join(WORKING_DIR,"PATCH/"),
                        prefix="%s_" %request.pk)
        request.save()
        nslc = gap.nslc
        if source_list==None:
            source_list = config.sources.filter(nslc__code=nslc)

        for source in source_list.order_by("priority"):
            if not source.is_online:
                logger.warning("%s is offline, not included in the request"
                               %source.name)
            else:
                if gap.nslc.sta.multiplexing and not created:
                    filename = request.postfile.first().filename
                else:
                    filename = os.path.join( WORKING_DIR, "POST",
                                            "post.request.%s.txt"
                                            %(get_random_string(length=16)))
                postfile, created = Postfile.objects.get_or_create(
                                  source=source, filename=filename)

                availability = SourceAvailability.objects.filter(
                             source=source,
                             starttime__lte=gap_end,
                             endtime__gte=gap_start,
                             nslc=nslc).order_by("starttime")

                # 'add' doesn't duplicate relation if it already exists
                request.postfile.add(postfile)
                request.save()

                if availability:
                    if gap.nslc.sta.multiplexing:
                        add_to_postfile(filename,
                                        "%s.%s.%s.%s"
                                        %(gap.nslc.sta.network.name,
                                          gap.nslc.sta.name,"*","*"),
                                        # build_wildcard_string(config,gap.nslc.sta),
                                        gap_start - timedelta(seconds=1),
                                        gap_end + timedelta(seconds=1))
                    else:
                        add_to_postfile(filename, nslc.code,
                                        gap_start - timedelta(seconds=1),
                                        gap_end + timedelta(seconds=1))


def execute_stack(config, progress_recorder=FakeProgress()):
    requests = Request.objects.filter(status__in=["new", "retry"])
    loop_count = 0
    archive = config.archive
    data_struct = config.struct_type
    data_format = config.data_format
    dataformat = config.get_data_format()
    max_gaps = config.max_gaps_by_analysis
    blocksize = config.blocksize
    compression = config.compression_format.upper()
    quality = config.quality_label.upper()
    for request in requests:
        progress_recorder.set_progress(loop_count, len(requests))
        loop_count += 1
        request.status = "in_progress"
        request.save()
        tempdir = request.tempdir
        # if request directory is not empty, we empty it
        if os.path.exists(tempdir):
            if len(os.listdir(tempdir) ) != 0:
                shutil.rmtree(request.tempdir)
        temp_log = os.path.join(tempdir, "log.txt")
        try:
            request.gap.status = "in_process"
            request.gap.save()
        except:
            logger.exception("No gap found for request %s. Deleting request"
                             %(request.pk))
            request.delete()
            continue
        if request.gap.nslc.sta.multiplexing:
            gap_queryset = Gap.objects.filter(
                         archive=archive,
                         nslc__net=request.gap.nslc.net,
                         nslc__sta=request.gap.nslc.sta,
                         starttime__gte=request.starttime,
                         endtime__lte=request.endtime
                         )
            gap_files = DataFile.objects.filter(gap__in=gap_queryset)
        else:
            gap_files = request.gap.files.all()
        patch_files = list()
        try:
            for postfile in request.postfile.all():
                # One postfile = 1 source
                logger.info("executing %s" %postfile.filename)
                source = postfile.source
                tempdir_source = os.path.join(tempdir, source.name.upper())
                if not os.path.exists(tempdir_source):
                    os.makedirs(tempdir_source)

                plugin = source.get_plugin()
                parameters = source.parameters
                limit_rate = source.limit_rate
                verbose = source.log_level
                connect_infos = plugin.set_connect_infos(parameters,limit_rate)

                r = plugin.read(postfile.filename, tempdir_source, data_format,
                                blocksize, compression, connect_infos, temp_log,
                                verbose)
                # If the plugin fetches data, it will return 0
                if r != 0:
                    logger.warning("No data for %s" %postfile)
                    continue
                for path, subdirs, files in os.walk(tempdir_source):
                    for name in files:
                        # If source availability is selected, update data avail
                        if source.availability:
                            update_availability(source,
                                                os.path.join(path, name),
                                                dataformat)
                        # update_postfile(postfile,
                        #                 os.path.join(path, name),
                        #                 dataformat)
                        # Create the patch files list
                        patch_files.append(os.path.join(path, name))

            # End of postfile for loop
            # Set patch for the given gap(s)
            patched_files = dataformat.set_patch(tempdir, gap_files,
                          patch_files, request.starttime, request.endtime,
                          quality, temp_log)
            dataformat.merge_to_final(gap_files, patched_files,tempdir,archive)
            request.status = "succeeded"
            request.save()
            request.gap.status = "archived"
            # if request.gap.nslc.sta.multiplexing:
            #     gap_queryset.delete()
            # else:
            #     request.gap.delete()
            if not config.debug_mode:
                request.delete()

        except:
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


def clean(config, log):
    # this function reads the stack when process is finished
    # check status of each remaining request
    # if status is succedded or cancelled --> archive it
    # if status is new, retry or on_hold : user choice
    # if status = failed replaces it on top of stack with status = retry
    # if status = failed and lifespan is over, status = on_hold
    for request in Request.objects.filter(status="succeeded"):
        try:
            for post in request.postfile.all():
                # print("post.filename",post.filename)
                os.remove(post.filename)
            request.postfile.all().delete()
            request.gap.delete()
            request.delete()
        except:
            logger.exception("Can't delete request %s and gap %s"
                             %(request.gap.id, request.id))
