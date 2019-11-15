#!/bin/bash -e
# Siqaco plugin to get data from the FDSN Web Service, using dataselect
SCRIPTPATH=$(dirname $0)
siqacobin="$(dirname $(dirname ${SCRIPTPATH}}))/bin"
export PATH="${siqacobin}:${SCRIPTPATH}:/usr/local/bin:/usr/bin:/bin"
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
#    This program is part of 'Projet SiQaCo'.                             #
#    It has been financed by RESIF (Réseau sismologique & géodésique      #
#    français )                                                           #
#                                                                         #
#  ***********************************************************************#

# ------------------------------------------------------------------------------
#
#  Development notes :
#
# * Data MUST be written to the WORKSPACE path in an SDS archive:
#
# Please see https://www.seiscomp3.org/doc/applications/slarchive/SDS.html and
# github.com/iris-edu/dataselect/blob/master/doc/dataselect.md#archive-format
#
# ------------------------------------------------------------------------------
#
# * LOGS:
#
# Siqaco will create a log file from the outputs of the plugin. Please use
# the .log funcion when you write your outputs, instead of echo
#
# ------------------------------------------------------------------------------

echo $@
set -o history -o histexpand # only for dev: echo !! prints last command line

usage()
{
  echo "usage : `basename $0` [-h] [--help] [--is_online] [--postfile=<path>]
  [--workspace=<path>] [--data-format=<name>] [--blocksize=<int>]
  [--compression=<name>]
  [--connect-infos=<client:<wsaddress>[?limit_rate=<limit>]>]
  [--log-level=<int>]

Warning: if you are using --is_online, this script will not fetch any data
  "
}

# Help :
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  usage
  echo "
  ## Simple command usage
  -h or --help                  Show this message

  --is_online=CLIENT            Flag to asks if the webservice defined in CLIENT
                                is online and reachable.
                                Returns 0 if it is online, else 3

  ## Fetch data from postfile usage
  --postfile=POSTFILE           Path to the postfile containing the nslc
                                and starttime/endtime of the samples we want to
                                fetch.
                                Defaults to ''.
                See https://www.orfeus-eu.org/data/eida/webservices/dataselect/
                to see the format of postfiles

  --workspace=WORKSPACE         Path to the temporary workspace where data will
                                be written to.
                                Defaults to '../../WORKING_DIR/PATCH/FDSN_WS'

  --data-format=DATA_FORMAT     The format to write your data.
                                Defaults to 'seed'

  --blocksize=BLOCKSIZE         The output block size, in bytes (or 0).
                                Valid blocksize is between 256 and 8192
                                inclusive, and blocksize=2^N (See qmerge -h)
                                Defaults to '4096'

  --compression=COMPRESS        Valid formats are STEIM1, STEIM2, INT_16,
                                INT_32, INT_24, IEEE_FP_SP, IEEE_FP_DP
                                (See qmerge -h)
                                Defaults to 'STEIM2'

  --connect-infos=CONNECT_INFOS A string containing additional informations to
                                connect to the webservice. Must be
                                client:<wsaddress>[?limit_rate=<limit>] where
                                <wsaddress> is the web service url and <limit>
                                is the downloading limit in bytes per seconds.
                                Defaults to 'client:service.iris.edu'

  --log-level                   An integer, between 1 and 3 to define the
                                verbose level for this script
                                [1]=err [2]=warning [3]=debug

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
# command -v dataselect >/dev/null 2>&1 || { echo >&2 "ERROR : dataselect is not \
# installed. Please install dataselect >= 3.20: \
# https://github.com/iris-edu/dataselect"; exit 1; }
if ! [ -x "$(command -v dataselect)" ]; then
  echo >&2 "ERROR : dataselect is not\
  installed. Please install dataselect >= 3.20:\
  https://github.com/iris-edu/dataselect"
  exit 1
fi

DATASELECT_VERSION=$(dataselect -V 2>&1)
VERSION=${DATASELECT_VERSION##*: }

if (( $(echo "${VERSION} <= 3.19" |bc -l) )); then
  echo "Your dataselect software version is ${VERSION}, must be >= 3.20\
  Please install dataselect >= 3.20: https://github.com/iris-edu/dataselect"
  exit 1
fi

# command -v msi >/dev/null 2>&1 || { echo >&2 "ERROR : msi (miniSEED inspector) \
# is not installed. Please install msi \
# https://github.com/iris-edu/msi"; exit 1; }
if ! [ -x "$(command -v dataselect)" ]; then
  echo >&2 "ERROR : msi (miniSEED inspector)\
  is not installed. Please install msi\
  https://github.com/iris-edu/msi"
  exit 1
fi

# command -v qmerge >/dev/null 2>&1 || { echo >&2 "ERROR : qmerge \
# is not installed. Please install qmerge : \
# quake.geo.berkeley.edu/qug/software/ucb/qmerge.2014.329.tar.gz"; exit 1; }
if ! [ -x "$(command -v dataselect)" ]; then
  echo >&2 "ERROR : qmerge \
  is not installed. Please install qmerge : \
  quake.geo.berkeley.edu/qug/software/ucb/qmerge.2014.329.tar.gz"
  exit 1
fi
# Verbose
declare -A LOG_LEVELS
LOG_LEVELS=([1]="err" [2]="warning" [3]="debug")
function .log () {
  local LEVEL=${1}
  shift
  if [[ ${__VERBOSE} -ge ${LEVEL} ]]; then
    echo "[${LOG_LEVELS[$LEVEL]}]" "$@"
  fi
}

# Convert wget exit code to exit status understandable by SiQaCo
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
    *) .log 1 "Unkown ERROR during WGET" ; exit 1 ;;
  esac;
  echo ${EXIT_STATUS}
}

# Function that returns the online status for the client
function is_source_online() {
  local CLIENT=${1}
  if [ "${CLIENT}" = "" ]; then
    CLIENT='service.iris.edu'
  fi
  .log 3 ${CLIENT}
  wget "http://${CLIENT}/fdsnws/dataselect/1/" -q --spider  2>&1 >/dev/null \
  || exit_wget=$? ;

  EXIT_STATUS=$(convert_exit ${exit_wget})
  .log 3 "Exit status :" ${EXIT_STATUS}
  exit ${EXIT_STATUS}
}

# List of inputs
ARGUMENT_LIST=(
    "is_online"
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
        --is_online) ONLINE_FLAG=true; CLIENT=$2; shift 2 ;;

        --postfile) POSTFILE=$2; shift 2 ;;

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

if [ "${__VERBOSE}" = "" ]; then
  __VERBOSE="3"
  .log 3 "Verbose: $__VERBOSE"
fi

if [ ${ONLINE_FLAG} ]; then
  echo "client : ${CLIENT}"
  is_source_online $CLIENT
fi


# Create defaults
if [ "${WORKSPACE}" = "" ]; then
  base=$(dirname $(dirname $(pwd)}))
  if [ ! -d "${base}/WORKING_DIR/TEST/PATCH/" ]; then
    mkdir -pv "${base}/WORKING_DIR/TEST/PATCH/"
    .log 3 "${base}/WORKING_DIR/TEST/PATCH/ created"
  fi
  TEMPDIR=$(mktemp -d -p ${base}/WORKING_DIR/TEST/PATCH/)
  WORKSPACE="${TEMPDIR}/FDSNWS"
  .log 3 "Workspace: $WORKSPACE"
fi
if [ "${DATA_FORMAT}" = "" ]; then
  DATA_FORMAT="seed"
  .log 3 "Data format: $DATA_FORMAT"
fi
if [ "${BLOCKSIZE}" = "" ]; then
  BLOCKSIZE="4096"
  .log 3 "Blocksize: $BLOCKSIZE"
fi
if [ "${COMPRESS}" = "" ]; then
  COMPRESS="STEIM2"
  .log 3 "Compress: $COMPRESS"
fi
if [ "${CONNECT_INFOS}" = "" ]; then
  CONNECT_INFOS="client:service.iris.edu"
  .log 3 "Connect infos: $CONNECT_INFOS"
fi


# If we have just want to know if the plugin is online:

# Check that the postfile exists
if [ ! -e ${POSTFILE} ]; then
  .log 1 "${POSTFILE} doesn't exist, exiting...."
  exit 1
fi

# Create workspace directory if it doesn't exist yet
if [ ! -d "${WORKSPACE}" ]; then
  mkdir -pv "${WORKSPACE}"
  .log 3 "${WORKSPACE} created"
fi

################# THIS IS WERE THE MAGIC HAPPENS. (or not) #####################

# Get client name
CLIENT=$(echo ${CONNECT_INFOS} | awk -F '[:?=&]' '{print $2}')
.log 3 "client: "${CLIENT}
LIMIT_RATE=$(echo ${CONNECT_INFOS} | awk -F '[:?=&]' '{print $4}')
if [ "${LIMIT_RATE}" = "" ]; then
  LIMIT_RATE="0k"
fi
.log 3 "Limit rate: ${LIMIT_RATE}"

now="$(date +'%s')"

# Create a temp directory (will be erase at the end of this script if succeded)
# TEMP_DIR=$(mktemp -d -p ${WORKSPACE}) || { .log 1 \
# "Failed to create temp dir"; exit 1; }
# FILENAME="${TEMP_DIR}/${now}.ws_raw.${DATA_FORMAT}"
FILENAME=$(mktemp ${WORKSPACE}/XXXXXX.ws_wget.${DATA_FORMAT})
.log 3 "Filename: ${FILENAME}"

wget -q --post-file=${POSTFILE} --limit-rate=${LIMIT_RATE} \
-O ${FILENAME} "http://${CLIENT}/fdsnws/dataselect/1/query" \
2>&1 >/dev/null || exit_wget=$? ;

EXIT_STATUS=$(convert_exit ${exit_wget})
.log 3 "Exit status :" ${EXIT_STATUS}

if [ "${EXIT_STATUS}" -ne 0 ]; then
  .log 1 ${EXIT_STATUS}
  exit ${EXIT_STATUS};
fi

.log 3 "WGET success"

if ! ( [ -f ${FILENAME} ] && [ -s ${FILENAME} ] ) ; then
  .log 1 "No data found"
  exit 2;
fi

################# END OF WERE THE MAGIC HAPPENS. (or not) #####################

correct_seed.sh --log-level=${__VERBOSE} \
  --input-file=${FILENAME} \
  --output-dir=${WORKSPACE} \
  --blocksize=${BLOCKSIZE} \
  --encoding=${COMPRESS}

.log 3 "FDSNWS Script finished with success"
exit 0
