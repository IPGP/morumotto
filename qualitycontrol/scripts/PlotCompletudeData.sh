#! /bin/bash

# Aurelien Mordret 2013 PlotCompletudeData.sh
# Arnaud Lemarchand juillet 2014
# 	ajout des tests sur existance du répertoire LISTFILES et FIGURES
# Jean-Marie Saurel juin 2017
# 	ajout d'une expression reguliere pour ne chercher que les fichiers respectant la nomenclature SDS

if [ "$#" != "4" ]
then
	echo -e "\nUsage: $0 STALIST datapath BeginningYear EndYear\n"
	exit
fi
racine=/data1/volobsis/miniseed
TOOLPATH="/opt/volobsis/validationSEED"
listdir=$racine/out/$USER/listfiles
figuresdir=$racine/out/$USER/figures
################## variables
if [ -d $listdir ]
 then
 rm $listdir/*Gapsfile*
fi

net=( `awk '{print $1}' $1` )
stalist=( `awk '{print $2}' $1 | uniq` )
mainpath=$2
	 
for i in `seq 0 $((${#stalist[*]} - 1))`
do

	touch "$listdir/${stalist[i]}Gapsfile"

			for yyyy in `seq $3 $4`
			do	

#				allpath=`paste -d '/' <(echo "$mainpath") <(echo "$yyyy") <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "[BEHL][HN][ZNE123].D") <(echo "*")`
				allpath=`paste -d '/' <(echo "$mainpath") <(echo "$yyyy") <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "[BEHL][HN][ZNE123].D") <(echo "${net[i]}.${stalist[i]}.??.[BEHL][HN][ZNE123].D.$yyyy.???")`
				echo "$allpath"	

				${TOOLPATH}/Check-Gaps.sh $allpath >> "$listdir/${stalist[i]}Gapsfile"
			done

	echo "Plot-Gaps.sh $listdir/${stalist[i]}Gapsfile $3-001 $4-365"
	${TOOLPATH}/Plot-Gaps.sh $listdir/"${stalist[i]}"Gapsfile "$3"-001 "$4"-365

done
if [[ $( ls -l ./PerctageData*.pdf | wc -l )  >  1 ]]
 then
  pdfunite `ls ./PerctageData*.pdf` "Completude.${net[i]}.pdf"
  mv Completude.*.pdf $figuresdir/
  rm ./PerctageData*.pdf
elif [[ $( ls -l ./PerctageData*.pdf | wc -l )  == 1 ]]
 then
  cp ./PerctageData*.pdf Completude.${net[i]}.pdf
  mv Completude.*.pdf $figuresdir/
  rm ./PerctageData*.pdf
fi

/usr/bin/evince "$figuresdir/Completude.${net[i]}.pdf"
