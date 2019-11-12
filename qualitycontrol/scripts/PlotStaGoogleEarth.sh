#! /bin/bash

# Aurelien Mordret 2013 PlotStaGoogleEarth.sh
# A. Lemarchand 201410
racine=/data1/volobsis/miniseed
kmlfile=${racine}/out/$USER/kml/$(date +%Y%m%d%H%M)Stamap.kml 
/opt/volobsis/validationSEED/plot_sta_coor_1sta.sh ${*} >> $kmlfile

#cat Stamap.kml | mailx -a Stamap.kml -s "Station map" jacques@ipgp.fr
#echo -e "Station coordinates sent by email"



