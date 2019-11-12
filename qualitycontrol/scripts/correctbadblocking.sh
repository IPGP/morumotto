#!/bin/bash

# 2015/07/06 Arnaud Lemarchand
# reblock files in the list of files [FILE]  

blocking='4096'
workdir='./'
racine=/data1/volobsis/miniseed/out/$USER/CorrectionLog
if [ ! -d ${racine} ]
then
 mkdir -p ${racine}
fi
logfile=${racine}/$(date +%Y%m%d%H%M)correctBadblocking.log 
exec 1> >(tee -a "$logfile") 2>&1


function usage(){
        printf "\n $0 blocking of files listed in FILE\n\n"
        printf " $0 [-h] [-b blocksize] [-d working directory] inputfile \n"
        printf "where:\n"
        printf "\t-b\t\t: blocking size of output files (512 or 4096 default 4096);\n"
        printf "\t-d\t\t: working directory to process files (default ./) ;\n"
        printf "\t-h\t\t: display this message ; \n"
        printf "\FILE\t\t: File with all files to be  processed (absolute roots required) .\n"
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
  LIST_FROM=$(cat $1)
  cd ${workdir}
  for file in ${LIST_FROM}
  do
   echo $file "en cours de traitement"
   cp $file tmp.miniseed
   sta=`basename $file | cut -d"." -f2`
   qmerge -b $blocking tmp.miniseed  > `basename $file` 2>>qmerge_$sta.badblocking.log 
   rm tmp.miniseed
   echo $file " processed"
  done
fi 
