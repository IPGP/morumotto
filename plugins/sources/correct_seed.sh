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


echo $@
set -o history -o histexpand # only for dev: echo !! prints last command line

usage()
{
  echo "usage : `basename $0` [-h] [--help] [--log-level=<int>]
  [--blocksize=<int>] [--encoding=<name>] [--input-file=<name>]
  "
}

# Help :
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  usage
  echo "
  ## Simple command usage
  -h or --help                  Show this message

  --input-file=INFILE           The miniseed input file to check and correct

  --output-dir=OUTDIR           The directory where to put the resulting
                                Net.Sta.Loc.Chan files

  --blocksize=BLOCKSIZE         The output block size, in bytes (or 0).
                                Valid blocksize is between 256 and 8192
                                inclusive, and blocksize=2^N (See qmerge -h)
                                Defaults to '4096'

  --encoding=ENCODING           Valid formats are STEIM1, STEIM2, INT_16,
                                INT_32, INT_24, IEEE_FP_SP, IEEE_FP_DP
                                (See qmerge -h)
                                Defaults to 'STEIM2'

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
if [ "$#" -gt 5 ] || [ -z "$1" ]; then
  echo "ERROR: wrong usage"
  usage
  exit 1
fi

# Check requirements
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

if ! [ -x "$(command -v msi)" ]; then
  echo >&2 "ERROR : msi (miniSEED inspector)\
  is not installed. Please install msi\
  https://github.com/iris-edu/msi"
  exit 1
fi

if ! [ -x "$(command -v qmerge)" ]; then
  echo >&2 "ERROR : qmerge \
  is not installed. Please install qmerge : \
  quake.geo.berkeley.edu/qug/software/ucb/qmerge.2014.329.tar.gz"
  exit 1
fi

# Verbose levels
declare -A LOG_LEVELS
LOG_LEVELS=([1]="err" [2]="warning" [3]="debug")
function .log () {
  local LEVEL=${1}
  shift
  if [[ ${__VERBOSE} -ge ${LEVEL} ]]; then
    echo "[${LOG_LEVELS[$LEVEL]}]" "$@"
  fi
}

# List of inputs
ARGUMENT_LIST=(
    "input-file"
    "output-dir"
    "blocksize"
    "encoding"
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
        --input-file) INFILE=$2; shift 2 ;;

        --output-dir) OUTDIR=$2; shift 2 ;;

        --blocksize) BLOCKSIZE=$2; shift 2 ;;

        --encoding) ENCODING=$2; shift 2 ;;

        --log-level) __VERBOSE=$2; shift 2 ;;

        --) shift ; break ;;
        *) echo "Wrong call to the script!" usage ; exit 1 ;;
    esac
done

# Initialisation complete, let's go to work
###########################################


# Check block size and encoding type, change if necessary
CORRECTED_FILE=$(mktemp ${OUTDIR}/XXXXXX.ws_raw_corrected.seed)

# Map encoding format string to SEED blockette 1000 value
case ${ENCODING} in
  "INT_16")
    SEED_encoding_format_val=1
    ;;
  "INT_24")
    SEED_encoding_format_val=2
    ;;
  "INT_32")
    SEED_encoding_format_val=3
    ;;
  "IEEE_FP_SP")
    SEED_encoding_format_val=4
    ;;
  "IEEE_FP_DP")
    SEED_encoding_format_val=5
    ;;
  "STEIM1")
    SEED_encoding_format_val=10
    ;;
  "STEIM2")
    SEED_encoding_format_val=11
    ;;
  *)
    .log 1 "Unknown encoding format ${ENCODING}"
    exit 5
    ;;
esac

# Check SEED blockette 1000 values for encoding format and blocksize
BAD_HEADERS_FLAGS=( $(msi -p ${INFILE}  | sed 's/(//g;s/)//g' | \
  awk -F":" -v blocking="${BLOCKSIZE}" -v coding="${SEED_encoding_format_val}" \
'{
  if ( $1~/encoding.*/ && $3!~coding )
  {
          print "bad_encoding"
  }
  if ( $1~/record length.*/ && 2^$3!~blocking)
  {
          print "bad_blocking"
  }
}' | sort -u) )

# Check if we found any error to correct
if (( ${#BAD_HEADERS_FLAGS[*]} ))
then
  QMERGE_OPT="-o ${CORRECTED_FILE}"
  for i in $(seq 0 $((${#BAD_HEADERS_FLAGS[*]} - 1)))
  do
    case "${BAD_HEADERS_FLAGS[i]}" in
      "bad_encoding")
        QMERGE_OPT="${QMERGE_OPT} -r -O ${ENCODING}"
        ;;
      "bad_blocking")
        QMERGE_OPT="${QMERGE_OPT} -b ${BLOCKSIZE}"
        ;;
    esac
  done
  qmerge ${QMERGE_OPT} ${INFILE} || { .log 1 \
  "QMERGE failed to change encoding and/or block size"; exit 5; }
  .log 3 "QMERGE SUCCESS"
else
  cp ${INFILE} ${CORRECTED_FILE}
  .log 3 "No encoding/blocksize to change, file simply copied"
fi
rm -f ${INFILE}

#
# Demux data and sort them in the appropriate structure.
dataselect -szs -CHAN ${OUTDIR} ${CORRECTED_FILE}
if [ $? -ne 0 ]; then
  .log 1 "Dataselect error"
  exit 5
fi
rm -f ${CORRECTED_FILE}
