# -*- coding: utf-8 -*-
import re
import logging
from datetime import datetime
from obspy import read_inventory
from archive.models import Network, Station, Location, Channel, NSLC
from monitoring.models import Component
import morumotto.toolbox as toolbox


logger = logging.getLogger('Status')

def update_database(net, sta, loc, chan, configuration):
    """
    This method will update the Station, Channel, Location, NSLC and Component
    objects in the database, according to the net, sta, loc and chan values.

    It will check for already existing entities in order not to create duplicate
    data

    Parameters :

    net : `str`
          The Network code

    sta : `str`
          The Station code

    loc : `str`
          The Location code

    chan : `str`
          The Channel code

    configuration : a Configuration instance (from archive.models)
    """
    comp = chan[0:2]
    network, created = Network.objects.get_or_create(name=net)
    station, created = Station.objects.get_or_create(
                     network=network,name=sta)
    if not configuration.networks.filter(pk=network.pk).exists():
        configuration.networks.add(network)
        configuration.save()
    if not configuration.stations.filter(pk=station.pk).exists():
        configuration.stations.add(station)
        configuration.save()


    location, created = Location.objects.get_or_create(name=loc)
    channel, created = Channel.objects.get_or_create(name=chan)

    nslc, created = NSLC.objects.get_or_create(
                  net=network, sta=station, loc=location, chan=channel)
    if not configuration.nslc.filter(pk=nslc.pk).exists():
        configuration.nslc.add(nslc)
        configuration.save()

    component, created = Component.objects.get_or_create(name=comp)
    return nslc


def nslc_from_webservice(client, configuration):
    """
    This method reads all NSLC available for a given configuration from a
    specified client and create the associate NSLC fields in the Database

    Parameters :

    client : A webservice client for ObsPy, for example
             obspy.clients.fdsn("IRIS")

    configuration : a Configuration instance (from archive.models)
    """


    networks = [net.name for net in configuration.networks.all()]

    archive = configuration.archive
    try:
        inventory = client.get_stations(
                  network=",".join(net for net in networks),
                  starttime=toolbox.to_utcdatetime(datetime.utcnow()),
                  endtime=toolbox.to_utcdatetime(datetime.utcnow()),
                  level="channel")
        # print("inventory", inventory)
    except (TypeError, IndexError) as err:
        logger.exception("error", err)

    # for network in sorted(inventory.get_contents()["networks"]):
    # NSLC.objects.all().delete()
    nslc_list = list()
    for channel in sorted(inventory.get_contents()["channels"]):
        net,sta,loc,chan = channel.split('.')
        nslc = update_database(net,sta,loc,chan,configuration)
        nslc_list.append(nslc.code)
    return nslc_list

def nslc_from_stationxml(filename, configuration):
    """
    This method reads all NSLC from a stationXML file, then puts them into the
    database
    Parameters :

    file : `path`
            the path to file we want to read

    configuration : a Configuration instance (from archive.models)
    """
    inv = read_inventory(filename, format="STATIONXML")
    nslc_list = list()
    for channel in sorted(inv.get_contents()["channels"]):
        net,sta,loc,chan = channel.split('.')
        nslc = update_database(net,sta,loc,chan,configuration)
        nslc_list.append(nslc.code)
    return nslc_list


# def nslc_from_file(filename,configuration):
#     """
#     This method reads all NSLC from an xml file. The NSLC must be | separated,
#     following this example :
#
#     #Network|Station|Location|Channel
#     G|AIS|00|BHE
#     G|AIS|00|BHN
#
#     Parameters :
#
#     file : `path`
#             the path to file we want to read
#
#     configuration : a Configuration instance (from archive.models)
#     """
#
#     for line in filename.__iter__():
#         code = re.findall(r"'([^']*)'",str(line))[0]
#         code = code.replace('\\n','')
#
#         if code[0] == "#":
#             continue
#         net,sta,loc,chan = code.split("|")
#         update_database(net,sta,loc,chan,configuration)
