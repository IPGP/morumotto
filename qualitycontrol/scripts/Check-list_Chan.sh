#! /bin/bash
# Aurelien Mordret 2013 Check-list_Chan4WI.sh
# Arnaud Lemarchand 20150703 paramétrage du test du blocking en fonction du réseau
#		PF :4096
#		autres 512 
# Arnaud Lemarchand 20160830 test du blocking en 4 k pour tous les réseaux.

if [ "$#" != "1" ]
then
        echo -e "\nUsage: $0 file_list\n"
        #exit
fi

echo "start Check-list_Chan"

echo "Listing STA CHA LOC of Namefiles ......"
#touch temp.cha
#for i
#do
# ls -la $i | awk -F"." '{print $(NF-5),$(NF-4),$(NF-3),$(NF-2)}' >>temp.cha
#done
#sort -u temp.cha
#rm temp.cha

echo "Namefiles listed"
echo " Listing miniseed files with headers which don't verify  [LBEH][HN][ZNE123] as channel code, if data are in STEIM2 4096o"
for i
do
#       msi -p $i  | grep "_" | awk -F"," '{OFS="_";print $1}'|awk -F"_" ' $4!~/[H][H][ZNE123]/ {print $4}' | sort -u 
# modification de la ligne pour test en 4k pour tous les réseaux
#        msi -p $i  | awk -F":" -v blocking="512"  'BEGIN {
        msi -p $i  | awk -F":" -v blocking="4096"  'BEGIN {
                                                n=split("'$i'",f,"/")	
                                                m=split(f[n],filename,".")
						if ( filename[1] == "PF" || filename[1] == "KA" )
						{
							blocking="4096"
						}
                                        }
        {
                if ( $1~/[A-Z][A-Z]_[A-Z][A-Z][A-Z]_[0-9][0-9]_[A-Z][A-Z][A-Z0-9], .*/)
                {
                        split($1,a,",") 
                        split(a[1],b,"_")
			CHAN=b[4];
                        if ( filename[1]!=b[1] || filename[2]!=b[2] || filename[3]!=b[3] || filename[4]!=b[4] )
                        {
                                print  "bad NET_STA_CHA_LOC :", b[1],b[2],b[3],b[4], "in file '$i'" ;
                        }
                }       
               if ( $1~/encoding.*/ && $2!~/STEIM 2.*/ )
                {
                        print "'$i' bad encoding: " $2""
                }
                if ( $1~/byte order.*/ && $2!~/Big endian.*/)
                {
                        print "'$i' bad byte order:" $2""
                }
                if ( $1~/record length.*/ && $2!~blocking)
                {
                        print("'$i' bad blocking:",$2,blocking) 
                }
                if ( $1 ~/sample rate factor.*/ )
                {
			if ( CHAN~/[EH][HN][ZNE123]/ && $2!~/100 .*/ ) {print "'$i' bad sample rate: " $2" for channel " CHAN  }
			if ( CHAN~/B[HN][ZNE123]/ && $2!~/20 .*/ ) {print "'$i' bad sample rate: " $2" for channel " CHAN  }
			if ( CHAN~/L[HN][ZNE123]/ && $2!~/1 .*/ ) {print "'$i' bad sample rate: " $2" for channel " CHAN  }
                }

        }' | sort -u

done
echo "Headers files check is finished"
echo "End Check-list_Chan"
      
