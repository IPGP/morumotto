#!/bin/bash -e
# Morumotto plugin to get data from the FDSN Web Service, using dataselect

#******************************************************************************#
#                                                                              #
#                       Morumotto plugins structure                            #
#                       ---------------------------                            #
#                                                                              #
# INPUTS are :                                                                 #
#                                                                              #
# ___Simple command usage_____________________________________________________ #
# -h or --help                  Show this usage message                        #
#                                                                              #
# --is_online=CLIENT              Asks if the webservice defined in CLIENT is  #
#                              online and reachable.                           #
#                              Returns 0 if it is online, else 3               #
#                                                                              #
#                                                                              #
# ____________________Fetch data from postfile usage _________________________ #
#                                                                              #
# --postfile=POSTFILE           Path to the postfile containing the nslc       #
#                               and starttime/endtime of the samples we want to#
#                               fetch.                                         #
#                               Defaults to empty                              #
#           *See https://www.orfeus-eu.org/data/eida/webservices/dataselect/   #
#           *to see the format of postfiles                                    #
#                                                                              #
# --workspace=WORKSPACE         Path to the temporary workspace where data will#
#                               be written to.                                 #
#                               Defaults to the ../../WORKING_DIR              #
#                                                                              #
# --data-format=FORMAT          The format to write your data.                 #
#                               Defaults to 'seed'.                            #
#                                                                              #
# --blocksize=blocksize         The output block size, in bytes (or 0).        #
#                               Valid blocksize is between 256 and 8192        #
#                               inclusive, and blocksize=2^N (See qmerge -h)   #
#                               Defaults to 4096                               #
#                                                                              #
# --compression=COMPRESS        Valid formats are STEIM1, STEIM2, INT_16,      #
#                               INT_32, INT_24, IEEE_FP_SP, IEEE_FP_DP         #
#                               (See qmerge -h).                               #
#                               Defaults to STEIM2                             #
#                                                                              #
# --connect-infos=CONNECT_INFOS A string containing additional informations to #
#                               connect to the source. Must be                 #
#                              client:<wsaddress>[?limit_rate=<limit>] where   #
#                              <wsaddress> is the web service url and <limit>  #
#                              is the downloading limit in bytes per seconds.  #
#                              Defaults to client:service.iris.edu             #
#                                                                              #
# --log-level                   An integer, between 0 and 7 to define the      #
#                               verbose level for this script                  #
#                               [0]=emerg [1]=alert [2]=crit [3]=err           #
#                               [4]=warning [5]=notice [6]=info [7]=debug      #
#                               Defaults to 3                                  #
#                                                                              #
# OUTPUTS :                                                                    #
#                                                                              #
# * Exit Status                 0 : Success                                    #
#                               1 : Execution error                            #
#                               2 : No data error                              #
#                               3 : Timeout or connection error                #
#                               4 : Bad ID error                               #
#                               5 : Writing error                              #
#                                                                              #
# * Data MUST be written to the WORKSPACE path in an SDS archive.              #
#                                                                              #
# Please see https://www.seiscomp3.org/doc/applications/slarchive/SDS.html and #
# github.com/iris-edu/dataselect/blob/master/doc/dataselect.md#archive-format  #
#                                                                              #
#                                                                              #
# LOGS :                                                                       #
#                                                                              #
# Morumotto will create a log file from the outputs of the plugin. Please use  #
# the .log funcion when you write your outputs, instead of echo                #
#                                                                              #
#*******************************************************************************

SCRIPTPATH=$(dirname $0)
morumottobin="$(dirname $(dirname ${SCRIPTPATH}}))/bin"
export PATH="${morumottobin}:${SCRIPTPATH}:/usr/local/bin:/usr/bin:/bin"

# Help :
if [ "$1" == "-h" ] || [ "$1" == "--help" ]
then
  echo "Usage: `basename $0` NSLC starttime endtime workspace data_format data_structure connect_infos"
  echo "Parameters : NSLC "
  exit 0
fi

# Verbose

# (https://stackoverflow.com/questions/8455991/elegant-way-for-verbose-mode-in-scripts)
# to put some verbose in the script, do it like this :
# .log 3 "Something is wrong here"

# set verbose level to info
__VERBOSE=6

declare -A LOG_LEVELS
# https://en.wikipedia.org/wiki/Syslog#Severity_level
LOG_LEVELS=([0]="emerg" [1]="alert" [2]="crit" [3]="err" [4]="warning" [5]="notice" [6]="info" [7]="debug")
function .log () {
  local LEVEL=${1}
  shift
  if [ ${__VERBOSE} -ge ${LEVEL} ]; then
    echo "[${LOG_LEVELS[$LEVEL]}]" "$@"
  fi
}

# Check number of args
if [ "$#" -ne 7 ]; then
    echo "Missing some parameters, see --help"
    exit 0
fi

pid=$$
nslc_list=$1

starttime=$2
endtime=$3
workspace=$4
data_format=$5
data_structure=$6
connect_infos=$7

filedate=$(date -d "$starttime" +'%Y-%m-%dT%H:%M:%S')
year=$(date -d $filedate '+%Y')
jday=$(date -d $filedate '+%j')
echo "year : $year jday: $jday"

client="service.iris.edu"

for nslc in nslc_list;do
  Net="$(cut -d'.' -f1 <<<"$nslc")"
  Sta="$(cut -d'.' -f2 <<<"$nslc")"
  Loc="$(cut -d'.' -f3 <<<"$nslc")"
  Chan="$(cut -d'.' -f4 <<<"$nslc")"
  if [ $data_structure == "sds" ]
  then
    filename="$workspace/$year/$Net/$Sta/$Chan.D/$nslc.D.$jday.mseed"
    # filename="$workspace/$year/$Net/$Sta/$Chan.D/test"
  fi
  echo $filename
  request="http://$client/fdsnws/dataselect/1/query?network=$Net&station=$Sta&starttime=$starttime&endtime=$endtime"
  echo "request:" $request
  wget -O $filename $request
done;
# dataselect pour répartir dans la bonne structure
