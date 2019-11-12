# -*- coding: utf-8 -*-
import os
import obspy
import logging
import socket
from datetime import datetime, timedelta
import time

logger = logging.getLogger('Status')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR/")


def get_leaps(filename):
    """
    Method which reads a leapsecond.list file and returns a list of leap seconds
    in time format (leapsecond is not supported by datetime)
    """
    leap_sec_list = list()
    if not isempty(filename):
        with open(filename) as f_in:
            lines = filter(None, (line.rstrip() for line in f_in))

            for line in lines:
                if line[0] == "#":
                    continue
                if line:
                    l,y,m,d,clock,cor,rs = line.split()
                    date = time.strptime(
                         "%s-%s-%s %s" %(y,m,d,clock),"%Y-%b-%d %H:%M:%S")
                    date_str = time.strftime("%b %d %Y, %H:%M:%S",date)
                    leap_sec_list.append(date_str)
    return leap_sec_list


def isempty(filename):
    """Raises an error if the file "filename" doesn't exist"""
    try:
        return os.stat(filename).st_size == 0
    except OSError: #file does not exist
        return True


def delete_plots():
    """ To display plots of streams, we save png in a static folder.
    This function erases all PNG inside this folder,
    as they are useless outside the plot view"""

    pathtopng = os.path.join(WORKING_DIR, "PLOT/")
    for root, dirs, files in os.walk(pathtopng):
        for file in files:
            os.remove(os.path.join(root, file))


def lower(value):  # Only one argument.
    """Converts a string into all lowercase"""
    return value.lower()


def jday(dt):
    """ Converts a datetime into the corresponding julian DAY.
    (Please note that this is not the julian DATE, which is something
    completely different)
    """
    julianday = '%03d' % (dt.timetuple().tm_yday)
    return julianday


def yyyymmdd(year,jday):
    """ Converts a jday and a year into the corresponding string
    date which will be "YYYY-MM-DD".
    """
    stringdate = datetime.strptime('%d%03d' % (year,jday),"%Y%j").strftime('%Y-%m-%d')
    return stringdate


def to_utcdatetime(dt):
    """ Converts a python datetime object into an obspy UTCDateTime"""
    return obspy.UTCDateTime.strptime(
            dt.strftime("%Y-%m-%d %H:%M:%S.%f"),"%Y-%m-%d %H:%M:%S.%f")


def daterange( start_date, end_date ):
    """ Returns a list of days between start_date and end_date"""
    if start_date <= end_date:
        for n in range( ( end_date - start_date ).days + 1 ):
            yield start_date + timedelta( n )
    else:
        for n in range( ( start_date - end_date ).days + 1 ):
            yield start_date - timedelta( n )


def datelist(starttime, endtime):
    """
    Returns a list of datetimes between starttime and endtime
    """
    if starttime.strftime('%Y%j') == endtime.strftime('%Y%j'):
        # if the starting day is the same as the ending day
        return [starttime]
    else:

        return [starttime + timedelta(days=x)
                for x in range((endtime-starttime).days+1)]

def is_online():
    try:
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        pass
        return False
