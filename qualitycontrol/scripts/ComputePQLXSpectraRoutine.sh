#! /bin/bash

#Aurelien Mordret 2013 ComputePQLXSpectraRoutine.sh
#Jean-Marie Saurel 2017 : process $CPU files at a time


PQLXBIN=/opt/PQLX/PROD/bin/LINUX
CPUs=8

if [ "$#" != "6" ]
then
	echo -e "\nUsage: $0 STALIST mainpath YYYY DDDbeg DDDend dbName\n"
	exit
fi
racine=/data1/volobsis/miniseed
logfile=${racine}/out/$USER/log/$(date +%Y%m%d%H%M)ComputePQLX.log
DBNAME=$6

if [ ! -d $racine/out/$USER/PQLX/log ]
then
 mkdir $racine/out/$USER/PQLX/log
fi
export PQLXLOG=$racine/out/$USER/PQLX/log

computePSDs()
{
# for i in `seq 1 $(cat $racine/out/$USER/PQLX/LISTFILES/current.list|wc -l )`
 for i in `seq 1 $(cat $racine/out/$USER/PQLX/LISTFILES/current.list |awk -v n=${CPUs} 'END{printf("%d", NR/n)}' )`
 do 
#	tail -1  $racine/out/$USER/PQLX/LISTFILES/current.list  > $racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i"
	tail -n ${CPUs}  $racine/out/$USER/PQLX/LISTFILES/current.list  > $racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i"
	cat $racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i" >> $logfile
	${PQLXBIN}/pqlxSrvr --dbName=${DBNAME} --identFile=$racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i" --numCPU=${CPUs}
#	sed '$d'  $racine/out/$USER/PQLX/LISTFILES/current.list -i
	head -n -${CPUs}  $racine/out/$USER/PQLX/LISTFILES/current.list > $racine/out/$USER/PQLX/LISTFILES/tmp.list
	mv $racine/out/$USER/PQLX/LISTFILES/tmp.list $racine/out/$USER/PQLX/LISTFILES/current.list
 done 
 rm  $racine/out/$USER/PQLX/LISTFILES/*
}

################## variables
netcode=`awk '{print $1}' $1 | sort -u`
net=( `awk '{print $1}' $1` )
stalist=( `awk '{print $2}' $1` )
locid=( `awk '{print $4}' $1` )
chan=( `awk ' $3 ~/[EH][HN]/ {print $3}' $1` )
ybeg=( `awk '{print $5}' $1 | awk -F "," '{print $1}'` )
dbeg=( `awk '{print $5}' $1| awk -F "," '{print $2}'` )
yend=( `awk '{print $6}' $1| awk -F "," '{print $1}'` )
dend=( `awk '{print $6}' $1| awk -F "," '{print $2}'` )
cha=( `awk '{print $3}' $1 | awk -F "." '{print $1}'` )

#rm /opt/Tools/VALIDATION_TOOLS/LISTFILES/lst*


if [ -f $racine/out/$USER/PQLX/LISTFILES/current.list ]
then
  echo "previous ComputeSpectra not finished: still "$(cat $racine/out/$USER/PQLX/LISTFILES/current.list | wc -l ) " files to compute. see  $racine/out/$USER/PQLX/LISTFILES/current.list" 
  computePSDs
# for i in `seq 1 $(cat $racine/out/$USER/PQLX/LISTFILES/current.list|wc -l )`
# do 
#	tail -1  $racine/out/$USER/PQLX/LISTFILES/current.list  > $racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i"
#	cat $racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i" >> $logfile
#	${PQLXBIN}/pqlxSrvr --dbName=$6 --identFile=$racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i" --numCPU=4
#	sed '$d'  $racine/out/$USER/PQLX/LISTFILES/current.list -i
# done 
# rm  $racine/out/$USER/PQLX/LISTFILES/*
 exit  
fi



#boucle sur les stations
for i in `seq 0 $((${#stalist[*]} - 1))`
do
		mainpath=$2		
		allpath=`paste -d '/' <(echo "$mainpath") <(echo "$3") <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "${chan[i]}")`
		filename=`paste -d '.' <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "${locid[i]}") <(echo "${chan[i]}")`		
		
		for day in `seq -f %03.0f $4 $5`
		do
				
			fullpath="$allpath/$filename.$3.$day"
			if [[ -a $fullpath ]]
			then
				ls "$fullpath" >> $racine/out/$USER/PQLX/LISTFILES/current.tmp
				#/opt/PQLX/PROD/bin/LINUX/pqlxSrvr --dbName=$6 --identFile=$racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i" --numCPU=4

			else
				echo -e "$fullpath does not exist" >> $logfile
				continue
			fi
		done
done
[[ -f $racine/out/$USER/PQLX/LISTFILES/current.tmp ]] && sort -u  $racine/out/$USER/PQLX/LISTFILES/current.tmp >  $racine/out/$USER/PQLX/LISTFILES/current.list

computePSDs

#for i in `seq 1 $(cat $racine/out/$USER/PQLX/LISTFILES/current.list|wc -l )`
#do 
#	tail -1 $racine/out/$USER/PQLX/LISTFILES/current.list  > $racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i"
#	cat $racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i" >> $logfile
#        ${PQLXBIN}/pqlxSrvr --dbName=$6 --identFile=$racine/out/$USER/PQLX/LISTFILES/"lst$6$3_$i" --numCPU=4
#	sed '$d'  $racine/out/$USER/PQLX/LISTFILES/current.list -i
#done 
#rm  $racine/out/$USER/PQLX/LISTFILES/*
