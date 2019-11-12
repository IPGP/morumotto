#! /bin/bash
if [ "$#" -le  "2" ]
then
	echo $#
        echo -e "\nUsage: $0  'list of files' \n"
        exit
fi
racine=/data1/volobsis/miniseed
logfile=${racine}/out/$USER/log/$(date +%Y%m%d%H%M)SDSheaders.log 
Check-list_Chan.sh $*   >  $logfile  2>&1
logfile=${racine}/out/$USER/log/$(date +%Y%m%d%H%M)SDSOverlaps.log 
Check-Overlaps.sh $* | sort -u >  $logfile 2>&1
