#! /bin/bash
if [ "$#" != "2" ]
then
	echo -e "\nUsage: $0 dataless_file_name network_code (G, WI, PF, GL or MQ)\n"
	exit
fi

racine=/data1/volobsis/miniseed
logfile=${racine}/out/$USER/log/$(date +%Y%m%d%H%M)$(basename  $0 | cut -d. -f1).log 
verseedlog=${racine}/out/$USER/log/$(date +%Y%m%d%H%M).$2.verseed.out 
echo -e "$(date +%Y%m%d%H%M) execution of: $0 $1 $2 \n\n"  >> $logfile 
Check-list_dataless-alone.sh $1 $2 >> $logfile 2>&1
verseed -4 $1  2>> $verseedlog  1>>$verseedlog
