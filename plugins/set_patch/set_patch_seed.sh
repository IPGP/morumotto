#!/bin/bash -i
# Morumotto plugin to create patched files with seed format
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


# Note : all temp files created in the current directory are not removed
# for debug mode. Morumotto is handling the CURRENT_DIR, and will remove it
# when the associated request has succedded (except debug mode)


SCRIPTPATH=$(dirname $0)
morumottobin="$(dirname $(dirname ${SCRIPTPATH}}))/bin"
export PATH="${morumottobin}:${SCRIPTPATH}:/usr/local/bin:/usr/bin:/bin"

function convert_prio() {
  # This is a hack, as dataselect gives higher priority to highest quality data
  # See https://github.com/iris-edu/dataselect/blob/master/doc/dataselect.md#description
  # M > Q > D > R
  local prio=${1}
  case ${prio} in
    1) q_temp="M" ;;
    2) q_temp="Q" ;;
    3) q_temp="D" ;;
    4) q_temp="R" ;;
    *) q_temp="R" ;;
  esac;
  echo ${q_temp}
}


CURRENT_DIR=$1
GAP_FILELIST=$2
PATCH_FILELIST=$3
GAP_STARTTIME=$(date -d "$4" +'%Y,%j,%H,%M,%S.%N')
GAP_ENDTIME=$(date -d "$5" +'%Y,%j,%H,%M,%S.%N')
GAP_START_UNIXTIME=$(date -d "$4" +'%s')
GAP_END_UNIXTIME=$(date -d "$5" +'%s')
GAP_LAST_SAMPLE=$(date -d "$5 0.0001 second ago" +'%Y,%j,%H,%M,%S.%N')
QUALITY=$6



echo "start $4 end $5,"
MERGE_FILELIST=$(mktemp ${CURRENT_DIR}/merge_XXXXXX.list)
# 1) Clean data between start and end of gap
if ! [ ${GAP_FILELIST} == "empty" ]; then
  ORIG_START_FILE=$(mktemp ${CURRENT_DIR}/original_start_XXXXXX.seed)
  ORIG_END_FILE=$(mktemp ${CURRENT_DIR}/original_end_XXXXXX.seed)
  dataselect -szs -Ps -Pe  -te ${GAP_STARTTIME} -o "${ORIG_START_FILE}" @${GAP_FILELIST} 2>&1 >/dev/null
  dataselect -szs -Ps -Pe  -ts ${GAP_ENDTIME} -o "${ORIG_END_FILE}" @${GAP_FILELIST} 2>&1 >/dev/null
fi

# 2) Trim patch to fit the gap limits
#   (first sample missing to last sample missing)

while IFS="" read -r line; do
  FILENAME=$(mktemp ${CURRENT_DIR}/patch_XXXXXX.seed)
  PRIORITY=$(echo ${line} | awk -F ';' '{print $1}')
  FILE=$(echo ${line} | awk -F ';' '{print $2}')
  Q_TMP=$(convert_prio ${PRIORITY})
  dataselect -szs -Ps -Pe -Q ${Q_TMP} -ts ${GAP_STARTTIME} -te ${GAP_LAST_SAMPLE} -o ${FILENAME} ${FILE} 2>&1 >/dev/null
  echo -e ${FILENAME} >> ${MERGE_FILELIST}
done < ${PATCH_FILELIST}

# 3) Merge patch from 2 into the cleaned data from 1
OUTPUT=$(mktemp ${CURRENT_DIR}/XXXXXX.patched.seed)
PATCH_TMP=$(mktemp -d --tmpdir=${CURRENT_DIR})

# Split all cleaned patch data into one file per miniSEED record
# dataselect -szs -A ${PATCH_TMP}/%Y.%j.%H.%M.%S.%q.patch @${MERGE_FILELIST}
# /!\ THIS DOESN'T WORK
# --> TOO MUCH SAMPLES, must split work hour by hour

if ! [ -z ${ORIG_START_FILE} ] && [ -s ${ORIG_START_FILE} ]; then
  dataselect -szs -Q ${QUALITY} +o ${OUTPUT} ${ORIG_START_FILE} 2>&1 >/dev/null
fi
for i in $(seq ${GAP_START_UNIXTIME} 3600 ${GAP_END_UNIXTIME}); do

  # Split all cleaned patch data into one file per miniSEED record
  start=$(date -d "1970-01-01 +$i seconds" +'%Y,%j,%H,%M,%S,%N')
  end=$(date -d "1970-01-01 +$i seconds +3600 seconds" +'%Y,%j,%H,%M,%S,%N')
  dataselect -szs -ts $start -te $end -A ${PATCH_TMP}/%Y.%j.%H.%M.%S.%q.patch @${MERGE_FILELIST} 2>&1 >/dev/null
  if ! [ -z "$(ls -A ${PATCH_TMP})" ]; then
    # Merge all records, by chronological order into the output file
    # Set the correct quality flag
    dataselect -szs -Ps -Q ${QUALITY} +o ${OUTPUT} ${PATCH_TMP}/????.???.??.??.??.?.patch 2>&1 >/dev/null
    rm ${PATCH_TMP}/????.???.??.??.??.?.patch 2>&1 >/dev/null
  fi
done
if ! [ -z ${ORIG_START_FILE} ] && [ -s ${ORIG_END_FILE} ]; then
  dataselect -szs -Q ${QUALITY} +o ${OUTPUT} ${ORIG_END_FILE} 2>&1 >/dev/null
fi

rm -rf ${PATCH_TMP}

# 4) Check for overlaps and correct them
OVERLAPS="${CURRENT_DIR}/overlaps"
msi -G ${OUTPUT} -gmax 0 > ${OVERLAPS}
if [[ $(tail -1 ${OVERLAPS} | awk '{print $2}') -ne 0 ]]; then
  echo "Removing overlaps"
  SDRTEMP_DIR=$(mktemp -d -p ${CURRENT_DIR})
  cd ${SDRTEMP_DIR}
  sdrsplit -C ${OUTPUT} 2>&1 >/dev/null
  cd ..
  # HERE : HANDLE LEAP SECONDS
  dataselect -szs -Ps -o ${OUTPUT} ${SDRTEMP_DIR}/* 2>&1 >/dev/null
  rm -rf ${SDRTEMP_DIR}
fi
rm ${OVERLAPS}

echo "Patched data: $(msi -tg ${OUTPUT} 2>&1)"
# 5) Split file to SDS, from 00:00:00.0000000 to 23:59:59.990000 with -Sd option
dataselect -Ps -Sd -SDS "${CURRENT_DIR}/SDS/" ${OUTPUT} 2>&1 >/dev/null

echo "SET PATCH FINISHED WITH SUCCESS"
exit 0
