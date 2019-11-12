#! /bin/bash

# Aurelien Mordret 2013 plot_sta_coor_1sta.sh

#if [ "$#" != "2" ]
#then
#	echo -e "\nUsage: $0 dataless_file_name network_code (PF, GL or MQ)\n"
#	exit
#fi

k=0


for dataless in ${*}
do

	stadataless=`rdseed -f $dataless -s | grep B050F03 | awk '{print $4}'`

	lat1=`rdseed -f $dataless -s | grep B050F04 | awk '{print $3}'`

	lon1=`rdseed -f $dataless -s | grep B050F05 | awk '{print $3}'`

	alt1=`rdseed -f $dataless -s | grep B050F06 | awk '{print $3}'`

	net1=`rdseed -f $dataless -s | grep B050F16 | awk '{print $4}'`

	stadatalesslist[k]=$stadataless
	lat[k]=$lat1
	lon[k]=$lon1
	alt[k]=$alt1
	net[k]=$net1

	k=`expr 1 + $k`
	
done
nbsta=${#stadatalesslist[*]}


case ${net[0]} in
PF)
	echo -e "<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<kml xmlns=\"http://www.opengis.net/kml/2.2\"
xmlns:gx=\"http://www.google.com/kml/ext/2.2\">
<Document>
<name>Stations OVPF </name>
<open>0</open>"
;;
WI)
	echo -e "<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<kml xmlns=\"http://www.opengis.net/kml/2.2\"
xmlns:gx=\"http://www.google.com/kml/ext/2.2\">
<Document>
<name>Stations WESTINDIES </name>
<open>0</open>"
;;
MQ)
	echo -e "<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<kml xmlns=\"http://www.opengis.net/kml/2.2\"
xmlns:gx=\"http://www.google.com/kml/ext/2.2\">
<Document>
<name>Stations OVSM </name>
<open>0</open>"

;;
GL)
	echo -e "<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<kml xmlns=\"http://www.opengis.net/kml/2.2\"
xmlns:gx=\"http://www.google.com/kml/ext/2.2\">
<Document>
<name>Stations OVSG </name>
<open>0</open>"
;;
KA)
	echo -e "<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<kml xmlns=\"http://www.opengis.net/kml/2.2\"
xmlns:gx=\"http://www.google.com/kml/ext/2.2\">
<Document>
<name>Stations Kartahala</name>
<open>0</open>"
;;
esac


for i in $(seq 1 $nbsta)
do
	echo -e "<Placemark>
	<name>${stadatalesslist[i-1]}</name>
	<Point>   
	<coordinates>${lon[i-1]},${lat[i-1]},${alt[i-1]}</coordinates>
	</Point>
	</Placemark>"
done
echo -e "</Document>
</kml>"













