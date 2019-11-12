#! /bin/bash
# Aurelien Mordret 2013 Check-Gaps.sh
# Arnaud Lemarchand juillet 2014
#	Ajout du test si fichier vide sinon l'année entière n'est pas calculée 
#	Ajout de 0 pour les jours manquants
# Jean-Marie Saurel novembre 2015
#       Mets à 0 en cas d'échec de msi (pas de données SEED, fichier corrompu ...)
#
jjjp=0

for i
do

if [[ -a $i ]]
then
        yyyy=( `echo $i | awk -F "." '{print $7}'` )
        jjj=( `echo $i | awk -F "." '{print $8}'` )
        cha=( `echo $i | awk -F "." '{print $5}'` )
        sta=( `echo $i | awk -F "." '{print $3}'` )
	#if [[ $i != $1 ]]
	# then
	 #if (( (jjj-jjjp) > 1 ))
	 # then
	 #   for j in {$jjjp+1..$jjj-1..1}
	 #    do
	#	igap=0
	#	 echo "$yyyy-$j $cha $sta $igap"
	#     done
	#  fi 
	#fi
 	if [[ -s $i ]]
	 then
          iatot=` msi -s $i | tail -n1 | awk '{print $6}'`
          if [[ -z $iatot ]]
            then
            iatot=0
          fi
	else
	  iatot=0
	fi
	#jjjp=$jjj
        if [[ $cha == L[HN][ZNE123] ]]
	then
		igap=$(( (100 * $iatot) / 86400 ))
        elif [[ $cha == B[HN][ZNE123] ]]
	then
		igap=$(( (100 * $iatot) / (86400*20) ))
        elif [[ $cha == [EH][HN][ZNE123] ]]
	then
		igap=$(( (100 * $iatot) / (86400*100) ))
	else
		igap=0
	fi
        if (( $igap <= 100 ))
        then

                echo "$yyyy-$jjj $cha $sta $igap"

        fi
fi
done


