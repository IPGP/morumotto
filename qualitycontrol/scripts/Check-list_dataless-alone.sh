#! /bin/bash

# Aurelien Mordret 2013 Check-list_dataless-alone.sh

if [ "$#" != "2" ]
then
	echo -e "\nUsage: $0 dataless_file_name network_code (G, WI, PF, GL or MQ)\n"
	exit
fi

################## variables
netcode=`rdseed -f $1 -s | grep B050F16 | awk '{print $4}' | sort -u`
block=`rdseed -f $1 -s | grep B010F04 | awk '{print $5}'`
compression=(`rdseed -f $1 -s | grep B030F03 | awk '{print $4}' | sort -u`)
#rate=(`rdseed -f $1 -s | grep B052F18 | awk '{print $4}' | sort -u`)
rate=(`rdseed -f $1 -s | grep B052F18 | awk '{print $4}' `)
encod1=(`rdseed -f $1 -s | grep B050F11 | awk '{print $5}' | sort -u`)
encod2=(`rdseed -f $1 -s | grep B050F12 | awk '{print $5}' | sort -u`)
coord=( `paste -d'.' <(rdseed -f $1 -s | grep B050F04 | awk '{print $3}') <(rdseed -f $1 -s | grep B050F05 | awk '{print $3}') <(rdseed -f $1 -s | grep B050F06 | awk '{print $3}')` )
st=(`rdseed -f $1 -s | grep B050F03 | awk '{print $4}'`)
lats=(`rdseed -f $1 -s | grep B050F04 | awk '{print $3}'`)
lons=(`rdseed -f $1 -s | grep B050F05 | awk '{print $3}'`)
elvs=(`rdseed -f $1 -s | grep B050F06 | awk '{print $3}'`)
latc=(`rdseed -f $1 -s | grep B052F10 | awk '{print $3}'`)
lonc=(`rdseed -f $1 -s | grep B052F11 | awk '{print $3}'`)
elvc=(`rdseed -f $1 -s | grep B052F12 | awk '{print $3}'`)
sta=( `rdseed -f $1 -s | grep "+------------------|" | awk '{print $4}'` )  # grep "(Poles & Zeros)" | awk '{print $8}' # grep "+------------------|" | awk '{print $4}'
cha=( `rdseed -f $1 -s | grep "+------------------|" | awk '{print $7}'` ) # grep "(Poles & Zeros)" | awk '{print $10}' # grep "+------------------|" | awk '{print $7}'
loc=( `rdseed -f $1 -s | grep B052F03 | awk '{print $3}'` )
az=( `rdseed -f $1 -s | grep B052F14 | awk '{print $3}'` )
dip=( `rdseed -f $1 -s | grep B052F15 | awk '{print $3}'` )

sta2=( `rdseed -f $1 -s | grep "(Poles & Zeros)" | awk '{print $8}' ` )  # grep "(Poles & Zeros)" | awk '{print $8}' # grep "+------------------|" | awk '{print $4}'
cha2=( `rdseed -f $1 -s | grep "(Poles & Zeros)" | awk '{print $10}'` ) # grep "(Poles & Zeros)" | awk '{print $10}' # grep "+------------------|" | awk '{print $7}'
s1unit=(` rdseed -f $1 -s | grep B053F05 | awk '{print $6}'` )
stagenbr=(` rdseed -f $1 -s | grep B053F04 | awk '{print $5}'` )
stage1frq=(` rdseed -f $1 -s | grep B053F08 | awk '{print $4}'` )



rdseed -f $1 -S
sed -i 's/\"//' rdseed.stations

stadataless=( `cat rdseed.stations | awk '{print $(1)}'` )

echo -e "\n Starting dataless global checking"

echo -e "\n********** Checking if only $2 network in dataless  -------------------->"


if [ "$netcode" != "$2" ]
then
	echo -e "------> WARNING !! There is a problem with a network code in the dataless: $netcode\n"
#else
	#echo -e "------> OK: No network code problem\n"

fi
echo -e "done\n"

if [ $2 == "PF" ]
then
 stanamefromfile=(`echo "$1" | awk -F'.' '{print $2}'` )
else
 stanamefromfile=(`echo "$1" | awk -F'.' '{print $1}' | awk -F'_' '{print $2}'`)
fi
echo -e "********** Checking if station name in the dataless file name is the same than inside the dataless ----------->"

if [ "$sta" != "$stanamefromfile" ]
then
	echo -e "------> WARNING !! The station name in the dataless file name ${stanamefromfile} is different from the station name inside the dataless: ${sta}"
fi
echo -e "done\n"

echo -e "********** Checking if blockin, compression format encoding and sampling rate are OK ----------->"

if [ "${block[*]}" != "4096" ]
then
	echo -e "------> WARNING !! Blocking = ${block[*]} in dictionnary of ${sta[0]}"
#else
	#echo -e "------> OK: Blocking = ${block[*]}"
fi

if [ "${compression[*]}" != "Steim2" ]
then
	echo -e "------> WARNING !! Compression = ${compression[*]} in dictionnary of ${sta[0]}"
#else
	#echo -e "------> OK: Compression = ${compression[*]}"

fi

for i in ${!rate[*]}
do
 if [[ ${rate[i]} != 100  &&  ${cha[i]} = [EH][HN][ZNE123] ]]
 then
	echo -e "------> WARNING !! Sampling rate = ${rate[i]} in ${sta[i]}.${cha[i]}.${loc[i]} "
 fi
 if [[ ${rate[i]} != 20  &&  ${cha[i]} = [B][HN][ZNE123] ]]
 then
	echo -e "------> WARNING !! Sampling rate = ${rate[i]} in ${sta[i]}.${cha[i]}.${loc[i]} "
 fi
 if [[ ${rate[i]} != 1 &&  ${cha[i]} = [L][HN][ZNE123] ]]
 then
	echo -e "------> WARNING !! Sampling rate = ${rate[i]} in ${sta[i]}.${cha[i]}.${loc[i]} "
 fi
done


if [ "${encod1[*]}" != "3210" ]
then
	echo -e "------> WARNING !! 32-bit word order = ${encod1[*]} in blockette 50 of ${sta[0]}"
#else
	#echo -e "------> OK: 32-bit word order = ${encod1[*]}"

fi

if [ "${encod2[*]}" != "10" ]
then
	echo -e "------> WARNING !! 16-bit word order = ${encod2[*]}  in blockette 50 of ${sta[0]}"
#else
	#echo -e "------> OK: 16-bit word order = ${encod2[*]}\n"

fi
echo -e "done\n"



echo -e "\n********** Checking the dataless with verseed ------------>"

verseed $1

echo -e "done\n"


echo -e "\n********** Checking the coordinates of the stations in the dataless ------------>"

for i in `seq 0 $((${#sta[*]} - 1))`
do
	for j in `seq 0 $((${#st[*]} - 1))`
	do
		if [ "${sta[i]}" == "${st[j]}" ]
		then
			if [ "${latc[i]}" != "${lats[j]}" ]
			then
				echo -e "--------> WARNING !! For station ${sta[i]}, channel and station latitudes are different for channel ${cha[i]}.${loc[i]}: ${latc[i]} != ${lats[j]}"
#			else
				#echo -e "------> OK !! For station ${sta[i]}, station and channel latitudes are the same"

			fi
		fi
	done
done

for i in `seq 0 $((${#sta[*]} - 1))`
do
	for j in `seq 0 $((${#st[*]} - 1))`
	do
		if [ "${sta[i]}" == "${st[j]}" ]
		then
			if [ "${lonc[i]}" != "${lons[j]}" ]
			then
				echo -e "--------> WARNING !! For station ${sta[i]}, channel and station longitudes are different for channel ${cha[i]}.${loc[i]}: ${lonc[i]} != ${lons[j]}"
#			else
				#echo -e "------> OK !! For station ${sta[i]}, station and channel longitudes are the same"

			fi
		fi
	done
done

for i in `seq 0 $((${#sta[*]} - 1))`
do
	for j in `seq 0 $((${#st[*]} - 1))`
	do
		if [ "${sta[i]}" == "${st[j]}" ]
		then
			if [ "${elvc[i]}" != "${elvs[j]}" ]
			then
				echo -e "--------> WARNING !! For station ${sta[i]}, channel and station elevations are different for channel ${cha[i]}.${loc[i]}: ${elvc[i]} != ${elvs[j]} "
#			else
				#echo -e "------> OK !! For station ${sta[i]}, station and channel elevations are the same"

			fi
		fi
	done
done


for i in `seq 0 $((${#coord[*]} - 2))`
do
	for j in `seq $((i+1)) $((${#coord[*]} - 1))`
	do
		if [ "${coord[i]}" != "${coord[j]}" ]
		then
			echo -e "--------> WARNING !! Stations ${stadataless[i]} and ${stadataless[j]} are defined with differrent  coordinates"
#		else
			#echo -e "----> OK !! Stations ${stadataless[i]} and ${stadataless[j]} does not have the same coordinates"

		fi
	done
done

echo -e "done\n"

rm rdseed.stations




echo -e "\n********** Checking the consistency of the channel names and their orientations ---------------->"
for i in `seq 0 $((${#cha[*]} - 1))`
do

	if [[ "${cha[i]}" == [LBEH][HN][ENZ12] ]]
	then
		#echo -e "----> OK !! Channel name ${sta[i]}.${cha[i]}.${loc[i]} consistant with [LBEH][HN][ENZ12]"
		#echo -e "${cha[i]} ${az[i]} ${dip[i]}"
		echo -e "${cha[i]} ${az[i]} ${dip[i]} ${sta[i]} ${loc[i]}" | awk 'function abs(x){return ((x < 0.0) ? -x : x)} {
			if ($1~/[EH][HN]E/)
			{
				if ( (( $2 >= 95  || $2 <= 85) || ( $3 >= 5  || $3 <= -5)) )

					{
					print "--------> WARNING !! Problem of compatibility between channel "$4"."$1"."$5 " azimuth "$2" and/or dip "$3", channel name has to be changed"
					print " Unless azimuth = 270° for short period, this is OK (inversed polarity)"}
			}

			if ($1~/[EH][HN]2/)
			{	print "--------> WARNING !! Check if channel "$4"."$1"."$5 " has azimuth "$2" around East and if horizontal channels are 90° appart "
				if ( (($2 >= 85 && $2 <= 95) && ($3 >= -5 && $3 <= 5)) )

					print "--------> WARNING !! Problem of compatibility between channel "$4"/"$1" and azimuth "$2" and/or dip "$3" "
			}

			if ($1~/[EH][HN]N/)
			{
				if ( (($2 >= 5  || $2 <= -5) || ($3 >= 5  || $3 <= -5)) )
				{
					print "--------> WARNING !! Problem of compatibility between channel "$4"."$1"."$5 " azimuth "$2" and/or dip "$3", channel name has to be changed"
					print " Unless azimuth = 180° for short period, this is OK (inversed polarity)"}
			}

			if ($1~/[EH][HN]1/)
			{	print "--------> WARNING !! Check if channel "$4"."$1"."$5 " has azimuth "$2" around North and if horizontal channels are 90° appart "
				if ( (($2 >= -5 && $2 <= 5) && ($3 >= -5 && $3 <= 5)) )

					print "--------> WARNING !! Problem of compatibility between channel "$4"/"$1" and azimuth "$2" and/or dip "$3" "

			}

			if ( ($1~/[H][HN]Z/) && ($2 != 0 || $3 != -90))
			{
				print "--------> WARNING !! Problem of compatibility between channel "$4"."$1"."$5 " azimuth "$2" and/or dip "$3" "

			}

			if ( ($1~/[E][HN]Z/) && ($2 != 0 || abs($3) != 90) )
			{
				print "--------> WARNING !! Problem of compatibility between channel "$4"."$1"."$5 " azimuth "$2" and/or dip "$3" "

			}

		}'



	else
		echo -e "--------> WARNING !! Problem with channel name : ${sta[i]}.${cha[i]}.${loc[i]} not of the form [EH][HN][ENZ12]"
	fi

done
echo -e "\ndone\n"

echo -e "\n********** Checking stage 1 units ---------------->"

for i in `seq 0 $((${#cha2[*]} - 1))`
do
	if [[ "${cha2[i]}" == [EH][H][ENZ12] ]] && [ "${stagenbr[i]}" == 1 ] && [ "${s1unit[i]}" != "M/S" ]
	then
		echo -e "--------> WARNING !! Stage ${stagenbr[i]} of Channel ${sta2[i]}/${cha2[i]} unit is ${s1unit[i]} but should be in M/S"
	#else
		#echo -e "----> OK !! Stage ${stagenbr[i]} of Channel ${sta2[i]}/${cha2[i]} unit is ${s1unit[i]}"

	fi

	if [[ "${cha2[i]}" == [EH][N][ENZ12] ]] && [ "${stagenbr[i]}" == 1 ] && [ "${s1unit[i]}" != "M/S**2" ]
	then
		echo -e "--------> WARNING !! Stage ${stagenbr[i]} of Channel ${sta2[i]}/${cha2[i]} unit is ${s1unit[i]} but should be in M/S**2"
	#else
		#echo -e "----> OK !! Stage ${stagenbr[i]} of Channel ${sta2[i]}/${cha2[i]} unit is ${s1unit[i]}"

	fi
done
echo -e "done\n"


echo -e "\n********** Checking stages units: out unit for one stage is in unit for the following one ---------------->"

units=`paste -d" " <(rdseed -f $1 -s | grep "Response.* ch " | awk '{print $(NF-4),$(NF-2)}' | tail -n +2) <(rdseed -f $1 -s | grep "B05[34]F0[4]" | awk '{print $5}' | tail -n +2) <(rdseed -f $1 -s | grep "B05[34]F0[5]" | awk '{print $6}' | tail -n +2) <(rdseed -f $1 -s | grep "B05[34]F0[6]" | awk '{print $6}' | head -n -1)`

echo "$units" | awk '{if($3 != 1) print $0}' | awk '{if ($4 != $5)
print "--------> WARNING !! Stage unit in ("$4")!= Stage unit out ("$5"): problem for "$1"/"$2} '
echo -e "done\n"





echo -e "\n********** Checking if analog stages units is in rad/sec ---------------->"

astage=`paste -d " " <(rdseed -f $1 -s | grep "(Poles & Zeros)" | awk '{print $8}') <(rdseed -f $1 -s | grep "(Poles & Zeros)" | awk '{print $10}') <(rdseed -f $1 -s | grep B053F03 | awk '{print $5,$NF}' | sed 's/.$//')`

echo "$astage" | awk '{if ($3=="A" && $4 != "(Rad/sec)")
print "--------> WARNING !! Analog stage units "$4" is a problem for "$1"/"$2", it should be in (Rad/sec)"}'
echo -e "done\n"





echo -e "\n********** Checking if there are as many stage 0 as channels and if its sensitivity is about 1e9 Counts/m/s ---------------->"

stage0=`paste -d " " <(rdseed -f $1 -s | grep "Channel Sensitivity" | awk '{print $6}') <(rdseed -f $1 -s | grep "Channel Sensitivity" | awk '{print $8}') <(rdseed -f $1 -s | grep "B058F04.*Sensitivity" | awk '{print $3}')`

echo "$stage0" | awk 'function abs(x){return ((x < 0.0) ? -x : x)} {if (($2~/[EH][H][ZNE123]/) && (abs($3)>5E10 || abs($3)<1E7))
print "--------> WARNING !! There may be a sensitivity problem for "$1"/"$2", sensitivity " $3" is to low/high"}'
echo "$stage0" | awk 'function abs(x){return ((x < 0.0) ? -x : x)} {if (($2~/[EH][N][ZNE123]/) && (abs($3)>4.3E5 || abs($3)<3.8E5))
print "--------> WARNING !! There may be a sensitivity problem for accelerometer "$1"/"$2", sensitivity " $3" is to low/high"}'
echo -e "done\n"




echo -e "\n********** Checking if the normalization frequency of stage 1 is 0.1, 1 or 10  Hz ---------------->"

#rdseed -f $1 -s | grep B053F08 | awk '{print $4}'

#stage1=`paste -d " " <(rdseed -f $1 -s | grep "(Poles & Zeros)" | awk '{print $8}') <(rdseed -f $1 -s | grep "(Poles & Zeros)" | awk '{print $10}') <(rdseed -f $1 -s | grep B053F08 | awk '{print $4}') <(rdseed -f $1 -s | grep B053F04 | awk '{print $5}')`
stage1=`paste -d " " <(rdseed -f $1 -s | grep "(Poles & Zeros)" | awk '{print $8,$10}')  <(rdseed -f $1 -s | grep B053F08 | awk '{print $4}') <(rdseed -f $1 -s | grep B053F04 | awk '{print $5}')`

echo "$stage1" | awk '{
			if ($4==1 && $2~/[BH][HN][ZNE123]/ && $3 != 1  )  {print "--------> WARNING !! The normalisation frequency of stage 1 for "$1"/"$2" is " $3" but should be 1Hz"}
			if ($4==1 && $2~/E[HN][ZNE123]/    && $3 != 10 )  {print "--------> WARNING !! The normalisation frequency of stage 1 for "$1"/"$2" is " $3" but should be 10Hz"}
			if ($4==1 && $2~/L[HN][ZNE123]/    && $3 != 0.1)  {print "--------> WARNING !! The normalisation frequency of stage 1 for "$1"/"$2" is " $3" but should be 0.1Hz"}
			}'
echo -e "done\n"




echo -e "\n********** Checking if the normalization frequency of stage 0 is 0.1, 1 or 10 Hz ---------------->"

stage0=`paste -d " " <(rdseed -f $1 -s | grep "+------------------|" | awk '{print $4}') <(rdseed -f $1 -s | grep "+------------------|" | awk '{print $7}') <(rdseed -f $1 -s | grep "Frequency of sensitivity" | awk '{print $5}')`

echo "$stage0" | awk '{
			if ( $3 != 1 && $2~/[BH][HN][ZNE123]/ ) print "--------> WARNING !! The normalisation frequency for "$1"/"$2" is " $3" but should be 1Hz"
			if ( $3 != 10 &&  $2~/E[HN][ZNE123]/   ) print "--------> WARNING !! The normalisation frequency for "$1"/"$2" is " $3" but should be 10Hz"
			if ( $3 != 0.1 &&  $2~/L[HN][ZNE123]/   ) print "--------> WARNING !! The normalisation frequency for "$1"/"$2" is " $3" but should be 0.1Hz"
			}'
echo -e "done\n"



DictComCoId=(` rdseed -a -f $1  | grep B031F03 | awk '{print $5}'` )
DictComClaCode=(` rdseed -a -f $1  | grep B031F04 | awk '{print $5}'` )
StaComIndCode=(` rdseed -C [STN] -f $1  | grep B051F05 | awk '{print $6}'` )
ChanComIndCode=(` rdseed -C [CHN] -f $1  | grep B059F05 | awk '{print $6}'` )

echo -e "\n********** Checking if Station Comments ---------------->"
for i in ${!StaComIndCode[*]}
do
 for j in ${!DictComCoId[*]}
 do
   if [[ ${StaComIndCode[i]} == ${DictComCoId[j]}  ]]
   then
	if [[  ${DictComClaCode[j]} != "S"  ]]
	then
	 echo -e "------> WARNING !! Wrong station comment attribution (${DictComClaCode[j]} instead of S) for station ${sta[1]} with the comment $(rdseed -a -f $1  | grep B031F05 | awk ' NR==('$j'+1)  { for(k=4;k<=NF;k++) line=line" "$k; print line }') "
	fi
   fi
 done
done
echo -e "done\n"

echo -e "\n********** Checking if Channel Comments ---------------->"
for i in ${!ChanComIndCode[*]}
do
 for j in ${!DictComCoId[*]}
 do
   if [[ ${ChanComIndCode[i]} == ${DictComCoId[j]}  ]]
   then
	if [[  ${DictComClaCode[j]} != "C"  ]]
	then
	 echo -e "------> WARNING !! Wrong channel comment attribution (${DictComClaCode[j]} instead of C) for station ${sta[1]} with the comment $(rdseed -a -f $1  | grep B031F05 | awk ' NR==('$j'+1)  { for(k=4;k<=NF;k++) line=line" "$k; print line }') "
	fi
   fi
 done
done

echo -e "done\n"
