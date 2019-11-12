#! /bin/bash

# Aurelien Mordret 2013 Plot-Gaps.sh


if [ "$#" != "3" ]
then
	echo -e "\nUsage: $0 Gapsfile yyyy-jjjbeg yyyy-jjjend\n"
	exit
fi
echo "start Plot-Gaps"
echo " Plotting percentage of data in miniseed files ..."
echo " "
#2012-340 HHE GBS 99
#2012-340 HHN GBS 25
#2012-340 HHZ GBS 25
#2012-341 HHE GBS 80

stalist=( `awk '{print $3}' $1 | sort -u` )

for c1 in L B H E
do
 for c2 in H N
 do
  cat $1 | grep -e ${c1}${c2}[E2] > ${c1}${c2}Efile
  cat $1 | grep -e ${c1}${c2}[N1] > ${c1}${c2}Nfile
  cat $1 | grep ${c1}${c2}Z > ${c1}${c2}Zfile
 done
done



#dmx=( `minmax -C -f0T $1` )

GMT gmtset INPUT_DATE_FORMAT yyyy-jjj PLOT_DATE_FORMAT o ANNOT_FONT_SIZE_PRIMARY +10p
GMT gmtset CHAR_ENCODING ISOLatin1+
GMT gmtset TIME_FORMAT_PRIMARY abbreviated

#list=("HHEfile" "HHNfile" "HHZfile")

for i in `seq 0 $((${#stalist[*]} - 1))`

#for compfile in ${list[@]}
do	
	sta=${stalist[$i]}
	
	for c1 in L B H E
	do
	 for c2 in H N
	 do
	  cat  ${c1}${c2}Efile | grep $sta | awk '{print $1, $4}' > xyfile${c1}${c2}E
	  cat  ${c1}${c2}Nfile | grep $sta | awk '{print $1, $4}' > xyfile${c1}${c2}N
	  cat  ${c1}${c2}Zfile | grep $sta | awk '{print $1, $4}' > xyfile${c1}${c2}Z
	 done
	done

#	cat HHZfile | grep $sta | awk '{print $1, $4}' > xyfileZ
#	cat HHNfile | grep $sta | awk '{print $1, $4}' > xyfileN
#	cat HHEfile | grep $sta | awk '{print $1, $4}' > xyfileE


        for c1 in L B H E
        do
         for c2 in H N
         do
	 if [ -s xyfile${c1}${c2}Z ]
	 then
	  GMT psbasemap -R$2T/$3T/0/102 -JX25cT/3.5cp2 -K -Bs1Y/WSen \
    		-Bpa2Of1rg1r/20g10WSen:,"%"::."Percentage of data for station $sta, comp. ${c1}${c2}Z": > "PerctageData$sta.${c1}${c2}.ps"
	  GMT psxy xyfile${c1}${c2}Z -R -J -W0.5p,green -K -O >> "PerctageData$sta.${c1}${c2}.ps"
	  GMT psxy xyfile${c1}${c2}Z -R -J -Sc2.5p -Ggreen -K -O >> "PerctageData$sta.${c1}${c2}.ps"
	  
	  GMT psbasemap -R$2T/$3T/0/102 -JX25cT/3.5cp2 -K -O -Y6.5c -Bs1Y/WSen \
		-Bpa2Of1rg1r/20g10WSen:,"%"::."Percentage of data for station $sta, comp. ${c1}${c2}[2-E]": >> "PerctageData$sta.${c1}${c2}.ps"
	  GMT psxy xyfile${c1}${c2}E -R -J -W0.5p,blue -K -O >> "PerctageData$sta.${c1}${c2}.ps"
	  GMT psxy xyfile${c1}${c2}E -R -J -Sc2.5p -Gblue -K -O >> "PerctageData$sta.${c1}${c2}.ps"
	
	  GMT psbasemap -R$2T/$3T/0/102 -JX25cT/3.5cp2 -K -O -Y6.5c -Bs1Y/WSen \
    		-Bpa2Of1rg1r/20g10WSen:,"%"::."Percentage of data for station $sta, comp. ${c1}${c2}[1-N]": >> "PerctageData$sta.${c1}${c2}.ps"
	  GMT psxy xyfile${c1}${c2}N -R -J -W0.5p,red -O -K >> "PerctageData$sta.${c1}${c2}.ps"
	  GMT psxy xyfile${c1}${c2}N -R -J -Sc2.5p -Gred -O >> "PerctageData$sta.${c1}${c2}.ps"
	fi
        done
      done
done

for i in `ls *.ps` 
do 
	/usr/bin/ps2pdf $i 
done

rm xyfile* HH*file *.ps

