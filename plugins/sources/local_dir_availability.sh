#!/bin/bash -e
# Morumotto plugin to get data availability from local directory
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

if [ "${__VERBOSE}" = "" ]; then
  __VERBOSE="3"
  .log 3 "Verbose: $__VERBOSE"
fi
# Create defaults
if [ "${WORKSPACE}" = "" ]; then
  base=$(dirname $(dirname $(pwd)))
  WORKSPACE="${base}/WORKING_DIR"
  .log 3 "Workspace: $WORKSPACE"
fi
if [ "${CONNECT_INFOS}" = "" ]; then
  .log 1 "Connect infos is empty, exiting..."
  exit 1
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

if [ ! -d "${WORKSPACE}/AVAILABILITY" ]; then
  mkdir -p  "${WORKSPACE}/AVAILABILITY"
  .log 3 "${WORKSPACE}/AVAILABILITY created"
fi

# 1. Get PATH
SOURCE_DIR=$(echo ${CONNECT_INFOS} | awk -F '[:?=&]' '{print $2}')
.log 3 "Source directory: "${SOURCE_DIR}
SOURCE_STRUCTURE=$(echo ${CONNECT_INFOS} | awk -F '[:?=&]' '{print $4}')
.log 3 "Source data structure: "${SOURCE_STRUCTURE}
LIMIT_RATE=$(echo ${CONNECT_INFOS} | awk -F '[:?=&]' '{print $6}')
if [ "${LIMIT_RATE}" = "" ]; then
  LIMIT_RATE="0k"
fi
.log 3 "Limit rate: ${LIMIT_RATE}"

AVAILFILENAME="$(basename ${POSTFILE/"post."/""})"
FILENAME="${WORKSPACE}/AVAILABILITY/${AVAILFILENAME}"

.log 3 "Filename: ${FILENAME}"

case ${SOURCE_STRUCTURE} in
  "CHAN")FILE_PATTERN="/%n.%s.%l.%c";;
  # "QCHAN")FILE_PATTERN="/%n.%s.%l.%c.%q";;
  # "CDAY")FILE_PATTERN="/%n.%s.%l.%c.%Y:%j:#H:#M:#S";;
  "SDAY")FILE_PATTERN="/%n.%s.%Y:%j";;
  "BUD")FILE_PATTERN="/%n/%s/%s.%n.%l.%c.%Y.%j";;
  "SDS")FILE_PATTERN="/%Y/%n/%s/%c.D/%n.%s.%l.%c.D.%Y.%j";;
  # "CSS")FILE_PATTERN="/%Y/%j/%s.%c.%Y:%j:#H:#M:#S";;
  *) .log 1 "Structure unknown, exiting..."; exit 1;;
esac

# 2. Parse POSTFILE into a input list file and a selection file
echo "#n s     l  c                      earliest                      latest" > ${FILENAME}

while IFS= read -r line; do
  if ! [[ ${line} == mergequality* || ${line} == mergesamplerate* || ${line} == format* ]]; then
    net=$(echo "${line}" | cut -d' ' -f1)
    sta=$(echo "${line}" | cut -d' ' -f2)
    loc=$(echo "${line}" | cut -d' ' -f3)
    chan=$(echo "${line}" | cut -d' ' -f4)
    start=$(echo "${line}" | cut -d' ' -f5)
    end=$(echo "${line}" | cut -d' ' -f6)
    filedate_start=$(date -d "${start}" +'%Y-%m-%dT%H:%M:%S')
    filedate_end=$(date -d "${end}" +'%Y-%m-%dT%H:%M:%S')
    year_start=$(date -d ${filedate_start} '+%Y')
    jday_start=$(date -d ${filedate_start} '+%j')
    year_end=$(date -d ${filedate_end} '+%Y')
    jday_end=$(date -d ${filedate_end} '+%j')

    # Find all files between start and end dates :

    # Note that this will just work for two consecutive years...
    if (( ${year_end} - ${year_start} > 1 )); then
      .log 1 "ERROR, you are trying to get data over more than 2 consecutive"\
      " years, the LOCAL_DIR plugin doesn't know how to handle this"
    fi
    declare -a FILE_ARRAY=()
    if (( ${year_end} > ${year_start} )); then
      # handle leap years"
      if (( ${year_start} %4 )); then
        temp_end_jday=366
      else
        temp_end_jday=365
      fi
      declare -a jday_array_year1=$(seq ${jday_start} ${temp_end_jday})
      declare -a jday_array_year2=$(seq 1 ${jday_end})

      for jday in ${jday_array_year1[@]}; do
        _FILE=${FILE_PATTERN}
        _FILE=${_FILE//"%Y"/${year_start}}
        _FILE=${_FILE//"%j"/${jday}}
        _FILE=${_FILE//"%n"/${net}}
        _FILE=${_FILE//"%s"/${sta}}
        _FILE=${_FILE//"%l"/${loc}}
        _FILE=${_FILE//"%c"/${chan}}
        FILE_ARRAY+=("${_FILE}")
      done
      for jday in ${jday_array_year2[@]}; do
        _FILE=${FILE_PATTERN}
        _FILE=${_FILE//"%Y"/${year_end}}
        _FILE=${_FILE//"%j"/${jday}}
        _FILE=${_FILE//"%n"/${net}}
        _FILE=${_FILE//"%s"/${sta}}
        _FILE=${_FILE//"%l"/${loc}}
        _FILE=${_FILE//"%c"/${chan}}
        FILE_ARRAY+=("${_FILE}")
      done
    else
      for jday in $(seq ${jday_start} ${jday_end}); do
        _FILE=${FILE_PATTERN}
        _FILE=${_FILE//"%Y"/${year_start}}
        _FILE=${_FILE//"%j"/${jday}}
        _FILE=${_FILE//"%n"/${net}}
        _FILE=${_FILE//"%s"/${sta}}
        _FILE=${_FILE//"%l"/${loc}}
        _FILE=${_FILE//"%c"/${chan}}
        FILE_ARRAY+=("${SOURCE_DIR}${_FILE}")
      done
    fi
    for FILE in ${FILE_ARRAY[@]}; do
      if [ -f ${FILE} ];then
        MSI_FILE=$(mktemp ${WORKSPACE}/AVAILABILITY/msi_output_XXXXXXXX)
        msi -T -tf 1 ${FILE} | tr -s " " >> ${MSI_FILE}
        while IFS= read -r line; do
          if ! echo "${line}" | grep -q "Source\|Total"; then
            code=$(echo "${line}" | cut -d' ' -f1)
            net=$(echo "${code}" | cut -d'_' -f1)
            sta=$(echo "${code}" | cut -d'_' -f2)
            loc=$(echo "${code}" | cut -d'_' -f3)
            chan=$(echo "${code}" | cut -d'_' -f4)
            start=$(echo "${line}" |cut -d' ' -f2)
            end=$(echo "${line}" | cut -d' ' -f3)
            echo "${net} ${sta}   ${loc} ${chan} ${start}Z ${end}Z" >> ${FILENAME}
          fi
        done < ${MSI_FILE}
        rm -f ${MSI_FILE}
      fi
    done
  fi
done < ${POSTFILE}

if ! [ -s ${FILENAME} ]; then
  .log 1 "No data found "
else
  .log 3 "local_dir_availability script finished with success"
fi
exit 0
