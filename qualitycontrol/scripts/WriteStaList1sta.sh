#! /bin/bash

# Aurelien Mordret 2013 WriteStaList1sta.sh

racine=/data1/volobsis/miniseed	
Stafile=${racine}/out/$USER/stalist/$(date +%Y%m%d%H%M)$1 

if [ "$#" -le "1" ]
then
	echo -e "\nUsage: $0 'Sta_file' 'dataless files' \n"
	exit
fi

k=0


for dataless in ${*}
do
  if [ $dataless != $1 ]
   then
	sta1=( `rdseed -f $dataless -s | grep "+------------------|" | awk '{print $4}'` )
	#sta1=( `rdseed -f $dataless -s | grep "(Poles & Zeros)" | awk '{print $8}'` )
	
	net1=( `rdseed -f $dataless -s | grep B050F16 | awk '{print $4}'` )

	chan1=( `rdseed -f $dataless -s | grep B052F04 | awk '{print $3".D"}'` )

	locID1=( `rdseed -f $dataless -s | grep B052F03 | awk '{print $3}'` )

	Starttime1=( `rdseed -f $dataless -s | grep B052F22 | awk '{print $4}'` )

	Endtime1=( `rdseed -f $dataless -s | grep B052F23 | awk '{print $4}'` )

	#sta[k]=$sta1
	#chan[k]=$chan1
	#locID[k]=$locID11
	#Starttime[k]=$Starttime1
	#Endtime[k]=$Starttime1
	#net[k]=$net1

	#k=`expr 1 + $k`
    fi	



## Creating the Station list: NETCOD STA CHAN LOCID DATE_Beg DATE_End

for i in `seq 0 $((${#sta1[*]} - 1))`
do
	if [[ (! "${locID1[i]}" =~ 8[0-1]) && ("${chan1[i]}" =~ [EH][HN][123ZNE]) ]]
	then
		echo -e "$net1 ${sta1[i]} ${chan1[i]} ${locID1[i]} ${Starttime1[i]} ${Endtime1[i]}" >> $Stafile
	fi
done

done

