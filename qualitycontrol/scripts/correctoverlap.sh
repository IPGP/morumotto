#!/bin/bash

# 2015/07/06 Arnaud Lemarchand
# prune overlaps detected in the list of files 

bloking='512'
workdir='./'
racine=/data1/volobsis/miniseed/out/$USER/CorrectionLog
if [ ! -d ${racine} ]
then
 mkdir -p ${racine}
fi
logfile=${racine}/$(date +%Y%m%d%H%M)correctoverlaps.log 
exec 1> >(tee -a "$logfile") 2>&1


function usage(){
        printf "\n $0 prune overlaps of files listed in FILE\n\n"
        printf " $0 [-h] [-b blocksize] [-d working directory] inputfile \n"
        printf "where:\n"
        printf "\t-b --blocksize\t\t: blocking size of output files (512 or 4096) ;\n"
        printf "\t-d --directory\t\t: working directory to process files (default ./) ;\n"
        printf "\t-h --help\t\t: display this message ;\n"
        printf "\FILE\t\t: File with all files that must be processed (absolute roots required) .\n"
	exit 0
}



if [ $# -eq 0 ]
then
        usage
fi

OPTIND=1 # Reset is necessary if getopts was used previously in the script.  It is a good idea to make this local in a function.
while getopts "b:d:h:" opt; do
case "$opt" in
 h|-help)
  usage
  exit 0
 ;;
 b) if [[ $OPTARG -eq "512" || $OPTARG -eq "4096" ]]
    then
        blocking=$OPTARG
    else
        printf " -b option is with 512 or 4096\n"
        exit 0
    fi
 ;;
 d) workdir=$OPTARG
    if [ ! -d $OPTARG ]
    then
        mkdir -p $workdir
    else
	printf " directory $OPTARG already exists"
	exit 1
    fi
 ;;
  '?')
      usage
      exit 1
 ;;
esac
done
shift "$((OPTIND-1))" # Shift off the options and optional --.
if [[ ! -a $1 ||  $# -ne 1 ]]
then
	usage
        printf "\nFILE does not exist or not passed \n"
        exit 0
else
	LISTE_FROM=$(cat $1)
	echo "working directory where files are processed = " $workdir
#	echo $LISTE_FROM
	cd $workdir
	for file in  ${LISTE_FROM}
	do
	 read net sta locid chan quality year day <<< $(basename $file | awk -F"." '{OFS" "; print $1,$2,$3,$4,$5,$6,$7}' )
	 read datadir  <<< $( dirname  $file)
	 read filepun daypun<<< $(basename $file | awk -F"." '{OFS=".";daypun=sprintf("%03d",$7+1); print $1,$2,$3,$4,$5,$6,daypun" "daypun}' )
	 read filemun daymun<<< $(basename $file | awk -F"." '{OFS=".";daymun=sprintf("%03d",$7-1); print $1,$2,$3,$4,$5,$6,daymun" "daymun}' )
         if [ -f $file ]
	  then 
	 	echo $file "en cours de traitement sur un jour" 
	 	sdrsplit -v -c -C -G 1  $file  > sdrplit_$sta.log
	 	#qmerge -r $sta* > $(basename $file).new 2>>qmerge_$sta.log 
	 	#rm $sta*
	 	if  [[ "$LISTE_FROM" == *$filepun* ]]
	   	then
	     	  echo $file " traité en prenant en compte" $datadir"/"$filepun 
	     	  sdrsplit -v -c -C -G 1  $datadir"/"$filepun  > sdrplit_$sta.log
	 	fi
	 	if  [[ "$LISTE_FROM" == *$filemun* ]]
	   	then
	     	  echo $file " traité en prenant en compte" $datadir"/"$filemun 
	     	  sdrsplit -v -c -C -G 1  $datadir"/"$filemun  > sdrplit_$sta.log
	 	fi

		# qmerge -b $blocking -r $sta* >  temp.miniseed  2>>qmerge_$sta.log 
	#	 qmerge -b $blocking  $sta* >  temp.miniseed  2>>qmerge_$sta.log 

		 if [[ "$LISTE_FROM" == *$filepun* && "$LISTE_FROM" == *$filemun* ]]
	   	then
#	     	 qmerge -b $blocking -T -t $year,$day,23:59:59.99999 temp.miniseed > temp1.miniseed  2>>qmerge_$sta.log
#	     	 qmerge -b $blocking -T -f $year,$day,00:00:00.00000 temp1.miniseed > $(basename $file)  2>>qmerge_$sta.log
	     	 qmerge -b $blocking -T -f $year,$day,00:00:00.00000 -t $year,$day,23:59:59.99999 $sta* > $(basename $file)  2>>qmerge_$sta.log
	 	elif [[ "$LISTE_FROM" == *$filepun* ]]
	   	then
#	     	  qmerge -b $blocking -T -t $year,$day,23:59:59.99999 temp.miniseed > $(basename $file) 2>>qmerge_$sta.log
	     	  qmerge -b $blocking -T -t $year,$day,23:59:59.99999 $sta* > $(basename $file) 2>>qmerge_$sta.log
		elif [[ "$LISTE_FROM" == *$filemun* ]]
	   	then
#	     	  qmerge -b $blocking -T -f $year,$day,00:00:00.00000 temp.miniseed > $(basename $file) 2>>qmerge_$sta.log
	     	  qmerge -b $blocking -T -f $year,$day,00:00:00.00000 $sta* > $(basename $file) 2>>qmerge_$sta.log
	 	else
	#     	  qmerge -b $blocking -r $sta* > $(basename $file).new 2>>qmerge_$sta.log  
	     	  qmerge -b $blocking  $sta* > $(basename $file) 2>>qmerge_$sta.log  
	 	fi
		 [[ -z "${sta}" ]] ||   rm $sta*
	 	if [ -f .new ]
	   	then
	     	 rm .new 
	 	fi
	 	echo $datadir"/"$file "processed"
	   fi
	done 
fi

