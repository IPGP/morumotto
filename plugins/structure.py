# -*- coding: utf-8 -*-
import abc
import os
import fnmatch
from datetime import datetime
from glob import glob
import morumotto.toolbox as toolbox
import logging

logger = logging.getLogger('Status')

class AbstractStructure():
    """ This abstract class defines the basic methods that need
    to be implemented to use a data structure plugin

    To create a data format plugin, create a file named
    plugins/structures/yourstruct.py (with "yourformat" being the name of the
    format you want to use), and then you will have to create

    - a browse function which returns a list of files
    - a create_struct which makes directories according to your structure

    You can have a look at the other existing plugins to see how to proceed


    """
    @abc.abstractmethod
    def create_struct(self, archive, years, nslc_list):
        pass
    @abc.abstractmethod
    def browse(self, archive):
        pass
    @abc.abstractmethod
    def get_path(self, archive, nslc, year):
        pass
    @abc.abstractmethod
    def get_filepattern(self, nslc, jday , year):
        pass
    @abc.abstractmethod
    def get_filelist(self, archive, nslc_list, starttime, endtime):
        pass
    @abc.abstractmethod
    def pattern(self, year, nslc_code):
        pass
    @abc.abstractmethod
    def nslc_from_archive(self, archive):
        pass


class SDS(AbstractStructure):
    """ This class will be used when the admin defined the data structure as
    being Seiscomp Data Standart (SDS)

    It inheritates of the DataFormat abstract class
    """

    def create_struct(self, archive, years, nslc_list):
        """
        SDS : dir/%Y/%n/%s/%c.D/%n.%s.%l.%c.D.%Y.%j


        This method initiate all directories of the final archive
        where the data will be saved with all stations and channels for some given networks

        Networks are read from the configuration, then an empty SDS archive is created for
        a given set of years also defined in the configuration

        It requires :

        parameters : must be one of obspy parameters classes, see the Database
        or Web Service Access Clients section of obspy doc for more informations
        """

        for nslc in nslc_list:
            net,sta,loc,chan = nslc.split('.')
            if isempty(os.path.join(archivepath,year,net,sta,chan)):
                    try:
                        os.makedirs(os.path.join(archivepath,year,net,sta,chan+".D"))
                    except (FileExistsError) as err:
                        logger.exception("error", err)


    def browse(self, archive):
        """
        This method returns all existing channel paths existing
        for an SDS structure

        Arguments :
        archive : `str` the complete path to the archive you want to browse
        Return : a list of paths
        """

        paths = [glob(os.path.join(archive, '????', '*'))]
        l = [os.path.join(archive, '????', '*')]
        paths = [p for l in paths for p in l]
        stationpaths = [glob(os.path.join(p, '*')) for p in paths]
        stationpaths = [sp for l in stationpaths for sp in l]
        channelpaths = [glob(os.path.join(sp, '???.?')) for sp in stationpaths]
        return [cp for l in channelpaths for cp in l]


    def get_path(self, archive, nslc, year):
        """
        This method returns the complete path for a given nslc

        Arguments :
        archive : `str` the complete path to the archive
        nslc : `str` giving the NSLC dot separated (must be of the form N.S.L.C)
                example : "PF.BOR.00.EHZ"
        year : `str` the year we want to acces
        Return : `str` an SDS path so the folder containing this NLSC files for
                  the year defined
        """
        net, sta, loc, chan = nslc.split(".")
        return os.path.join(archive, year, net, sta, chan+".D")

    def get_filepattern(self, nslc, jday , year):
        """
        This method returns the file path paatern for a given nslc and year, jday

        Arguments :
        nslc : `str` giving the NSLC dot separated (must be of the form N.S.L.C)
                example : "PF.BOR.00.EHZ"
        jday : `str` the jday we want to acces
        Return : `str` an SDS file pattern to the nlsc jday file location
        """
        net, sta, loc, chan = nslc.split(".")
        return '%s.%s.%s.%s.D.%s.%s' % (net, sta, loc, chan, year,jday)


    def get_filelist(self, archive, nslc_list, starttime, endtime):
        """
        Returns a dictionary for all files to be proceded
        The key is a str of year.N.S.L.C.jday
        """
        date_list = toolbox.datelist(starttime,endtime)
        filelist = dict()
        for nslc in nslc_list:
            for date in date_list:
                year = date.strftime('%Y')
                jday = date.strftime('%j')
                channelpath = self.get_path(archive,nslc.code,year)
                mseedfpattern = self.get_filepattern(nslc.code, jday, year)
                if os.path.isfile(os.path.join(channelpath, mseedfpattern)):
                    mseedfile = os.path.join(channelpath, mseedfpattern)
                    key = '.'.join([year,nslc.code,jday])
                    filelist[key] = mseedfile
        return filelist


    def pattern(self, year, nslc_code):
        n,s,l,c = nslc_code.split(".")
        d_chan = c + ".D"
        return os.path.join(year,n,s,d_chan)

    def nslc_from_archive(self, archive):
        """"
        Method which create all NSLC from reading an archive
        """

        nslc_list = list()
        path_list = list()
        for path, subdirs, files in os.walk(archive):
            for name in files:
                nslc = ".".join(name.split(".")[-7:-3])
                if nslc and nslc not in nslc_list:
                    nslc_list.append(nslc)
        return nslc_list
