#!/bin/bash

# 2015/07/06 Arnaud Lemarchand
# change data format in STEIM2 of file listed in FILE 

encoding='STEIM2'
workdir='./'
racine=/data1/volobsis/miniseed/out/$USER/CorrectionLog
blocking='4096'
if [ ! -d ${racine} ]
then
 mkdir -p ${racine}
fi
logfile=${racine}/$(date +%Y%m%d%H%M)correctEncoding.log 
exec 1> >(tee -a "$logfile") 2>&1 


function usage(){
        printf "\n $0 re-encode in STEIM2 the files listed in FILE\n\n"
        printf " $0 [-h] [-d working directory] -b blocking inputfile \n"
        printf "where:\n"
        printf "\t-b\t\t: blocking size of output files (512 or 4096, default 4096);\n"
        printf "\t-d --directory\t\t: working directory to process files (default ./) ;\n"
        printf "\t-h --help\t\t: display this message ;\n"
        printf "\FILE\t\t: File with all files that must be processed (absolute roots required) .\n"
	exit 1 
}



if [ $# -eq 0 ]
then
        usage
fi

OPTIND=1 # Reset is necessary if getopts was used previously in the script.  It is a good idea to make this local in a function.
while getopts "b:d:h" opt; do
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
	echo $LISTE_FROM
	cd $workdir
	for file in  ${LISTE_FROM}
	do
	 echo $file "en cours de traitement sur un jour" 
	 qmerge -r -b $blocking -O STEIM2 $file >   $(basename $file)  2>>qmerge_$sta.log 
	 echo $file "processed"
	done 
fi

