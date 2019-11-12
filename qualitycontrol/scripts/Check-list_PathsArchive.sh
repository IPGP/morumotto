#! /bin/bash

# Aurelien Mordret 2013 Check-list_PathsArchive.sh
# 201601: A. Lemarchand
# ce script est remplacé par Check_DataFiles-vs-DatalessChannels.sh
if [ "$#" != "2" ]
then
	echo -e "\nUsage: $0 STALIST  datapath\n"
	exit
fi

################## variables
netcode=`awk '{print $1}' $1 | sort -u`
net=( `awk '{print $1}' $1` )
stalist=( `awk '{print $2}' $1` )
locid=( `awk '{print $4}' $1` )
chan=( `awk '{print $3}' $1` )
ybeg=( `awk '{print $5}' $1 | awk -F "," '{print $1}'` )
dbeg=( `awk '{print $5}' $1| awk -F "," '{print $2}'` )
yend=( `awk '{print $6}' $1| awk -F "," '{print $1}'` )
dend=( `awk '{print $6}' $1| awk -F "," '{print $2}'` )

#echo -e "netcode=$netcode net=$net statlist=$stalist locid=$locid channels=$chan ybeg=$ybeg  dbeg=$dbeg yend=$yend dend=$dend"
echo -e "\n Starting checking if paths archive are consistent with dataless"

echo -e "********** Checking if every Network/Station/Channel combination in the dataless have the corresponding SDS archive path -------------->"
echo -e "********** Checking if the file names are consistant with SEED standards -------------->"

	mainpath=$2
	 
	for i in `seq 0 $((${#stalist[*]} - 1))`
	do
	  if [[ ${yend[i]} = "(null)" ]] 
	   then  
		endyear=$(date +%Y )
	   else
		endyear=$(echo  ${yend[i]})
	   fi
	   for year in `seq ${ybeg[i]} $endyear`
	   do
		allpath=`paste -d '/' <(echo "$mainpath") <(echo "$year") <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "${chan[i]}")`
		#echo -e "$allpath"
		if [[ ! -d $allpath ]]
		then
			echo -e "----------------> WARNING !! The path $allpath does not exist in the archive!!"
		else
			fnameDataless=`paste -d '.' <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "${locid[i]}") <(echo "${chan[i]}") <(echo "$year")`
			#echo -e "$fnameDataless"
			k=0
			for file in $allpath/*
			do	
				if [[ -s $file ]]
				then
					fnameArch=`echo $file | awk -F'/' '{print $NF}' | awk -F'.' '{print $1"."$2"."$3"."$4"."$5"."$6}'`
					fnameArchfull=`echo $file | awk -F'/' '{print $NF}' | awk -F'.' '{OFS=".";print $0}'`
					#echo -e "$file" $fnameArch $fnameArchfull
					if [[ !( "$fnameArchfull" =~ [A-Z][A-Z].[A-Z][A-Z][A-Z].[0-9][0-9].[A-Z][A-Z][A-Z0-9].[A-Z].[0-9][0-9][0-9][0-9].[0-9][0-9][0-9] || "$fnameArchfull" =~ [A-Z][A-Z].[A-Z][A-Z][A-Z][A-Z].[0-9][0-9].[A-Z][A-Z][A-Z0-9].[A-Z].[0-9][0-9][0-9][0-9].[0-9][0-9][0-9]) ]]
					then
						echo -e "\t----------------> WARNING !! $fnameArchfull is not a standard name !!"
					fi
					if [ "$fnameDataless" == "$fnameArch" ] 
					then
						 k=1
						#echo -e "\t----------------> WARNING !! The fileID $fnameArch in the archive differs from $fnameDataless in the dataless!!"
					else
						echo -e " fnameDataless=$fnameDataless fnameArch=$fnameArch"
					fi
				fi
			done
			if [ "$k" == 0 ] 
			then
				
				echo -e "\t----------------> WARNING !! The combination $fnameDataless from the dataless has not been found in the archive $allpath !!"
			fi

		fi
	  done
	done

	echo -e "\n"








echo -e "Archive paths concistency done\n"

echo -e "\n********** Checking the consistency of the starting dates of the channels in the dataless and in the archive ---------------->"


	 
	for i in `seq 0 $((${#stalist[*]} - 1))`
	do
		allpath=`paste -d '/' <(echo "$mainpath") <(echo "${ybeg[i]}") <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "${chan[i]}")`
		filename=`paste -d '.' <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "${locid[i]}") <(echo "${chan[i]}")`		
		fullpath="$allpath/$filename*"
			if [[ -d $allpath ]]
			then

				date_beg_archive=`ls $fullpath | head -1 | awk -F'.' '{print $(NF-1)$NF}'`
				#echo -e "$date_beg_archive"
				date_beg_dataless="${ybeg[i]}${dbeg[i]}"
				#echo -e "$date_beg_dataless"
				

				if [ "$date_beg_archive" -gt "$date_beg_dataless" ]
				then
					echo -e  "--------> WARNING !! date_beg_archive ($date_beg_archive) later than date_beg_dataless ($date_beg_dataless) for ${stalist[i]}/${chan[i]} : data between $date_beg_dataless and $date_beg_archive may be missing!!"
				elif [ "$date_beg_dataless" -gt "$date_beg_archive" ]
				then
					echo -e  "--------> WARNING !!: date_beg_dataless ($date_beg_dataless) later than date_beg_archive ($date_beg_archive) for ${stalist[i]}/${chan[i]}: data before $date_beg_dataless should not be distributed"
				elif [ "$date_beg_dataless" -eq "$date_beg_archive" ]
				then
					echo -e "----> OK: date_beg_datales = date_beg_archive"
				fi

			else
				echo -e "----------------> WARNING !! The path $allpath does not exist in the archive!!"
			fi
	done	



echo -e "\nDate checking done\n"



