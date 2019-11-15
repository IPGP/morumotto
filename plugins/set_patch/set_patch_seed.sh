#!/bin/bash -i
# Siqaco plugin to create patched files with seed format
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

# Note : all temp files created in the current directory are not removed
# for debug mode. Siqaco is handling the CURRENT_DIR, and will remove it
# when the associated request has succedded (except debug mode)

CURRENT_DIR=$1
GAP_FILELIST=$2
PATCH_FILELIST=$3
GAP_STARTTIME=$4
GAP_ENDTIME=$5
QUALITY=$6

echo "start $4 end $5,"
MERGE_FILELIST=$(mktemp ${CURRENT_DIR}/merge_XXXXXX.list)
# 1) Clean data between start and end of gap
if ! [ ${GAP_FILELIST} == "empty" ]; then
  ORIG_START_FILE=$(mktemp ${CURRENT_DIR}/original_start_XXXXXX.seed)
  ORIG_END_FILE=$(mktemp ${CURRENT_DIR}/original_end_XXXXXX.seed)
  qmerge -a -T -F ${GAP_FILELIST} -t ${GAP_STARTTIME} -o "${ORIG_START_FILE}" 2>&1 >/dev/null
  # dataselect -szs -Ps -Pe  -te ${GAP_STARTTIME} -o "${ORIG_START_FILE}" @${GAP_FILELIST}
  echo ${ORIG_START_FILE} >> ${MERGE_FILELIST}
  qmerge -a -T -F ${GAP_FILELIST} -f ${GAP_ENDTIME} -o "${ORIG_END_FILE}" 2>&1 >/dev/null
  # dataselect -szs -Ps -Pe  -ts ${GAP_ENDTIME} -o "${ORIG_END_FILE}" @${GAP_FILELIST}
  echo ${ORIG_END_FILE} >> ${MERGE_FILELIST}
  # rm -f ${TEMP_FILE}

fi

# 2) Trim patch to fit the gap limits
#   (first sample missing to last sample missing)

# /!\ Priority : /!\
while IFS="" read -r line; do
  FILENAME=$(mktemp ${CURRENT_DIR}/patch_XXXXXX.seed)
  TEMP_FILE=$(mktemp ${CURRENT_DIR}/temp_XXXXXX.seed)
  # dataselect -szs -Ps -Pe -ts ${GAP_STARTTIME} -te ${GAP_ENDTIME} -o ${FILENAME} ${line}
  qmerge -a -T ${line} -f ${GAP_STARTTIME} -o ${TEMP_FILE}
  qmerge -a -T ${TEMP_FILE} -t ${GAP_ENDTIME} -o ${FILENAME} 2>&1 >/dev/null
  echo -e ${FILENAME} >> ${MERGE_FILELIST}
  rm -f ${TEMP_FILE}
done < ${PATCH_FILELIST}

# 3) Merge patch from 2 into the cleaned data from 1
OUTPUT=$(mktemp ${CURRENT_DIR}/XXXXXX.patched.seed)
PATCH_TMP=$(mktemp -d --tmpdir=${CURRENT_DIR})
# Split all cleaned patch data into one file per miniSEED record
# dataselect -szs -A ${PATCH_TMP}/%Y.%j.%H.%M.%S.%F.patch @${MERGE_FILELIST}

# Merge all records, by chronological order into the output file
# Set the correct quality flag
# dataselect -szs -Q ${QUALITY} -o ${OUTPUT} ${PATCH_TMP}/????.???.??.??.??.????.patch
# rm -rf ${PATCH_TMP}

qmerge -F ${MERGE_FILELIST} -R ${QUALITY} -o ${OUTPUT} 2>&1 >/dev/null


# 4) Check for overlaps and correct them
OVERLAPS="${CURRENT_DIR}/overlaps"
msi -G ${OUTPUT} -gmax 0 > ${OVERLAPS}
if [[ $(tail -1 ${OVERLAPS} | awk '{print $2}') -ne 0 ]]; then
  echo "Removing overlaps"
  SDRTEMP_DIR=$(mktemp -d -p ${CURRENT_DIR})
  cd ${SDRTEMP_DIR}
  sdrsplit -C ${OUTPUT} 2>&1 >/dev/null
  # HERE : HANDLE OVERLAPS AND LEAP SECONDS
  cd ..
  qmerge ${SDRTEMP_DIR}/* -o ${OUTPUT} 2>&1 >/dev/null
  # dataselect -szs -Ps -o ${OUTPUT} ${SDRTEMP_DIR}/*

  rm -rf ${SDRTEMP_DIR}
fi
rm ${OVERLAPS}

echo "Patched data: $(msi -tg ${OUTPUT} 2>&1)"
# 5) Split file to SDS, from 00:00:00.0000000 to 23:59:59.9999999 with -Sd option
dataselect -Ps -Sd -SDS "${CURRENT_DIR}/SDS/" ${OUTPUT} 2>&1 >/dev/null

echo "SET PATCH FINISHED WITH SUCCESS"
exit 0
