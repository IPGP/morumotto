#!/bin/bash

if [ "$#" != "4" ]
then
	echo -e "\nUsage: $0 STALIST YYYY DDDbeg DDDend\n"
	exit
fi

################## Arguments
netcode=( `gawk '{print $1}' $1 | sort -u` )
net=( ` gawk ' $3 ~/HH/ {print $1}' $1 ` )
stalist=( ` gawk ' $3 ~/HH/ {print $2}' $1 ` )
locid=( ` gawk ' $3 ~/HH/ {print $4}' $1 ` )
chan=( ` gawk ' $3 ~/HH/ {print substr($3,1,3)}' $1 ` )
year=$2
juldbeg=$3
juldend=$4


if [ ${#stalist[*]} -eq 0 ]
then
 echo "no HH channel in the stalist ... exit"
 exit
fi
 
################## Paramètres
FDSN_event_server="http://earthquake.usgs.gov/fdsnws/event/1/query?"
#http://earthquake.usgs.gov/fdsnws/event/1/query?format=text&starttime=2015-01-01&endtime=2016-01-02&latitude=-21.15&longitude=55.5&minradius=40&maxradius=85&minmagnitude=7&orderby=magnitude
Arclink_Server="localhost:18001"

Reunion_lat=-21.15
Reunion_lon=55.5
Antilles_lat=15.4
Antilles_lon=-61.2

minmag=6.8
maxmag=7.2

racine=/data1/volobsis/miniseed
workdir=${racine}/out/$USER/SEEDvolume/$(date +%Y%m%d%H%M)
#workdir=/media/saurel/JMS_DATA/SDS_temp/test_script/buildSEED

################## Variables
start_date=$(date -d "$year-01-01 +$juldbeg days -1 day" +"%Y-%m-%d")
end_date=$(date -d "$year-01-01 +$juldend days -1 day" +"%Y-%m-%d")

################## Initialisation du répertoire de travail
if [ ! -d ${workdir} ]
then
	mkdir -p ${workdir}
fi

# Boucle sur les réseaux
for i in `seq 0 $((${#netcode[*]} - 1))`
do
	echo "Working on network "${netcode[i]}
	case ${netcode[i]} in
	PF )		lat=${Reunion_lat}
			lon=${Reunion_lon}
			catalog=${workdir}/reunion.catalog
			;;
	MQ | GL | WI )	lat=${Antilles_lat}
			lon=${Antilles_lon}
			catalog=${workdir}/antilles.catalog
			;;
	esac
	# Récupération du catalogue d'événements à l'USGS
	WS_request="format=text&starttime="${start_date}"&endtime="${end_date}"&latitude="${lat}"&longitude="${lon}"&minradius=40&maxradius=85&minmagnitude="${minmag}"&maxmagnitude="${maxmag}"&orderby=magnitude"
	wget ${FDSN_event_server}${WS_request} -q -O ${catalog}
	# Construit les dates des événements à demander pour au plus les trois événements les plus importants
	events=( `head -n 4 ${catalog} | gawk -F '|' '!/^#/ {
		year=substr($2,1,4);
		month=substr($2,6,2);
		day=substr($2,9,2);
		hour=substr($2,12,2);
		minute=substr($2,15,2);
		debstr=sprintf("%4d %2d %2d %2d %2d 00",year,month,day,hour,minute);
		tsdeb=mktime(debstr);
		print strftime("%Y,%m,%d,%H,%M,%S",tsdeb);
		}'` )
	events_desc=( `head -n 4 ${catalog} | gawk -F '|' '!/^#/ {
		origintime=gensub(" ","_","g",$2);
		region=gensub(" ","_","g",$13);
		magtype=gensub(" ","_","g",$10);
		mag=gensub(" ","_","g",$11);
		print origintime",_"region",_"magtype"="mag;
		}'` )
	echo ${#events[*]}" events found"
	# Boucle sur les événements pour construire les requêtes arclink
	for e in `seq 0 $((${#events[*]} - 1))`
	do
		deb=${events[e]}
		end=( `echo ${events[e]} | gawk -F ',' '{
			endstr=sprintf("%4d %2d %2d %2d %2d 00",$1,$2,$3,$4,$5);
			tsend=mktime(endstr)+3600;
			print strftime("%Y,%m,%d,%H,%M,%S",tsend);
			}'` )
		event_name=$(echo ${events[e]} | sed 's/,/-/g' )
		event_description=$(echo ${events_desc[e]} | sed 's/_/ /g' )
		echo "Evénement le "${event_description}
		# Boucle sur les stations pour construire la requête arclink
		echo "nombre de stations":${#stalist[*]}

		if [ -f ${workdir}/temp.req ]
		then		
			rm ${workdir}/temp.req
		fi
		for s in `seq 0 $((${#stalist[*]} - 1))`
		do
			if [ "${net[s]}" == "${netcode[i]}" ]
			then
#				echo $deb" "$end" "${net[s]}" "${stalist[s]}" "${chan[s]}" "${locid[s]} >> ${workdir}/${event_name}.${netcode[i]}.req
				echo $deb" "$end" "${net[s]}" "${stalist[s]}" "${chan[s]}" "${locid[s]} >> ${workdir}/temp.req
			fi
		done
		sort -u ${workdir}/temp.req > ${workdir}/${event_name}.${netcode[i]}.req
		rm ${workdir}/temp.req
	done
done

# Boucle sur les requêtes
for reqfile in ${workdir}/????-??-??-??-??-00.??.req
do
	SEEDname=$(basename ${reqfile} .req)
	arclink_fetch -a ${Arclink_Server} -n -k fseed -u $USER -o ${workdir}/${SEEDname}.seed ${reqfile}
done

