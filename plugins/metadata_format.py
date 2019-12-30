# -*- coding: utf-8 -*-
import abc
import os
import logging
import subprocess
from obspy import read_inventory


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN =  os.path.join(BASE_DIR, "bin")

logger = logging.getLogger('QC')

class MetadataFormat():
    """
    Abstract class for metadata functions
    """
    @abc.abstractmethod
    def read_metadata(self, metadata_path):
        pass
    @abc.abstractmethod
    def validate(self, metadata_path):
        pass
    @abc.abstractmethod
    def write_metadata(self):
        pass
    @abc.abstractmethod
    def resp_plot(self,metadata,outfile):
        pass
    @abc.abstractmethod
    def __str__(self):
        pass

class DatalessSEED(MetadataFormat):
    def __init__(self):
        self.extention = "dataless"
        self.validator = os.path.join(BIN, "stationxml-validator.jar")
        # stationxml validator work as well for dataless, see
        # https://github.com/iris-edu/StationXML-Validator/wiki

    def read_metadata(self, metadata_path):
        return read_inventory(metadata_path)

    def validate(self, metadata_path):
        outfile = os.path.join(metadata_path,"LOG.txt")
        validator_script = ["java","-jar",self.validator,metadata_path,
                            "--format csv", "--output %s" %outfile ]

        result = subprocess.run(validator_script, stdout=subprocess.PIPE)

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
    def __init__(self):
        self.extention = "xml"
        self.validator = os.path.join(BIN, "stationxml-validator.jar")

    def read_metadata(self, metadata_path):
        return read_inventory(metadata_path)

    def validate(self, metadata_path):
        outfile = os.path.join(metadata_path,"LOG.txt")
        validator_script = ["java","-jar", self.validator, metadata_path,
                            "--format csv" ]

        result = subprocess.run(validator_script, stdout=subprocess.PIPE)
        print(result)
        error_list = list()
        warning_list = list()


        # pour chaque ligne :
        # si erreur : erreur list += erreur
        # si warning : wrning_list += warning etc
        return error_list, warning_list

    def write_metadata(self, inventory,filename):
        inventory.write(filename, format='STATIONXML')

    def resp_plot(self,metadata,outfile):
        try:
            resp = read_inventory(metadata.file)[0][0][0].response
            resp.plot(0.001,outfile=outfile,label="Velocity")
        except (TypeError, IndexError) as err:
            logger.error(err)
            return err
        except Exception as err:
            logger.exception("Can't plot response from stationXML")
            return err
        return True

    def __str__(self):
        return "StationXML"
