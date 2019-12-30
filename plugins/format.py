# -*- coding: utf-8 -*-
import abc
import obspy
import inspect
import sys
import os
import logging
import subprocess
import shutil
import tempfile
from datetime import datetime, timedelta
from glob import glob
from distutils.dir_util import copy_tree
import plugins.structure as structure
import morumotto.toolbox as toolbox
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use('Agg')

logger = logging.getLogger('Status')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCH_DIR =  os.path.join(BASE_DIR, "WORKING_DIR", "PATCH")

def create_listfile(destination, file_list, prefix):
    """
    This method will create a list file from all files in the dir located
    by "channelpath"

    Arguments:
    destination : `str`
                  the path to our destination directory where we write the file list
    file_list : `str`
                 list of path to the files we want to list

    Returns:
    filename : `str`
                    path to the created file containing the list
    """
    if file_list:
        now = datetime.utcnow()
        filename = tempfile.mkstemp(dir=destination, prefix=prefix,
                                    suffix=".list")
        for file in file_list:
            try:
                list = open(filename[1], 'a')
                list.write("%s" %file+"\n")
                list.close()
            except (OSError) as err:
                logger.error(err)
                return err
        return filename[1]
    else:
        return "empty"


class DataFormat():
    """ This abstract class defines the basic methods that need
    to be implemented to use a source plugin

    To create a source plugin, create a file named
    plugins/structures/yoursrouce.py (with "yoursource" being the name of the
    srouce you want to use), and then you will have to create

    - a read function
    - a write Function
    - a get_stats Function
    - a generate_plot function
    - a plot_completion Function
    - a set_patch function
    - a check_diff function
    - a merge_to_final Function

    You can have a look at the other existing plugins to see how to proceed
    """
    @abc.abstractmethod
    def __init__(self):
        self.set_patch_script = os.path.join(
                              BASE_DIR, os.path.join("plugins","set_patch",
                              self.script_name)
                              )
    @abc.abstractmethod
    def read(self, filename, starttime=None, endtime=None):
        pass
    @abc.abstractmethod
    def write(self):
        pass
    @abc.abstractmethod
    def get_stats(self, streamfile):
        pass
    @abc.abstractmethod
    def generate_plot(self, streamfile, plotfilename):
        pass
    @abc.abstractmethod
    def plot_completion(self, nslc, year,plotfilename, archive, struct):
        pass
    @abc.abstractmethod
    def set_patch(self, tempdir, gap_files, patch_files,
                  gap_starttime, gap_endtime, quality, log):
        pass
    @abc.abstractmethod
    def check_diff(self , patched_file, original_file):
        pass
    @abc.abstractmethod
    def merge_to_final(self, gap_files, patched_files, tempdir, final_archive):
        pass


class miniSEED(DataFormat):
    # Don't forget to set the name of the script which must be placed in the
    # plugins/set_patch directory
    script_name = "set_patch_seed.sh"

    def read(self, mseedfile,starttime=None,endtime=None):
        """
        Read a miniseed file and returns an obspy stream
        Must be readable by SEED.get_stats()
        """
        if isinstance(starttime,datetime) and isinstance(endtime,datetime):
            utc_start = toolbox.to_utcdatetime(starttime)
            utc_end = toolbox.to_utcdatetime(endtime)
        else:
            if not (starttime == None or endtime == None):
                logger.warning("Warning: while trying to read %s with miniSEED, "
                               "Starttime/Endtime format must be datetime objects"
                               %mseedfile)
            utc_start=None
            utc_end=None

        return obspy.read(mseedfile,starttime=utc_start,endtime=utc_end)

    def write(self):
        pass

    def get_stats(self, stream):
        """
        Returns a tuple (gaps, overlaps) containing the gaps and overlaps lists
        for a given seed stream
        """

        gaps_overlaps = stream.get_gaps()
        gaps = [g for g in gaps_overlaps if g[6] > 0]
        overlaps = [o for o in gaps_overlaps if o[6] < 0]
        return (gaps, overlaps)


    def generate_plot(self, streamfile, plotfilename):
        """
        Generates a daily plot for a given miniSEED file, and saves it in the
        file defined by plotfilename
        """
        st = obspy.read(streamfile)
        ss0 = st[0].stats

        starttime = ss0.starttime.datetime
        day_start = starttime.replace(hour=00,minute=00,second=00,microsecond=00)
        day_end = day_start + timedelta(days=1)

        try:
            st.plot(outfile=plotfilename,
                    starttime=toolbox.to_utcdatetime(day_start),
                    endtime=toolbox.to_utcdatetime(day_end),
                    color='#007bff',
                    show_y_UTC_label=False)
            extension = plotfilename.split(".")[-1]
            dayplotfilename = plotfilename[:-4] + ".day." + extension
            st.plot(outfile=dayplotfilename, type='dayplot', interval=60,
                    starttime=toolbox.to_utcdatetime(day_start),
                    endtime=toolbox.to_utcdatetime(day_end),
                    one_tick_per_line=True,
                    color=['#007bff', '#fd7e14', '#ffc107', '#28a745'],
                    show_y_UTC_label=False)
        except (TypeError, IndexError) as err:
            logger.error(err)
            return err # if we can't compute plot from stream, we just give an error message
        return True


    def plot_completion(self,nslc,year,plotfilename, archive, struct):
        """
        Method that will plot data completion for a given nslc, to have a
        quick overview over a year
        parameters :

        config : `archive.models.Configuration`
                  config object

        nslc : `str`
                nslc code

        year : `int`
                year to compute completion

        plotfilename : `str`
                      where you want to save your plot

        archive : `str`
                  path to the final archive

        struct: `str`
                your final archive structure type
        """
        script = "obspy-scan"
        net,sta,loc,chan = nslc.split(".")
        if struct == "SDS":
            nslc_dir = os.path.join(archive,year,net,sta)
        elif struct == "CSS":
            nslc_dir = os.path.join(archive,year,"*","*.*.%s:*:*:*:*" %year)
        elif struct == "CDAY":
            nslc_dir = os.path.join(archive,"*.*.*.*.%s:*:#*:#*:#*" %year)
        elif struct == "SDAY":
            nslc_dir = os.path.join(archive,"*.*.%s:*" %year)
        elif struct == "BUD":
            nslc_dir = os.path.join(archive,net,sta,"*.*.*.*.%s.*" %year)
        else:
            logger.error("Structure not implemented yet")
            return "Archive structure unknown"
        arg_list= ['-o{0}'.format(plotfilename),
                   '-f{0}'.format("MSEED"),
                   nslc_dir
                   ]
        try:
            result = subprocess.run([script] + arg_list, stdout=subprocess.PIPE)
            print(str(script + ', '.join(arg_list)))
            # stats = result.stdout.decode('utf-8').splitlines()
            # nslc, start, end, span = stat.split(" ")
            # plt.figure()
            # plt.plot(stats[1],stats[3])
            # plt.grid(True)
            # plt.savefig(plotfilename)
            return True
        except (TypeError, IndexError) as err:
            logger.error(err)
            return err # if we can't compute plot from stream, we just give an error message
        except (FileNotFoundError) as err:
            logger.error(err)
            return err
        # try:
        #     logfile = open(log, 'a')
        #     logfile.write("%s" % result.stdout.decode('utf-8')+"\n")
        #     logfile.close()
        # except (OSError) as err:
        #     logger.error(err))







    def set_patch(self, tempdir, gap_files, patch_files,
            gap_starttime, gap_endtime, quality, log):
        """
        This method will create a file containing all path to the gap files
        and all path to the patch files, then call the set_patch script which
        will merge patch into the gap files

        parameters :

        tempdir : `str`
                    Path to the dir where we have our files

        gap_files : `list`
                    list of files containing a given gap. Usually just one, but
                    can be more

        patch_files : `list`
                    list of files containing the patch data to fill the gaps

        gap_starttime : `datetime.datetime`

        gap_endtime : `datetime.datetime`

        returns list of patched files
        """
        nslc_list = [filename.split(os.sep)[-1] for filename in patch_files]
        for nslc in set(nslc_list):
            gap_files_by_chan = [f for f in gap_files if nslc in f.key]
            patch_file_by_chan = [f for f in patch_files if nslc in f]

            # print("gap_files_by_chan",gap_files_by_chan)
            # print("patch_file_by_chan", patch_file_by_chan)

            gap_filelist = create_listfile(destination=tempdir,
                                           file_list=gap_files_by_chan,
                                           prefix="gap_")
            patch_filelist = create_listfile(destination=tempdir,
                                             file_list=patch_file_by_chan,
                                             prefix="patch_")
            start = gap_starttime.strftime("%Y-%m-%dT%H:%M:%S.%f")
            end = gap_endtime.strftime("%Y-%m-%dT%H:%M:%S.%f")


            arg_list= [str(tempdir),str(gap_filelist),str(patch_filelist),
                       str(start), str(end), str(quality),
                       ]
            result = subprocess.run([self.set_patch_script]
                                    + arg_list, stdout=subprocess.PIPE)
            try:
                logfile = open(log, 'a')
                logfile.write("%s" % result.stdout.decode('utf-8')+"\n")
                logfile.close()
            except (OSError) as err:
                logger.error(err)


            if result.returncode != 0:
                logger.warning("Set_patch failed for %s" %tempdir)


        patched_files = dict()
        for path, subdirs, files in os.walk(os.path.join(tempdir,"SDS")):
            for name in files:
                n,s,l,c,d,y,j = name.split(".")
                key = "%s.%s.%s.%s.%s.%s" %(y,n,s,l,c,j)
                patched_files[key] = os.path.join(path, name)
        return patched_files



    def check_diff(self, patched_file, original_file):
        """
        This method checks that the patched data contain all data
        already existing in the original file in final_archive

        Returns True if the patched data is better than the original data
        False otherwise
        """
        st1 = self.read(original_file)

        # Testing decompression to check that patch didn't introduce any error
        try:
            st2 = self.read(patched_file)
        except:
            logger.exception("Patch can't be decompressed "
                             "\n Not copying file %s"
                             %patched_file)
            return False

        # 1) Get list of all segments in both traces
        # orig_seg_list = [(t.stats.starttime,t.stats.endtime) for t in st1]
        # patch_seg_list = [(t.stats.starttime,t.stats.endtime) for t in st2]


        # 2) Compare all segments in patch with segments in original file
        for orig_seg in st1:

            # i) Get intersection of original_file segments and the current seg
            # -> get all patch segments that start before the end of the
            #    patch segment and end after the start of the patch segment

            # ex:  orig_seg :      |------------------|
            #      st2 :   |---|  |-----|    |---|  |----|   |-----|
            #      inter :        |-----|    |---|  |----|
            #
            inter = [s for s in st2
                     if s.stats.starttime <= orig_seg.stats.endtime
                     and s.stats.endtime >= orig_seg.stats.starttime]
            # print("seg, inter", orig_seg, inter)
            if inter :
                # ii) check that the intersection contains all data from the
                #     original segment
                n_sample = 0
                for trace in inter:
                    n_sample += trace.count()

                # startdif = orig_seg.stats.starttime - inter[0].stats.starttime
                # enddif = orig_seg.stats.endtime - inter[-1].stats.endtime
                sampling_rate = orig_seg.stats.sampling_rate
                # if (orig_seg.count() >= n_sample
                #    or orig_seg.stats.starttime < (inter[0].stats.starttime - (1/sampling_rate))
                #    or orig_seg.stats.endtime > (inter[-1].stats.endtime + (1/sampling_rate))):
                if (orig_seg.count() > n_sample
                   or orig_seg.stats.starttime < (inter[0].stats.starttime - (1/sampling_rate))
                   or orig_seg.stats.endtime > (inter[-1].stats.endtime + (1/sampling_rate))):

                   logger.warning("Set patch : original is better "
                                   "than patch, \n Not copying file %s"
                                   %patched_file)
                   return False

        # 3) Finally, checking that we didn't introduce more overlaps
        #    in the patch
        gaps1, overlaps1 = self.get_stats(st1)
        overlapspan1 = sum(g[6] for g in overlaps1)

        gaps2, overlaps2 = self.get_stats(st2)
        overlapspan2 = sum(g[6] for g in overlaps2)

        if ( len(overlaps1) < len(overlaps2)
            or overlapspan1 < overlapspan2 ):
            logger.warning("Patch has more overlaps than original, "
                           "\n Not copying file %s"
                           %patched_file)
            return False




        # if ( len(gaps1) < len(gaps2)
        #     or len(overlaps1) < len(overlaps2)
        #     or gapspan1 < gapspan2
        #     or overlapspan1 < overlapspan2 ):
        #     logger.warning("Patch has more gaps or overlaps than original, "
        #                    "\n Not copying file %s"
        #                    %patched_file)
        #     return False

        if (st1 == st2):
            # If we have the exact same file, we don't copy it
            logger.warning("Set patch : original is the same "
                            "as patch, \n Not copying file %s"
                            %patched_file)
            return False

        return True


    def merge_to_final(self, gap_files, patched_files, tempdir, final_archive):
        """
        This methods reads the working archive and merges all files to the final
        archive

        """
        # print("gap_files",gap_files)
        for key, patched_file in patched_files.items():
            # print("patch : ", patched_file)

            if gap_files.filter(key=key).count() == 1:
                original_file = gap_files.get(key=key).filename
                if self.check_diff(patched_file, original_file):
                    print("Merging patched file %s to final archive" %patched_file)
                    shutil.copy(patched_file, original_file)
            elif gap_files.filter(key=key).count() > 1:
                logger.error("More than one file exist for the key %s" %key)
            else:
                # print("copying tempdir", tempdir)
                print("Merging data in %s to final archive" %tempdir)
                copy_tree(os.path.join(tempdir,"SDS"),final_archive)
        # shutil.rmtree(tempdir)


    def completion(self, metadata, output):
        return False
