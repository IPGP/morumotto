# -*- coding: utf-8 -*-
import abc
import logging
from obspy import read_inventory

logger = logging.getLogger('QC')

class MetadataFormat():
    """
    Abstract class for metadata functions
    """
    @abc.abstractmethod
    def read_metadata(self):
        pass
    @abc.abstractmethod
    def write_metadata(self):
        pass
    @abc.abstractmethod
    def __str__(self):
        pass

class DatalessSEED(MetadataFormat):
    def read_metadata(self):
        pass
    def write_metadata(self):
        pass

    def resp_plot(self,metadata,outfile):
        try:
            resp = read_inventory(metadata.file)[0][0][0].response
            resp.plot(0.001,outfile=outfile,label="Velocity")
        except (TypeError, IndexError) as err:
            logger.error(err)
            return err
        return True


    def __str__(self):
        return "dataless"


class stationXML(MetadataFormat):
    def read_metadata(self):
        pass

    def write_metadata(self, inventory,filename):
        inventory.write(filename, format='STATIONXML')

    def resp_plot(self,metadata,outfile):
        try:
            resp = read_inventory(metadata.file)[0][0][0].response
            resp.plot(0.001,outfile=outfile,label="Velocity")
        except (TypeError, IndexError) as err:
            logger.error(err)
            return err
        return True

    def __str__(self):
        return "StationXML"
