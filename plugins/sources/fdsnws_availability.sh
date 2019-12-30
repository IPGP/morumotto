#!/bin/bash -e
# Morumotto plugin to get data availability for the iris FDSN Web Service

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

# ------------------------------------------------------------------------------
#
#  Development notes :
#
# * LOGS:
#
# Morumotto will create a log file from the outputs of the plugin. Please use
# the .log funcion when you write your outputs, instead of echo
#
# ------------------------------------------------------------------------------
SCRIPTPATH=$(dirname $0)
morumottobin="$(dirname $(dirname ${SCRIPTPATH}}))/bin"
export PATH="${morumottobin}:${SCRIPTPATH}:/usr/local/bin:/usr/bin:/bin"
check_requirements.sh

echo $@
set -o history -o histexpand # only for dev: echo !! prints last command line

usage()
{
  echo "usage : `basename $0` [-h] [--help] [--postfile=<path>]
  [--workspace=<path>]
  [--connect-infos=<client:<wsaddress>[?limit_rate=<limit>]>]
  [--log-level=<int>]
  "
}

# Help :
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  usage
  echo "

  -h or --help                  Show this message

  --postfile=POSTFILE           Path to the postfile containing the nslc
                                and starttime/endtime of the samples we want to
                                fetch.
                                Defaults to ''.
                See https://www.orfeus-eu.org/data/eida/webservices/dataselect/
                to see the format of postfiles

  --workspace=WORKSPACE         Path to the temporary workspace where data will
                                be written to.
                                Defaults to '../../WORKING_DIR'

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
if [ "$#" -gt 4 ] || [ -z "$1" ]; then
  echo "ERROR: wrong usage"
  usage
  exit 1
fi

# Verbose
declare -A LOG_LEVELS
LOG_LEVELS=([1]="err" [2]="warning" [3]="debug")
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
    *) .log 1 "Unkown ERROR during WGET" ; exit 1 ;;
  esac;
  echo ${EXIT_STATUS}
}

# List of inputs
ARGUMENT_LIST=(
    "availability"
    "postfile"
    "workspace"
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
        --postfile) POSTFILE=$2; shift 2 ;;

        --workspace) WORKSPACE=$2; shift 2 ;;

        --connect-infos) CONNECT_INFOS=$2; shift 2 ;;

        --log-level) __VERBOSE=$2; shift 2 ;;

        --) shift ; break ;;
        *) echo "Wrong call to the script!" usage ; exit 1 ;;
    esac
done


# Create defaults
if [ "${WORKSPACE}" = "" ]; then
  base=$(dirname $(dirname $(pwd)))
  WORKSPACE="${base}/WORKING_DIR"
  .log 3 "Workspace: $WORKSPACE"
fi
if [ "${CONNECT_INFOS}" = "" ]; then
  CONNECT_INFOS="client:service.iris.edu"
  .log 3 "Connect infos: $CONNECT_INFOS"
fi
if [ "${__VERBOSE}" = "" ]; then
  __VERBOSE="3"
  .log 3 "Verbose: $__VERBOSE"
fi

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

# Get client name
CLIENT=$(echo ${CONNECT_INFOS} | awk -F '[:?=&]' '{print $2}')
.log 3 "client: "${CLIENT}
LIMIT_RATE=$(echo ${CONNECT_INFOS} | awk -F '[:?=&]' '{print $4}')
if [ "${LIMIT_RATE}" = "" ]; then
  LIMIT_RATE="0k"
fi
.log 3 "Limit rate: ${LIMIT_RATE}"

if [ ! -d "${WORKSPACE}/AVAILABILITY" ]; then
  mkdir -p  "${WORKSPACE}/AVAILABILITY"
  .log 3 "${WORKSPACE}/AVAILABILITY created"
fi
AVAILFILENAME="$(basename ${POSTFILE/"post."/""})"
FILENAME="${WORKSPACE}/AVAILABILITY/${AVAILFILENAME}"

.log 3 "Filename: ${FILENAME}"
# At the moment, only works for service.iris.edu/irisws. When available, we
# will change http://service.iris.edu/irisws/availability/1/query with
# http://${CLIENT}/fdsnws/availability/1/query
wget --post-file=${POSTFILE} -O ${FILENAME} \
"http://service.iris.edu/irisws/availability/1/query" \
2>&1 >/dev/null || exit_wget=$? ;


EXIT_STATUS=$(convert_exit ${exit_wget})
# .log 3 "Exit status :" ${EXIT_STATUS}

# if ! ( [ -f ${FILENAME} ] && [ -s ${FILENAME} ] ) ; then
#   .log 2 "Inventory not available"
#   exit 2;
# else
#   # In case of a problem, we add the client info to the top of the
#   # availability file
#   echo "# CLIENT : http://service.iris.edu/irisws/availability/1/query" |\
#   cat - ${FILENAME} > temp && mv temp ${FILENAME}
#   # When available, we need to change the url with
#   # http://"${CLIENT}"/fdsnws/availability/1/query
#   exit ${EXIT_STATUS};
# fi
if [ ${exit_wget} ]; then
  .log 3 " ERROR while connecting to Webservice, exit status :" ${exit_wget}
  exit ${EXIT_STATUS}
else
  .log 3 "fdsnws_availability script finished with success"
  exit 0
fi
