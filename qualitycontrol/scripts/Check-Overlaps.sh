#! /bin/bash

# Aurelien Mordret 2013 Check-Overlaps.sh
# Arnaud Lemarchand 2014/10/28
#  1- reconfiguration du fichire de sortie avec le chemin complet du fichier avec un Overlaps
#  2- Ajout d'un test si données dans le fichiers appartiennent bien au jour J +/- 1
# Arnaud Lemarchand 2015/07/02
#  - Ajout du fichier j+1 si le début de l'ovserlap commence à 23h5?. Ce fichier sera alors traité dans la routine correctionoverlap.sh 

echo " List of  miniseed files with overlaps ..."
iaover=0
igap=0
iover=0
dir=$( ls $* | xargs -i dirname {} | sort -u )
#echo "   Source                Last Sample              Next Sample       Gap  Samples"
  
for file in $*
do
	read filenameyear filenameday <<< $(basename $file | awk -F"." '{ print $6,$7}' ) 
	msi -S $file| awk -F"|" '{print $5}' | awk -F","  -v year=$filenameyear -v day=$filenameday 'BEGIN { daypu=sprintf("%03d",day+1);daymu=sprintf("%03d",day-1) } { if ( ($1 != year || ( $2!=day && $2!=daymu && $2!=daypu))  && NR>1 )  print "data in bad file:    '"$file"' with "$1,$2 " data" } '
done
#echo "The total number of overlap(s) found is $iover"
for i in $dir
do
	echo "repertory scanned:  "$i
	msi -G $i/*.D.????.??? | grep "-" | awk -v dir=$i '{
					split($1,filename,"_");
					split($2,starttime,",");
					split($3,endtime,",");
					print dir"/"filename[1]"."filename[2]"."filename[3]"."filename[4]".D."starttime[1]"."starttime[2]" @ "starttime[1]"."starttime[2]","starttime[3]"  "$5" samples"
					if ( starttime[3] ~ /00:0*/ ) { print dir"/"filename[1]"."filename[2]"."filename[3]"."filename[4]".D."starttime[1]"."sprintf("%03d",starttime[2]-1)" @ "starttime[1]"."starttime[2]","starttime[3]"  "$5" samples" }
					if ( starttime[3] ~ /23:5*/ ) { print dir"/"filename[1]"."filename[2]"."filename[3]"."filename[4]".D."starttime[1]"."sprintf("%03d",starttime[2]+1)" @ "starttime[1]"."starttime[2]","starttime[3]"  "$5" samples" }
					}' 
	#outmsi=$( msi -G $i/* | grep "-" )
	#iaover=${#outmsi[*]}
	#iover=`expr $iover + $iaover`

done
for file in $*
do
	read filenameyear filenameday <<< $(basename $file | awk -F"." '{ print $6,$7}' ) 
	msi -S $file | \
	awk -F"|" '{print $5}' | \
	awk -F","  -v year=$filenameyear -v day=$filenameday ' BEGIN { daypu=sprintf("%03d",day+1);daymu=sprintf("%03d",day-1) } 
	{ if ( ($1 != year || ( $2!=day && $2!=daymu && $2!=daypu))  && NR>1 )  print "data in bad file:    '"$file"'  with "$1,$2 " data" } '
done
#echo "The total number of overlap(s) found is $iover"
echo " "

