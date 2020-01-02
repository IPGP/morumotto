# -*- coding: utf-8 -*-
import os
import subprocess
import logging
from distutils.dir_util import copy_tree
from obspy.io.xseed import Parser
from obspy import read_inventory
from obspy.clients.fdsn.header import FDSNNoDataException
from datetime import datetime, timedelta
from fnmatch import fnmatch
from .models import Metadata, Message
from archive.models import NSLC, Network, Station, Location, Channel

logger = logging.getLogger('QC')


def update_metadata(config):
    """
    Update metadata in the database
    """
    archive = config.archive
    md_format = config.get_metadata_format()
    md_extention = ("*.%s" %md_format.extention)
    md_dir = os.path.join(archive,"METADATA/")
    # md_list = [f for f in os.listdir(md_dir) if
    #            os.path.isfile(os.path.join(md_dir, f))]
    # get all files recursively
    md_list = list()
    for (dirpath, dirnames, filenames) in os.walk(md_dir):
        md_list += [os.path.join(dirpath, file) for file in filenames]
    for md_file in sorted(md_list):
        if fnmatch(md_file, md_extention):
            md_path = os.path.join(md_dir,md_file)
            md_format.validate(md_path)
            try:
                sp = md_format.read_metadata(md_path)
            except ValueError as err :
                logger.exception("Reading metadata error")
            for chan in sp.get_contents()['channels']:
                lon = sp.get_coordinates(chan)["longitude"]
                lat = sp.get_coordinates(chan)["latitude"]
                elevation = sp.get_coordinates(chan)["elevation"]
                net, sta, loc, chan = chan.split(".")
                network, c = Network.objects.get_or_create(name=net)
                station, c = Station.objects.get_or_create(network=network,
                                                           name=sta)
                location, c = Location.objects.get_or_create(name=loc)
                channel, c = Channel.objects.get_or_create(name=chan)
                nslc, created = NSLC.objects.get_or_create(
                              net=network, sta=station,
                              loc=location, chan=channel)
                metadata, created = Metadata.objects.get_or_create(
                                  nslc=nslc, file=md_path, lon=lon, lat=lat)


def md_from_webservice(config, client):
    """
    This method fetches metadata for all stations and networks in the config
    object, using the WEBSERVICE client, and writing it in the final archive
    defined by the configuration object

    Parameters :

    client : A webservice client for ObsPy, for example
             obspy.clients.fdsn.Client("IRIS")

    config : a Configuration instance (from archive.models)
    """
    md_format = config.get_metadata_format()
    nslc_list = [ nslc for nslc in NSLC.objects.all() ]
    archive = config.archive

    for nslc in nslc_list:
        if not os.path.exists(os.path.join(archive,"METADATA/",nslc.net.name)):
            os.makedirs(os.path.join(archive,"METADATA/",nslc.net.name))
        filename = os.path.join(
                 archive,"METADATA/",nslc.net.name,
                 "%s_%s.%s" %(nslc.net.name,nslc.sta.name,md_format.extention))
        try:
            inventory = client.get_stations(
                      network=nslc.net.name,
                      station=nslc.sta.name,
                      level="response")
            md_format.write_metadata(inventory,filename)
            update_metadata(config)
            logger.info( "Metadata updated on %s from %s"
                        %(datetime.now(), client) )
        except (FDSNNoDataException,
                AttributeError) as err:
            logger.exception(err)



def md_from_svn(config, svn_address, username, password):
    """
    This method fetches metadata for all stations and networks in the config
    object, using a svn adress, and writing it in the final archive
    defined by the configuration object

    Parameters :

    svn_address : the URL to the svn to get metadata

    config : a Configuration instance (from archive.models)
    """

    archive = config.archive
    filename = os.path.join(archive,"METADATA/")
    try:
        result = subprocess.run(["svn","export",svn_address, filename,
                                 "--username", username,
                                 "--password", password],
                                stdout=subprocess.PIPE)

        update_metadata(config)
        logger.info( "Metadata updated on %s from %s"
                    %(datetime.now(), svn_address) )
    except (TypeError, IndexError) as err:
        logger.error(err)


def md_from_dir(config, dirname):
    """
    This method makes a local copy from metadata files contained in a local dir,
    located by dirname

    Parameters :

    dirname : `path`
            the path to directory we want to read

    config : a Configuration instance (from archive.models)
    """


    archive = config.archive
    destination = os.path.join(archive,"METADATA/")
    try:
        # remove files in dir
        for root, dirs, files in os.walk(destination):
            for file in files:
                os.remove(os.path.join(root, file))
        copy_tree(dirname, destination)
        # print(result.stdout.decode('utf-8'))
    except (TypeError, IndexError) as err:
        logger.error(err)

    update_metadata(config)
    logger.info( "Metadata updated on %s from %s" %(datetime.now(), dirname) )



def md_check(config, metadata_list, starttime=None,endtime=None):
    """

    This method will perform some validations on your metadata list
    and save all messages into database
    """

    md_format = config.get_metadata_format()
    for metadata in metadata_list:
        error_list, warning_list = md_format.validate(metadata.file)
        for error in error_list:
            error_start = error[1]
            error_end = error[2]
            # test starttime, endtime
            error_msg = Message(type='error',msg=error[0])
            metadata.messages.add(error_msg)
            metadata.save()
        for warning in warning_list:
            warning_start = warning[1]
            warning_end = warning[2]
            # test starttime, endtime
            warning_msg = Message(type='warning',msg=warning[0])
            metadata.messages.add(warning_msg)
            metadata.save()


def metadata_vs_data(config, nslc_list, starttime=None,endtime=None):
        """

        This method will perform some validations on your metadata list,
        confronting it with your data
        """

        md_format = config.get_metadata_format()
        metadata_list = Metadata.objects.filter(nslc__in=nslc_list)
        for metadata in metadata_list:
            # get all data with this nslc,
            # read datafile, check consistency with NSLC, etc.
            continue
