#!/bin/bash

# 2015/06/29 Jean-Marie Saurel
# Copy miniseed files from 'list of files' following symlinks to the DeliveryDir
# list them in the DeliveryDir.txt
# and add the Q quality flag

if (( "$#" < 2  ))
then
        echo -e "\n$0 follows all symlink from miniseed files in 'list of files'"
        echo -e "  sets the quality flag to Q, copy the files to DeliveryDir"
	echo -e "  and write the list in the DeliveryDir.txt file\n"
        echo -e "Usage: $0 'list of files' DeliveryDir\n"
        echo -e "  'list of files' is either a file containing a list of files"
        echo -e "  or the result of a command containing a list of files (\$(ls )  for example)\n"
        exit
fi

if [ -f $1 ]
then
        LISTE_FILES=`cat $1`
else
        LISTE_FILES=$1
fi

delivery_dir=$2

myname=`hostname | cut -d '.' -f 1`

if [[ -d ${delivery_dir} ]]
then
	echo '/!\ Répertoire '${delivery_dir} 'existe /!\'
	exit 0
else
	mkdir ${delivery_dir}
	if [[ -f ${delivery_dir}.txt ]];then rm ${delivery_dir}.txt;fi
fi


for fichier_a_livrer in ${LISTE_FILES}
do
        if [[ !  ${fichier_a_livrer##*/} =~ ^[A-Z0-9]{1,2}\.[A-Z][A-Z0-9]{2,4}\.[A-Z0-9]{2}\.[A-Z][A-Z][A-Z0-9]\.D\.[0-9][0-9][0-9][0-9]\.[0-9][0-9][0-9]$ ]]
        then
          echo "--> WARNING !! ${sds_file} is not a standard name !!"
          continue
        fi

	msmod --quality Q -A ${delivery_dir}/%Y/%n/%s/%c.D/%n.%s.%l.%c.D.%Y.%j $(readlink -e ${fichier_a_livrer})
	echo "msmod --quality Q -A ${delivery_dir}/%Y/%n/%s/%c.D/%n.%s.%l.%c.D.%Y.%j $(readlink -e ${fichier_a_livrer})"
done

ls ${delivery_dir}/????/*/*/???.D/*.????.??? | awk -v machine=${myname} '{print machine":"$0}' > ${delivery_dir}.txt
