#! /bin/bash

# Aurelien Mordret 2013 PlotRESP.sh
# Arnaud Lemarchand 20150702
#  -Modification du script piur toutes les séries temporelles des réponses de tous les canaux
#  - ajout option -last pour ne tracer que la dernière.
if (( "$#"<1 ||  "$#">2 ))
then
	echo -e "\nUsage: $0 STALIST\n option: -last : plot the last response files (default is all time series) " 
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
end=( `awk '{print $6}' $1` )
cha=( `awk '{print $3}' $1 | awk -F "." '{print $1}'` )
racine="/data1/volobsis/miniseed"
indirRESP=$racine/in/dataless/RESP
outdirfiles=$racine/out/$USER/plotresp/amp_phase_files
outdirplot=$racine/out/$USER/plotresp
figuresdir=$racine/out/$USER/figures
racineJEvalResp=/opt/volobsis/tools/JPlotResp/last

rm $outdirfiles/PHASE* $outdirfiles/AMP* $outdirplot/PLOTRESP* 

for i in `seq 0 $((${#stalist[*]} - 1))`
#for i in `seq 10 10`
do
	filename="${indirRESP}/${net[i]}/RESP.${net[i]}.${stalist[i]}.${locid[i]}.${cha[i]}"
	for j in `seq 0 1`
	do
		db=`expr ${dbeg[i]} + 1`
		if [[ "${end[i]}" == *null* ]]
		then
		 ey=9999
		 ed=365
		else
		 ey=${end[i]:0:4}
		 ed=${end[i]:5:3}
		fi
		#echo -e "${stalist[i]} ${cha[i]} ${ybeg[i]} ${dbeg[i]} 0.001 300 500 -f $filename"		
		java -jar $racineJEvalResp/JEvalResp.jar ${stalist[i]} ${cha[i]} ${ybeg[i]} $db 0.001 300 500 -ey $ey -ed $ed  -u def -f $filename -s log -stage $j $j -o $outdirfiles
		ampfilein="AMP.${net[i]}.${stalist[i]}.${locid[i]}.${cha[i]}"
		phasefilein="PHASE.${net[i]}.${stalist[i]}.${locid[i]}.${cha[i]}"
	#	echo $2
		if [ "$2" = "-last" ]
		then
			psfile="PLOTRESP.${net[i]}.${stalist[i]}.${locid[i]}.${cha[i]}-$j.ps"
			ampfileout="AMP.${net[i]}.${stalist[i]}.${locid[i]}-${cha[i]}"
			phasefileout="PHASE.${net[i]}.${stalist[i]}.${locid[i]}-${cha[i]}"
		else
			psfile="PLOTRESP.${net[i]}.${stalist[i]}.${locid[i]}.${cha[i]}.${ybeg[i]}_$db-$j.ps"
			ampfileout="AMP.${net[i]}.${stalist[i]}.${locid[i]}-${cha[i]}.${ybeg[i]}_$db"
			phasefileout="PHASE.${net[i]}.${stalist[i]}.${locid[i]}-${cha[i]}.${ybeg[i]}_$db"
		fi
		if [[ "${end[i]}" == *null* ]]
		then
			title="${ybeg[i]}_$db - now   ${net[i]}.${stalist[i]}.${locid[i]}.${cha[i]} - stage $j"
		else
			title="${ybeg[i]}_$db - $ey.$ed   ${net[i]}.${stalist[i]}.${locid[i]}.${cha[i]} - stage $j"
		fi
		echo "sed 's/,/\./g' "$outdirfiles/$ampfilein" > "$outdirfiles/$ampfileout""
		sed 's/,/\./g' $outdirfiles/$ampfilein > $outdirfiles/$ampfileout
		sed 's/,/\./g' $outdirfiles/$phasefilein > $outdirfiles/$phasefileout
		
		GMT psxy "$outdirfiles/$phasefileout" -JX25cl/8c -R0.001/300/-200/200 -Ba1pf3g3:"Frequency":/a60g60:"Phase":WeSn -V -K -X3c -W10,blue > "$outdirplot/$psfile"

		GMT psxy "$outdirfiles/$ampfileout" -JX25cl/8cl -R0.001/300/1e-2/1e11 -Ba1pf3g3:"Frequency":/a1pf3g1:"Amplitude"::."$title".:Wesn -W10,red -V -Y8c -O >> "$outdirplot/$psfile"

	done
done

fileend=$(date +%Y%m%d%H%M)RESP.${net[i]}.pdf

cd $outdirplot

for i in `ls $outdirplot/*.ps` 
do 
   echo " /usr/bin/ps2pdf $i"	
       /usr/bin/ps2pdf $i 
done

pdfunite `ls $outdirplot/PLOTRESP.*.pdf` $fileend
mv $fileend $figuresdir

rm $outdirfiles/* 

/usr/bin/evince $figuresdir/$fileend

