#!/bin/bash -e
# Morumotto plugin to copy data from a local directory, using dataselect
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
# * Data MUST be written to the WORKSPACE path in an SDS archive:
#
# Please see https://www.seiscomp3.org/doc/applications/slarchive/SDS.html and
# github.com/iris-edu/dataselect/blob/master/doc/dataselect.md#archive-format
#
# ------------------------------------------------------------------------------
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
  echo "usage : `basename $0` [-h] [--help] [--is_online] [--postfile=<path>]
  [--workspace=<path>] [--data-format=<name>] [--blocksize=<int>]
  [--compression=<name>][--cpu-limit=<int>]
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

  --is_online=DIR               Flag to asks if the directory defined in DIR
                                exists.
                                Returns 0 if so, else 3

  ## Fetch data from postfile usage
  --postfile=POSTFILE           Path to the postfile containing the nslc
                                and starttime/endtime of the samples we want to
                                fetch.
                                Defaults to ''.
                See https://www.orfeus-eu.org/data/eida/webservices/dataselect/
                to see the format of postfiles

  --workspace=WORKSPACE         Path to the temporary workspace where data will
                                be written to.
                                Defaults to '../../WORKING_DIR/PATCH/LOCAL'

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

  --cpu_limit                   An integer, which is the CPU percentage allowed
                                for this plugin. See cpulimit manual

  --connect-infos=CONNECT_INFOS A string containing additional informations to
                                access data. Must be
                                dir:<directory>&structure:<struct_type>
                                [?limit_rate=<limit>] where <directory> is the
                                root directory for the data archive,
                                <struct_type> is the type of data structure and
                                <limit> sets the copying limit in KBytes/cec.
                                Defaults is empty, so connect-infos is not set,
                                the scripts just exits to prevent any other kind
                                of error

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
if [ "$#" -gt 8 ] || [ -z "$1" ]; then
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
  if [[ ${__VERBOSE} -ge ${LEVEL} ]]; then
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

# Function that returns the online status for the client
function is_source_online() {
  local DATA_DIR=${1}
  if [ -d "${DATA_DIR}" ]; then
    exit 0;
  else
    .log 3 "Directory doesn't exist. Exiting..."
    exit 3
  fi
}

############## CHECKING INPUTS ##############

# List of inputs
ARGUMENT_LIST=(
    "is_online"
    "postfile"
    "workspace"
    "data-format"
    "blocksize"
    "compression"
    "connect-infos"
    "cpu-limit"
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
        --is_online) ONLINE_FLAG=true; DIR=$2; shift 2 ;;

        --postfile) POSTFILE=$2; shift 2 ;;

        --workspace) WORKSPACE=$2; shift 2 ;;

        --data-format) DATA_FORMAT=$2; shift 2 ;;

        --blocksize) BLOCKSIZE=$2; shift 2 ;;

        --compression) COMPRESS=$2; shift 2 ;;

        --cpu-limit) CPU_LIMIT=$2; shift 2 ;;

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

# If we have just want to know if the plugin is online:
if [ ${ONLINE_FLAG} ]; then
  DATA_DIR=$(echo ${DIR} | awk -F '[:?=&]' '{print $1}')
  is_source_online $DATA_DIR
fi

# Create defaults
if [ "${WORKSPACE}" = "" ]; then
  base=$(dirname $(dirname $(pwd)}))
  if [ ! -d "${base}/WORKING_DIR/PATCH/" ]; then
    mkdir -pv "${base}/WORKING_DIR/PATCH/"
    .log 3 "${base}/WORKING_DIR/PATCH/ created"
  fi
  TEMPDIR=$(mktemp -d -p ${base}/WORKING_DIR/PATCH/)
  WORKSPACE="${TEMPDIR}/LOCAL"
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

# Check that we provided some connection informations
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

################# FETCH DATA ###################

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

FILENAME=$(mktemp ${WORKSPACE}/XXXXXX.local_cp.${DATA_FORMAT})
.log 3 "Filename: ${FILENAME}"

# 2. Define file pattern
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


# 3. Parse POSTFILE into a input list file and a selection file
INPUT_LIST=$(mktemp ${WORKSPACE}/XXXXXX.input.list)
SELECT_FILE=$(mktemp ${WORKSPACE}/XXXXXX.select.list)
echo "#net  sta  loc  chan  qual  start  end" > ${SELECT_FILE}
while IFS= read -r line; do
  if ! [[ "${line}" = "\#*" ]]; then
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
      exit 1
    fi
    declare -a FILE_ARRAY=()
    if (( ${year_end} > ${year_start} )); then
      # handle leap years"
      if isleap ${year_start}; then
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
        FILE_ARRAY+=("${SOURCE_DIR}${_FILE}")
      done
      for jday in ${jday_array_year2[@]}; do
        _FILE=${FILE_PATTERN}
        _FILE=${_FILE//"%Y"/${year_end}}
        _FILE=${_FILE//"%j"/${jday}}
        _FILE=${_FILE//"%n"/${net}}
        _FILE=${_FILE//"%s"/${sta}}
        _FILE=${_FILE//"%l"/${loc}}
        _FILE=${_FILE//"%c"/${chan}}
        FILE_ARRAY+=("${SOURCE_DIR}${_FILE}")
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
        echo ${FILE} >> ${INPUT_LIST}
      fi
    done
  fi
done < ${POSTFILE}

if ! [[ -s ${INPUT_LIST} ]]; then
  .log 1 "No data found"
  exit 2;
fi

# 4. Copy data using dataselect, to a single output file
cpulimit -l ${CPU_LIMIT} -f -q -- dataselect -Ps -s ${SELECT_FILE} \
+o ${FILENAME} @${INPUT_LIST}

############ CORRECT DATA ###############

correct_seed.sh --log-level=${__VERBOSE} \
  --input-file=${FILENAME} \
  --output-dir=${WORKSPACE} \
  --blocksize=${BLOCKSIZE} \
  --encoding=${COMPRESS}

rm -f ${INPUT_LIST}
rm -f ${SELECT_FILE}
.log 3 "LOCAL Script finished with success"
exit 0
