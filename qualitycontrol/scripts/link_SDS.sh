#!/bin/bash

# 2015/06/29 Jean-Marie Saurel
# Link miniseed files from 'list of files' to the Destination Root Directory
# following an SDS structure

if (( "$#" < 2  ))
then
	echo -e "\n$0 links miniseed files to the DestinationRootDirectory"
	echo -e "  following and SDS structure\n"
	echo -e "Usage: $0 'list of files' DestinationRootDirectory\n"
	echo -e "  'list of files' is either a file containing a list of files"
	echo -e "  or the result of a command containing a list of files (\$(ls )  for example)\n"
	exit
fi

if [ -f $1 ]
then
	LISTE_FROM=`cat $1`
else
	LISTE_FROM=$1
fi

TO_SDS=$2

if [[ ! -d ${TO_SDS} ]]
then
	mkdir -p ${TO_SDS}
fi


for msfile in ${LISTE_FROM}
do
#	echo $msfile
	msname=`basename $msfile`
	net=`echo $msname | cut -d '.' -f 1`
	sta=`echo $msname | cut -d '.' -f 2`
	loc=`echo $msname | cut -d '.' -f 3`
	chan=`echo $msname | cut -d '.' -f 4`
	year=`echo $msname | cut -d '.' -f 6`
	julday=`echo $msname | cut -d '.' -f 7`
	TO_DIR=`echo ${TO_SDS}/${year}/${net}/${sta}/${chan}.D`
	if [ -h ${TO_DIR}/${msname} ]
	then
		echo "--remove old symlink and create new one--"
		rm ${TO_DIR}/${msname}
		ln -s $msfile ${TO_DIR}/${msname}
	elif [ -f ${TO_DIR}/${msname} ]
	then
		echo "--rename old file and create a symlink--"
		mv ${TO_DIR}/${msname} ${TO_DIR}/${msname}.old
		ln -s $msfile ${TO_DIR}/${msname}
	elif [ -d ${TO_DIR} ]
	then
		echo "--create a symlink--"
		ln -s $msfile ${TO_DIR}/${msname}
	else
		echo "--create ${TO_DIR} and a symlink--"
		mkdir -p -m 775  ${TO_DIR}
		ln -s $msfile ${TO_DIR}/${msname}
	fi
done
