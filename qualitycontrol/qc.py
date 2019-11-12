# -*- coding: utf-8 -*-
import os
import subprocess
import logging
from obspy.io.xseed import Parser
from datetime import datetime, timedelta
from fnmatch import fnmatch
from .models import Metadata
from seismicarchive.models import NSLC, Network, Station, Location, Channel

logger = logging.getLogger('QC')


def update_metadata(config):
    """
    Update metadata in the database
    """
    archive = config.archive
    md_dir = os.path.join(archive,"METADATA/")
    md_list = [f for f in os.listdir(md_dir) if
               os.path.isfile(os.path.join(md_dir, f))]
    for md_file in sorted(md_list):
        if fnmatch(md_file, '*.dataless'):
            md_path = os.path.join(md_dir,md_file)
            sp = Parser(md_path) #ONLY SEED
            for chan in sp.get_inventory()['channels']:
                code = chan["channel_id"]
                lon = chan["longitude"]
                lat = chan["latitude"]
                net, sta, loc, chan = code.split(".")
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

# /home/geber/SiQaCo/siqaco_project/WORKING_DIR/METADATA

def metadata_from_webservice(config, client):
    """
    This method fetches metadata for all stations and networks in the config
    object, using the WEBSERVICE client, and writing it in the final archive
    defined by the configuration object

    Parameters :

    client : A webservice client for ObsPy, for example
             obspy.clients.fdsn("IRIS")

    config : a Configuration instance (from seismicarchive.models)
    """
    md_format = config.get_metadata_format()
    nslc_list = [nslc for nslc in config.nslc.all()]
    archive = config.archive

    for nslc in nslc_list:
        filename = os.path.join(
                 archive,"METADATA/",nslc.net.name,
                 "%s_%s.%s" %(nslc.net.name,nslc.sta.name,md_format.__str__()))
        try:
            inventory = client.get_stations(
                      network=nslc.net.name,
                      station=nslc.sta.name,
                      level="channel")
            md_format.write_metadata(inventory,filename)
            update_metadata(config)
            logger.info( "Metadata updated on %s from %s"
                        %(datetime.now(), client) )
        except AttributeError as err:
            logger.exception(err)



def metadata_from_svn(config, svn_address, username, password):
    """
    This method fetches metadata for all stations and networks in the config
    object, using a svn adress, and writing it in the final archive
    defined by the configuration object

    Parameters :

    svn_address : the URL to the svn to get metadata

    config : a Configuration instance (from seismicarchive.models)
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


def metadata_from_dir(config, dirname):
    """
    This method makes a local copy from metadata files contained in a local dir,
    located by dirname

    Parameters :

    dirname : `path`
            the path to directory we want to read

    config : a Configuration instance (from seismicarchive.models)
    """


    archive = config.archive
    destination = os.path.join(archive,"METADATA/")
    try:
        result = subprocess.run(["cp","-rf", dirname, destination],
                                stdout=subprocess.PIPE)

        # print(result.stdout.decode('utf-8'))
        update_metadata(config)
        logger.info( "Metadata updated on %s from %s"
                    %(datetime.now(), dirname) )
    except (TypeError, IndexError) as err:
        logger.error(err)


def dataless_log_check():
    # get DatalessUpdateLog
    now = datetime.now()
    pass


def dataless_consistency():
    #check_dataless.sh
    pass
