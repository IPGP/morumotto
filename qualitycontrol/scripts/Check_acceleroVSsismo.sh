#!/bin/bash

if [ "$#" != "5" ]
then
	echo -e "\nUsage: $0 STALIST YYYY DDDbeg DDDend min_magnitude\n"
	exit
fi

################## Arguments
netcode=( `awk '{print $1}' $1 | sort -u` )
net=( ` awk ' $3 ~/H[HN][ZNE]/ {print $1}' $1 ` )
stalist=( ` awk ' $3 ~/H[HN][ZNE]/ {print $2}' $1 ` )
locid=( ` awk ' $3 ~/H[HN][ZNE]/ {print $4}' $1 ` )
chan=( ` awk ' $3 ~/H[HN][ZNE]/ {print substr($3,1,3)}' $1 ` )
year=$2
juldbeg=$3
juldend=$4
minmag=$5

################## Paramètres
FDSN_event_server="http://earthquake.usgs.gov/fdsnws/event/1/query?"
#http://earthquake.usgs.gov/fdsnws/event/1/query?format=text&starttime=2015-01-01&endtime=2016-01-02&latitude=-21.15&longitude=55.5&minradius=40&maxradius=85&minmagnitude=7&orderby=magnitude

IRIS_TravelTime_server="http://service.iris.edu/irisws/traveltime/1/query?"
#http://service.iris.edu/irisws/traveltime/1/query?evloc=[-36.122,-72.898]&staloc=[-33.45,-70.67],[47.61,-122.33],[47.37,8.55]&evdepth=22.9&phases=P&noheader&traveltimeonly

Arclink_Server="localhost:18001"

Reunion_lat=-21.15
Reunion_lon=55.5
Antilles_lat=15.4
Antilles_lon=-61.2

maxmag=9.0

racine=/data1/volobsis/miniseed
workdir=${racine}/out/$USER/SEEDvolume/$(date +%Y%m%d%H%M)
SACworkdir=${racine}/out/$USER/SACfiles/$(date +%Y%m%d%H%M)
FiguresDir=${racine}/out/$USER/figures/$(date +%Y%m%d%H%M)
#workdir=/home/saurel/test_script/buildSEED
#SACworkdir=/home/saurel/test_script/SACfiles
#FiguresDir=/home/saurel/test_script/figures

################## Variables
start_date=$(date -d "$year-01-01 +$juldbeg days -1 day" +"%Y-%m-%d")
end_date=$(date -d "$year-01-01 +$juldend days -1 day" +"%Y-%m-%d")

################## Initialisation des répertoires de travail
if [ ! -d ${workdir} ]
then
	mkdir -p ${workdir}
fi
if [ ! -d ${SACworkdir} ]
then
	mkdir -p ${SACworkdir}
fi

################## Récupération des volumes SEED pour au plus trois téléséismes
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
	# Récupération du catalogue des 3 plus gros événements à l'USGS
	WS_request="format=text&starttime="${start_date}"&endtime="${end_date}"&latitude="${lat}"&longitude="${lon}"&minradius=40&maxradius=85&minmagnitude="${minmag}"&maxmagnitude="${maxmag}"&orderby=magnitude&limit=3"
	echo "wget ${FDSN_event_server}${WS_request} -q -O ${catalog}"
	wget ${FDSN_event_server}${WS_request} -q -O ${catalog}
	# Construit les infos des événements à demander
	# origintime_seconds latitude longitude profondeur
	events_params=( `awk -F '|' '!/^#/ {
		year=substr($2,1,4);
		month=substr($2,6,2);
		day=substr($2,9,2);
		hour=substr($2,12,2);
		minute=substr($2,15,2);
		seconde=substr($2,18,2);
		debstr=sprintf("%4d %2d %2d %2d %2d %2d",year,month,day,hour,minute,seconde);
		tsdeb=mktime(debstr);
		lat=$3;
		lon=$4;
		prof=$5;
		print tsdeb,lat,lon,prof;
		}' ${catalog}` )
	# Description des événements
	events_desc=( `awk -F '|' '!/^#/ {
		origintime=gensub(" ","_","g",$2);
		region=gensub(" ","_","g",$13);
		magtype=gensub(" ","_","g",$10);
		mag=gensub(" ","_","g",$11);
		print origintime",_"region",_"magtype"="mag;
		}' ${catalog}` )
	echo $((${#events_params[*]} / 4))" events found"
	# Boucle sur les événements pour récupérer l'heure d'arrivée de la P
	for e in `seq 0 4 $((${#events_params[*]} - 1))`
	do
		Otime=${events_params[e]}
		Olat=${events_params[$(($e + 1))]}
		Olon=${events_params[$(($e + 2))]}
		Odepth=${events_params[$(($e + 3))]}
		# Récupération de l'heure d'arrivée de la P
		WS_request="evloc=["${Olat}","${Olon}"]&staloc=["${lat}","${lon}"]&evdepth="${Odepth}"&phases=P&noheader=true&traveltimeonly=true"
		echo ${IRIS_TravelTime_server}${WS_request}
		Ttime=`curl -s --globoff ${IRIS_TravelTime_server}${WS_request}`
		# Début des données : P - 60s
		deb=( `echo ${Otime} | awk -v traveltime=${Ttime} '{
			print strftime("%Y,%m,%d,%H,%M,%S",$0+traveltime-60);
			}'` )
		# Fin des données : P + 300s
		end=( `echo ${Otime} | awk -v traveltime=${Ttime} '{
			print strftime("%Y,%m,%d,%H,%M,%S",$0+traveltime+300);
			}'` )
		event_name=$(echo "${Otime}_${Olat}_${Olon}_${Odepth}_" | sed 's/,/-/g' )
		event_description=$(echo ${events_desc[$(($e / 4))]} | sed 's/_/ /g' )
		echo "Evénement le "${event_description}
		# Boucle sur les stations pour construire la requête arclink
		this_station=""
		first_sensor=""
		for s in `seq 0 $((${#stalist[*]} - 1))`
		do
			if [ "${net[s]}" == "${netcode[i]}" ] && [ "${stalist[s]}" != "${this_station}" ]
			then
				this_station=${stalist[s]}
				first_sensor=${chan[s]:0:2}
			elif [ "${net[s]}" == "${netcode[i]}" ]
			then
				if [ "${first_sensor}" == "HH" ] && [ "${chan[s]:0:2}" == "HN" ]
				then
					echo $deb" "$end" "${net[s]}" "${stalist[s]}" H* "${locid[s]} >> ${workdir}/${event_name}.${netcode[i]}.req0
				elif [ "${first_sensor}" == "HN" ] && [ "${chan[s]:0:2}" == "HH" ]
				then
					echo $deb" "$end" "${net[s]}" "${stalist[s]}" H* "${locid[s]} >> ${workdir}/${event_name}.${netcode[i]}.req0
				fi
			fi
		done
	done
done

################## Traitement des données récupérées : déconvolution et comparaison accéléro et vélocimètre
# Boucle sur les requêtes arclink à faire
for reqfile in ${workdir}/*_*_*_*_.*.req0
do
	SEEDname=$(basename ${reqfile} .req0)
	if [ -f ${workdir}/${SEEDname}.req0 ]
	then
		sort -u ${workdir}/${SEEDname}.req0 >  ${workdir}/${SEEDname}.req
		rm ${workdir}/${SEEDname}.req0
		# On fait la requête de données
		arclink_fetch -a ${Arclink_Server} -n -k fseed -u $USER -o ${workdir}/${SEEDname}.seed ${workdir}/${SEEDname}.req
		if [ ! -f ${workdir}/${SEEDname}.seed.*.* ]
		then
			echo "No data found for request ${workdir}/${SEEDname}.req"
			break
		fi
		# Récupération des coordonnées de l'événement dans le nom de la requête
		evtLat=$(echo ${SEEDname} | cut -d '_' -f 2)
		evtLon=$(echo ${SEEDname} | cut -d '_' -f 3)
		evtDepth=$(echo ${SEEDname} | cut -d '_' -f 4)
		SACOtime=$(echo ${SEEDname} | awk -F '_' '{print strftime("%Y %j %H %M %S",$1)}')
		# Nom du répertoire de sortie contenant le PDF : date origine du séisme
		EvtOutDir=$(echo ${SEEDname} | awk -F '_' '{print strftime("%Y_%j_%H_%M_%S",$1)}')
		if [ ! -d ${FiguresDir}/${EvtOutDir} ]
		then
			mkdir -p ${FiguresDir}/${EvtOutDir}
		fi
		# Si plusieurs volumes SEED téléchargés, récupération de la liste
		seedlist=( `ls ${workdir}/${SEEDname}.seed.*.*` )
		for n in `seq 0 $((${#seedlist[*]} - 1))`
		do
			seedfile=${seedlist[n]}
			if [ -f ${seedfile} ]
			then
				seedDIR=$(basename ${seedfile})
				if [ ! -d ${SACworkdir}/${seedDIR} ]
				then
					mkdir -p ${SACworkdir}/${seedDIR}
				fi
				cd ${SACworkdir}/${seedDIR}
				# Lecture du volume SEED : données en SAC et fichiers RES
				echo "extract SAC data from SEED volume ${seedfile}"
				cp ${seedfile} ./
				file=$(basename ${seedfile})
				rdseed -f ${file} -d -o 1 -R
				#rm ${file}
				# Extraction de la liste des stations du volume SEED
				rdseed -f ${seedfile} -S
				stations=( `awk '{print $1"_"$2"_"$3"_"$4"_"}' ${SACworkdir}/${seedDIR}/rdseed.stations` )
				echo $stations
				for k in `seq 0 $((${#stations[*]} - 1))`
				do
					# Paramètres de la station (réseau, code, position)
					SACnet=$(echo ${stations[k]} | cut -d '_' -f 2)
					SACstation=$(echo ${stations[k]} | cut -d '_' -f 1)
					SAClat=$(echo ${stations[k]} | cut -d '_' -f 3)
					SAClon=$(echo ${stations[k]} | cut -d '_' -f 4)
					# Calcul de l'heure d'arrivée théorique de la P à la station (WebService IRIS Travel Time)
					WS_request="evloc=["${evtLat}","${evtLon}"]&evdepth="${evtDepth}"&staloc=["${SAClat}","${SAClon}"]&phases=P&noheader&traveltimeonly"
					Pcalc=`curl -s --globoff ${IRIS_TravelTime_server}${WS_request}`
					# On s'intéresse à la fenêtre P-10s - P+60s
					SACdeb=$(echo "$Pcalc - 10" | bc)
					SACend=$(echo "$Pcalc + 60" | bc)
					# On ne traite la station que si on dispose d'un accéléro et d'un sismomètre
					for chan in Z N E
					do
						echo "Trying comparison for station $SACnet.$SACstation"
						if [ -f ????.???.??.??.??.????.$SACnet.$SACstation.??.HN${chan}.?.SAC ] && [ -f ????.???.??.??.??.????.$SACnet.$SACstation.??.HH${chan}.?.SAC ]
						then
							# Génération de la macro SAC
							echo "qdp off" > macro.sac
							# Lecture d'une composante accéléro et sismo
							echo "read ????.???.??.??.??.????.$SACnet.$SACstation.??.HH${chan}.?.SAC ????.???.??.??.??.????.$SACnet.$SACstation.??.HN${chan}.?.SAC" >> macro.sac
							# On renseigne l'heure origine du séisme
							echo "chnhdr O GMT $SACOtime 000" >> macro.sac
							# On enlève la moyenne
							echo "rmean" >> macro.sac
							# On dépointe le signal
							echo "taper" >> macro.sac
							# Déconvolution en accélération des deux signaux, entre 0.2Hz et 5Hz
							echo "transfer from evalresp to acc freq 0.1 0.2 5 10" >> macro.sac
							# Activation de la sortie graphique fichier
							echo "begindevices sgf" >> macro.sac
							# Graphique limité à la portion qui nous intéresse autour de la P
							echo "xlim O $SACdeb $SACend" >> macro.sac
							echo "color on increment on" >> macro.sac
							# On affiche les deux canaux sur le même graphe
							echo "plot2 absolute" >> macro.sac
							# Fermeture du fichier
							echo "enddevices sgf" >> macro.sac
							echo "quit" >> macro.sac
							# Exécution de la macro SAC
							sac macro.sac
							# Transformation de la figure en PostScript
							sgftops f001.sgf $SACnet.$SACstation.${chan}.ps 1 i
							# Transformation de la figure en PDF
							ps2pdf $SACnet.$SACstation.${chan}.ps $SACnet.$SACstation.${chan}.pdf
							rm f001.sgf $SACnet.$SACstation.${chan}.ps
						else
							echo "No HH and HN data found"
						fi
					done
				done
			# Assemblage des PDF par canaux en un seul document PDF et déplacement dans le dossier de sortie
			pdfunite $(ls ${SACworkdir}/${seedDIR}/??.*.?.pdf) "${SEEDname}.pdf"
			mv ${SEEDname}.pdf ${FiguresDir}/${EvtOutDir}/$n.pdf
			fi
		done
	if [ $n -gt 0 ]
	then
		# Si on a traité plusieurs volumes SEED pour un événement, on assemble les sorties
		pdfunite ${FiguresDir}/${EvtOutDir}/?.pdf "${FiguresDir}/${EvtOutDir}.pdf"
	else
		mv ${FiguresDir}/${EvtOutDir}/0.pdf "${FiguresDir}/${EvtOutDir}.pdf"
	fi
	rm -r ${FiguresDir}/${EvtOutDir}
	fi
done


