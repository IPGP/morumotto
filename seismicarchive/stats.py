# -*- coding: utf-8 -*-
import os
import logging
import warnings
from datetime import datetime, timedelta
from collections import defaultdict, Counter
# from django.utils import timezone
from .models import Gap, Overlap, DataFile, NSLC
import plugins.structure as struct
import plugins.format as format
import siqaco.toolbox as toolbox

logger = logging.getLogger('Stats')
class FakeProgress():
    def set_progress(self, start, end):
        return


def get_datafiles(nslc,window_starttime,window_endtime):
    n,s,l,c = nslc.code.split(".")
    file_list = []
    if datetime.date(window_starttime) < datetime.date(window_endtime):
        for day in toolbox.daterange(window_starttime,window_endtime):
            year = day.strftime("%Y")
            jday = day.strftime("%j")
            key = "%s.%s.%s.%s.%s.%s" %(year,n,s,l,c,jday)
            if DataFile.objects.filter(key=key).exists():
                file_list.append(DataFile.objects.get(key=key))
    else:
        year = window_starttime.strftime("%Y")
        jday = window_starttime.strftime("%j")
        key = "%s.%s.%s.%s.%s.%s" %(year,n,s,l,c,jday)
        if DataFile.objects.filter(key=key).count():
            file_list.append(DataFile.objects.get(key=key))
    return file_list


def get_datafile(key,filename):
    if toolbox.isempty(filename):
        # logger.warning("In stats.get_datafile : file %s not found"
        #              %filename)
        return DataFile.objects.none()

    files = DataFile.objects.filter(key=key,filename=filename)
    if files.count() == 1:
        return DataFile.objects.get(key=key,filename=filename)

    else:
        if files.count() > 1:
            logger.warning("More than one Datafile exists for %s, %s\n"
                           "Datafiles will be removed and a new one created."
                           %(key, filename))
            for file in files:
                file.delete()
        now = datetime.utcnow()
        return DataFile.objects.create(key=key,filename=filename,
                                       modif_time=datetime.timestamp(now))


def get_gapsoverlaps(archive, nslc_list, data_format, data_structure, max_gaps,
                     window_starttime, window_endtime,
                     progress_recorder=FakeProgress()):
    """
    This method computes all statistics of the final archive for a given time
    lapse.

    Arguments :

    data_format  `str`
                 The format of the data. See plugins/format.py
    data_structure  `str`
                 The format of the structure. See plugins/structure.py
    max_gaps     `int`
                 threshold above which we merge gaps to fetch data only from
                 the starttime of the first gap to the end of the last gap
    window_starttime    `datetime`
                 starttime for the analysis window
    window_endtime      `datetime`
                 endtime for the analysis window

    Returns
    datafile_list  `list`
                 The list of all datafiles that have been analyzed

    """
    loop_count = 0
    file_list = data_structure.get_filelist(
              archive, nslc_list,
              window_starttime,
              window_endtime)

    stream_gaps = defaultdict(list)
    stream_full = defaultdict(lambda: defaultdict(bool))
    first_stream_start = defaultdict(datetime)
    last_stream_end = defaultdict(datetime)
    # logger.info("Updating statistics for %s" %nslc_list)
    logger.info("Updating Gaps / Overlaps statistics")
    # Reading gaps and overlaps from files
    for key, filename in file_list.items():
        # If file doesn't exists, skip this loop and continue to next file
        progress_recorder.set_progress(loop_count, len(file_list))
        loop_count += 1
        datafile = get_datafile(key=key, filename=filename)
        if not datafile:
            continue

        nslc = ".".join(key.split(".")[1:5])
        modif_time = os.path.getmtime(filename)
        try:
            # if modif_time != datafile.modif_time:
            #     # if the file has been changed since last
            #     get_gapsoverlaps(), we update the statistics
            # logger.info("Updating statistics for %s" % filename)
            # Storefile modification time
            # datafile.modif_time = modif_time
            # datafile.save()

            stream = data_format.read(filename)#,window_starttime,window_endtime)
            # else:
            #     continue
        except (TypeError, IndexError) as err:
            logger.exception("error", err)
            continue

        ss0 = stream[0].stats
        ss1 = stream[-1].stats
        stream_start = ss0.starttime.datetime #timezone.make_aware(ss0.starttime.datetime)
        stream_end = ss1.endtime.datetime #timezone.make_aware(ss1.endtime.datetime)
        sampling_rate = ss0.sampling_rate
        datafile.stream_starttime = stream_start
        datafile.stream_endtime = stream_end
        datafile.save()
        day_start = datetime(stream_start.year,
                             stream_start.month,
                             stream_start.day)
        day_end = day_start + timedelta(days=1)
        if not first_stream_start.get(nslc):
            first_stream_start[nslc] = stream_start
        else:
            if stream_start < first_stream_start[nslc]:
                first_stream_start[nslc] = stream_start
        if not last_stream_end.get(nslc):
            last_stream_end[nslc] = stream_end
        else:
            if stream_end > last_stream_end[nslc]:
                last_stream_end[nslc] = stream_end

        # if stream starts after day_start
        if ((stream_start - day_start).total_seconds() >
            float(1 / sampling_rate)):
            # stream_gaps[nslc].append(window_starttime)
            stream_gaps[nslc].append(day_start)
            stream_gaps[nslc].append(stream_start)

        # Now we add all gaps read in the datafile

        gaps, overlaps = data_format.get_stats(stream)
        if len(gaps) > max_gaps:
            # max_gaps is defined in the configuration as the threshold over
            # which we consider only 1 big gap instead of several small ones
            # This gap goes from the beginning of the first gap to the end of the
            # last gap
            gap_start = gaps[0][4].datetime
            gap_end = gaps[-1][5].datetime
            # Fixing problem if we have more than max_gaps and stream start or
            # end outside the gaps

            # if stream_start > day_start:
            if ((stream_start - day_start).total_seconds() >
                float(1 / sampling_rate)):
                stream_gaps[nslc].append(stream_start)
                stream_gaps[nslc].append(gap_start)


            stream_gaps[nslc].append(gap_start)
            stream_gaps[nslc].append(gap_end)

            # if day_end > stream_end:
            if ((day_end - stream_end).total_seconds() >
                float(1 / sampling_rate)):

                stream_gaps[nslc].append(gap_end)
                stream_gaps[nslc].append(stream_end)
        else:
            for g in gaps:
                gap_start = g[4].datetime
                gap_end = g[5].datetime

                stream_gaps[nslc].append(gap_start)
                stream_gaps[nslc].append(gap_end)

        if ((day_end - stream_end).total_seconds() >
            float(1 / sampling_rate)):

            stream_gaps[nslc].append(stream_end)
            stream_gaps[nslc].append(day_end)



        for o in overlaps:
            overlap, created = Overlap.objects.get_or_create(
                             archive=archive, nslc=nslc,
                             starttime=o[4].datetime,
                             endtime=o[5].datetime)

    for nslc in nslc_list:
        if first_stream_start.get(nslc.code) and stream_gaps.get(nslc.code):
            if ((first_stream_start[nslc.code] - window_starttime).total_seconds() >
                float(1/sampling_rate)):
                # First stream starts after window starttime
                if ((first_stream_start[nslc.code] -
                    stream_gaps[nslc.code][0]).total_seconds() >
                    float(1/sampling_rate)):
                    # First gap begins after window start
                    # -> update first stream_gap, changing with window start
                    stream_gaps[nslc.code][0] = window_starttime
                else:
                    stream_gaps[nslc.code].insert(0,window_starttime)
                    stream_gaps[nslc.code].insert(1,first_stream_start[nslc.code])

        # Repeat with last segment
        if last_stream_end.get(nslc.code) and stream_gaps.get(nslc.code):
            if ((window_endtime - last_stream_end[nslc.code]).total_seconds() >
                float(1/sampling_rate)):
                # Last stream ends before window endtime
                if ((stream_gaps[nslc.code][-1]
                    - last_stream_end[nslc.code]).total_seconds() >
                    float(1/sampling_rate)):
                    # update last stream_gap, changing with window end
                    stream_gaps[nslc.code][-1] = window_endtime
                else:
                    stream_gaps[nslc.code].append(last_stream_end[nslc.code])
                    stream_gaps[nslc.code].append(window_endtime)


    for nslc in nslc_list:
        if not stream_gaps.get(nslc.code):
            # no stream found at all :
            stream_gaps[nslc.code].append(window_starttime)
            stream_gaps[nslc.code].append(window_endtime)

        # 1) Check that stream_gaps and stream_overlaps are OK
        if len(stream_gaps[nslc.code]) % 2 != 0:
            logger.error("Reading stats for %s failed " %nslc )
            continue

        # 2) We unpack the stream_gaps list and create gaps in the database
        #    i) even index values are all starting times
        start_times = stream_gaps[nslc.code][::2]
        #    ii) odd index values are all ending times
        end_times = stream_gaps[nslc.code][1::2]

        #   iii) if we have some gap ending on the next gap starttime, we
        #        should merge them into one only gap :

        # get intersection of the two lists
        intersection = Counter(start_times) & Counter(end_times)

        # create two indexes of all values that don't contain the
        # intersection values (which are same starttime/endtime.
        # Can happen on file boundaries)
        multiset_start_without_common = Counter(start_times) - intersection
        multiset_end_without_common = Counter(end_times) - intersection

        # recreate list with the indexes
        start_list = list(multiset_start_without_common.elements())
        end_list = list(multiset_end_without_common.elements())

        # Concatenate start and end times into list of tuples
        tuple_list = list(zip(start_list,end_list))

        # 3) Put these gaps into the database
        gap_id = list()
        for starttime, endtime in tuple_list:
            # i) Save gaps in the database
            gap, created = Gap.objects.get_or_create(
                         archive=archive,nslc=nslc,
                         starttime=starttime,
                         endtime=endtime)
            gap_id.append(gap.id)
            # ii) archive previous gaps taht are outside the window

            existing = Gap.objects.filter(archive=archive,nslc=nslc,
                               starttime__lte=endtime,
                               endtime__gte=starttime,
                               status__in=["new","in_process"],
                               ).order_by("-endtime")

            # Keep gaps outside the window
            for g in existing:
                if g.starttime < window_starttime:
                    g.endtime=window_starttime
                    g.save()
                    gap_id.append(g.id)
                if g.endtime > window_endtime:
                    g.starttime = window_endtime
                    g.save()
                    gap_id.append(g.id)

            existing.exclude(id__in=list(set(gap_id))).delete()
            file_list = get_datafiles(nslc,starttime,endtime)
            for file in file_list:
                gap.files.add(file)
            gap.save()

    gap_list = Gap.objects.filter(starttime__lte=window_endtime,
                                  endtime__gte=window_starttime,
                                  status__in=["new","in_process"],
                                  archive=archive)

    overlap_list = Overlap.objects.filter(archive=archive,
                                          starttime__lte=window_endtime,
                                          endtime__gte=window_starttime)
    return gap_list, overlap_list
