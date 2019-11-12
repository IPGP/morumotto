#! /bin/bash
if [ "$#" != "3" ]
then
	echo -e "\nUsage: $0   STALIST YEAR  datapath\n"
	exit
fi
racine=/data1/volobsis/miniseed
logfile=${racine}/out/$USER/log/$(date +%Y%m%d%H%M)$(basename  $0 | cut -d. -f1).log 
echo -e "$(date +%Y%m%d%H%M) execution: $0 $1 $2 \n\n" >> $logfile 
#Check-list_PathsArchive.sh $1 $2   >> $logfile
#Check_DataFiles-vs-DatalessChannels.sh  $1 $2 $3  >> $logfile
dataless_vs_SDS.sh $1 $2 $3  >> $logfile
