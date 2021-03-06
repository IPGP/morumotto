#!/bin/bash -e
# Morumotto plugin to get data from the VALDON server, using ssh

# ************************************************************************#
#                                                                         #
#    Copyright (C) 2019 RESIF/IPGP                                        #
#                                                                         #
#    This program is free software: you can redistribute it and/or modify #
#    it under the terms of the GNU General Public License as published by #
#    the Free Software Foundation, either version 3 of the License, or    #
#    (at your option) any later version.                                  #
#                                                                         #
#    This program is distributed in the hope that it will be useful,      #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of       #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        #
#    GNU General Public License for more details.                         #
#                                                                         #
#    This program is part of 'Morumotto'.                                 #
#    It has been financed by RESIF (Réseau sismologique & géodésique      #
#    français )                                                           #
#                                                                         #
#  ***********************************************************************#

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
# --availability               Flag to get only the inventory, not downloading #
#                              any data.                                       #
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
check_requirements.sh

echo $@
set -o history -o histexpand # only for dev: echo !! prints last command line

usage()
{
  echo "usage : `basename $0` [-h] [--help] [--online] [--availability]
  [--postfile] [--workspace] [--data-format] [--blocksize] [--compression]
  [--connect-infos ] [--log-level]

Warning: if you are using --online or --availability, this script will not
         fetch any data

Info: you may want to add your rsa public key to your host in order to avoid
      clear passwords informations in the client. See 'man ssh-copy-id', it
      takes less than a minute to configure and will avoid security problems
  "
}

# Help :
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  usage
  echo "
  ## Simple command usage
  -h or --help                  Show this usage message

  --online=CLIENT               Asks if the webservice defined in CLIENT is
                                online and reachable.
                                Returns 0 if it is online, else 3

  --availability                Flag to get only the inventory, not downloading
                                any data.

  --dataless                    Flag to get dataless from the postfile

  ## Fetch data from postfile usage
  --postfile=POSTFILE           Path to the postfile containing the nslc
                                and starttime/endtime of the samples we want to
                                fetch.
                                Defaults to ''.
                See https://www.orfeus-eu.org/data/eida/webservices/dataselect/
                to see the format of postfiles

  --workspace=WORKSPACE         Path to the temporary workspace where data will
                                be written to.
                                Defaults to '../../WORKING_DIR'

  --data-format=FORMAT          The format to write your data.
                                Defaults to 'seed'

  --blocksize=blocksize         The output block size, in bytes (or 0).
                                Valid blocksize is between 256 and 8192
                                inclusive, and blocksize=2^N (See qmerge -h)
                                Defaults to '4096'

  --compression=COMPRESS        Valid formats are STEIM1, STEIM2, INT_16,
                                INT_32, INT_24, IEEE_FP_SP, IEEE_FP_DP
                                (See qmerge -h)
                                Defaults to 'STEIM2'

  --connect-infos=CONNECT_INFOS A string containing additional informations to
                                connect to the archive. Must be
                 <user_name@server:/path/to/SDS/>[?limit=<limit>&pwd=<password>]
                                where <limit> is the downloading limit in bytes
                                per seconds.
                                Defaults to ''

  --log-level                   An integer, between 0 and 7 to define the
                                verbose level for this script
                                [0]=emerg [1]=alert [2]=crit [3]=err
                                [4]=warning [5]=notice [6]=info [7]=debug

  Exit Status                   0 : Success
                                1 : Execution error
                                2 : No data/inventory found
                                3 : Timeout or connection error
                                4 : Bad ID error
                                5 : Writing error
  "
  exit 0
fi

# Check number of args
if [ "$#" -gt 7 ] || [ -z "$1" ]; then
  echo "ERROR: wrong usage"
  usage
  exit 1
fi

# Check requirements
command -v dataselect >/dev/null 2>&1 || { echo >&2 "ERROR : dataselect is not \
installed. Please install dataselect >= 3.20: \
https://github.com/iris-edu/dataselect"; exit 1; }
DATASELECT_VERSION=$(dataselect -V 2>&1)
VERSION=${DATASELECT_VERSION##*: }

if (( $(echo "${VERSION} <= 3.19" |bc -l) )); then
  echo "Your dataselect software version is ${VERSION}, must be >= 3.20
  Please install dataselect >= 3.20: https://github.com/iris-edu/dataselect"
  exit 1
fi

command -v msi >/dev/null 2>&1 || { echo >&2 "ERROR : msi (miniSEED inspector) \
is not installed. Please install msi \
https://github.com/iris-edu/msi"; exit 1; }

command -v qmerge >/dev/null 2>&1 || { echo >&2 "ERROR : qmerge \
is not installed. Please install qmerge : \
quake.geo.berkeley.edu/qug/software/ucb/qmerge.2014.329.tar.gz"; exit 1; }


# Verbose
declare -A LOG_LEVELS
LOG_LEVELS=([0]="emerg" [1]="alert" [2]="crit" [3]="err" [4]="warning" \
            [5]="notice" [6]="info" [7]="debug")
function .log () {
  local LEVEL=${1}
  shift
  if [ ${__VERBOSE} -ge ${LEVEL} ]; then
    echo "[${LOG_LEVELS[$LEVEL]}]" "$@"
  fi
}

# Convert wget exit code to exit status understandable by Morumotto
# See doc of wget for exit status :
# https://www.gnu.org/software/wget/manual/html_node/Exit-Status.html
function convert_exit() {
  local exit_code=${1}
  case ${exit_code} in
    "") EXIT_STATUS=0 ;; # SUCCESS
    1) EXIT_STATUS=1 ;;
    2) EXIT_STATUS=1 ;;
    3) EXIT_STATUS=5 ;;
    4) EXIT_STATUS=3 ;;
    5) EXIT_STATUS=3 ;;
    6) EXIT_STATUS=4 ;;
    7) EXIT_STATUS=3 ;;
    8) EXIT_STATUS=3 ;;
    *) .log 3 "Unkown ERROR during WGET" ; exit 1 ;;
  esac;
  echo ${EXIT_STATUS}
}

# Function that returns the online status for the client
function is_source_online() {
  local CLIENT=${1}
  local SERVER=$(echo ${CLIENT} | awk -F '[@:?=&/]' '{print $2}')
  .log 7 "Server : ${SERVER}"
  if [ "${SERVER}" = "" ]; then
    .log . "Please fill the source 'client' information. "
    exit 1
  fi
  ping -c1 -W1 -q ${SERVER} 2>&1 >/dev/null || exit_wget=$? ;

  EXIT_STATUS=$(convert_exit ${exit_wget})
  .log 6 "Exit status :" ${EXIT_STATUS}
  exit ${EXIT_STATUS}
}

# List of inputs
ARGUMENT_LIST=(
    "online"
    "availability"
    "dataless"
    "postfile"
    "workspace"
    "data-format"
    "blocksize"
    "compression"
    "connect-infos"
    "log-level"
)

# Read arguments
opts=$(getopt \
    --longoptions "$(printf "%s::," "${ARGUMENT_LIST[@]}")" \
    --name "$(basename "$0")" \
    --options "" \
    -- "$@"
    )
eval set --${opts}
# extract options and their arguments into variables.
while true; do
    case "$1" in
        --online) ONLINE_FLAG=true; CLIENT=$2; shift 2 ;;

        --availability) AVAILABILITY_FLAG=true; shift 2 ;;

        --postfile) POSTFILE=$2; shift 2 ;;

        --dataless) DATALESS_FLAG=$2; shift 2 ;;

        --workspace) WORKSPACE=$2; shift 2 ;;

        --data-format) DATA_FORMAT=$2; shift 2 ;;

        --blocksize) BLOCKSIZE=$2; shift 2 ;;

        --compression) COMPRESS=$2; shift 2 ;;

        --connect-infos) CONNECT_INFOS=$2; shift 2 ;;

        --log-level) __VERBOSE=$2; shift 2 ;;

        --) shift ; break ;;
        *) echo "Wrong call to the script!" usage ; exit 1 ;;
    esac
done

# If we have just want to know if the plugin is online:
if [ ${ONLINE_FLAG} ]; then
  is_source_online $CLIENT
fi

# Create defaults
if [ "${WORKSPACE}" = "" ]; then
  base=$(dirname $(dirname $(dirname ${BASH_SOURCE[0]})))
  WORKSPACE="${base}/WORKING_DIR"
  .log 7 "Workspace: $WORKSPACE"
fi
if [ "${DATA_FORMAT}" = "" ]; then
  DATA_FORMAT="seed"
  .log 7 "Data format: $DATA_FORMAT"
fi
if [ "${BLOCKSIZE}" = "" ]; then
  BLOCKSIZE="4096"
  .log 7 "Blocksize: $BLOCKSIZE"
fi
if [ "${COMPRESS}" = "" ]; then
  COMPRESS="STEIM2"
  .log 7 "Compress: $COMPRESS"
fi
if [ "${CONNECT_INFOS}" = "" ]; then
  CONNECT_INFOS="client:service.iris.edu"
  .log 7 "Connect infos: $CONNECT_INFOS"
fi
if [ "${__VERBOSE}" = "" ]; then
  __VERBOSE="3"
  .log 7 "Verbose: $__VERBOSE"
fi

# Check that the postfile exists
if [ ! -e ${POSTFILE} ]; then
  .log 3 "${POSTFILE} doesn't exist, exiting...."
  exit 1
fi

# Create workspace directory if it doesn't exist yet
if [ ! -d "${WORKSPACE}" ]; then
  mkdir -pv "${WORKSPACE}"
  .log 6 "${WORKSPACE} created"
fi

# Get client name
CLIENT=$(echo ${CONNECT_INFOS} | awk -F '[?]' '{print $1}')
.log 7 "client: "${CLIENT}
LIMIT_RATE=$(echo ${CONNECT_INFOS} | awk -F '[?=&]' '{print $3}')
PASSWD=$(echo ${CONNECT_INFOS} | awk -F '[?=&]' '{print $5}')
if [ "${LIMIT_RATE}" = "" ]; then
  LIMIT_RATE="0k"
fi
.log 7 "Limit rate: ${LIMIT_RATE}"

if [ ${AVAILABILITY_FLAG} ]; then
  .log 3 "Inventory not available yet"
  exit 2;
fi

# Create list of data to fetch
while IFS='' read -r Net Sta Loc Chan Starttime Endtime esc; do
  echo "${Net}.${Sta}.${Loc}.${Chan} $esc"
  # declare -a Net_array
  # declare -a Sta_array
  # declare -a Loc_array
  # declare -a Chan_array
  # declare -a Starttime_array
  # declare -a Endtime_array

  linedate=$(date -d "$Starttime" +'%Y-%m-%dT%H:%M:%S')
  year=$(date -d $linedate '+%Y')
  jday=$(date -d $linedate '+%j')
  # Net_array[$i]=$Net
  # Sta_array[$i]=$Sta
  # Loc_array[$i]=$Loc
  # Chan_array[$i]=$Chan
  # Starttime_array[$i]=$Starttime
  # Endtime_array[$i]=$Endtime

  now="$(date +'%s')"


  if [ ! -d "${WORKSPACE}/TEMP" ]; then
    mkdir "${WORKSPACE}/TEMP"
    .log 6 "${WORKSPACE}/TEMP created"
  fi
  if [ ! -d "${WORKSPACE}/ARCHIVE" ]; then
    mkdir "${WORKSPACE}/ARCHIVE"
    .log 6 "${WORKSPACE}/ARCHIVE created"
  fi
  # Create a temp directory (will be erase at the end of this script if succeded)
  TEMP_DIR=$(mktemp -d -p ${WORKSPACE}/TEMP) || { .log 3 \
  "Failed to create temp dir"; exit 1; }
  # FILENAME="${TEMP_DIR}/${now}.ws_raw.${DATA_FORMAT}"
  # .log 7 "Filename: ${FILENAME}"

  # wget --post-file=${POSTFILE} --limit-rate=${LIMIT_RATE} \
  # -O ${FILENAME} "http://${CLIENT}/fdsnws/dataselect/1/query" \
  scp "${CLIENT}${year}/${Net}/${Sta}/${Chan}.D/${Net}.${Sta}.${Loc}.${Chan}.D.${year}.${jday}" \
  "${WORKSPACE}/ARCHIVE" \
  2>&1 >/dev/null || exit_wget=$? ;

  EXIT_STATUS=$(convert_exit ${exit_wget})
  .log 7 "Exit status :" ${EXIT_STATUS}

  if [ "${EXIT_STATUS}" -ne 0 ]; then
    .log 3 ${EXIT_STATUS}
    exit ${EXIT_STATUS};
  fi

done <"${POSTFILE}"


.log 7 "SCP success"
