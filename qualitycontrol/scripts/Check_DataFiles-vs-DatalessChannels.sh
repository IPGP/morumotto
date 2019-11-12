#! /bin/bash

# Arnaud Lemarchand janvier 2016
# Ce script a pour vocation de remplacer le script  "Check-list_PathsArchive.sh" écrit par Aurélien Mordret en 2013
# Le script Check-list_PathsArchive.sh gérait mal:
#	- l'ouverture et la fermetre d'un même canal 
#	  les vérifications ne prennent pas en compte qu'un
#	  canal indentique peut se fernmer puis s'ouvrir juste après
#	  En effet la vérification considérait les entrées  
#	  du fichier stalist indépendamment les unes des autres.
#	- Les locId d'un mêmen nom de canal sont mal gérés aussi
# Le script  a une approche differente:
#	a- la vérification se fait sur une année.
#	b- Pour chaque jour de l'année qui est inclu dans une epoch des entrées du stalist
#	  la présence du fichier associé est vérifié
#	c- Pour chaque fichier de l'arborescence, le script vérifie  qu'il y a au moins une
#	 entrée   

if [ "$#" != "3" ]
then
	echo -e "\nUsage: $0  STALIST YEAR  datapath\n"
	exit
fi
[[ -e $1 ]] ||  { echo -e "stalist $1 do not exist" ; exit 1; }
[[ $2 =~ ^20[0-9][0-9]$  ]] ||  { echo "$2 is not a year 20[0-9][0-9] expected"; exit 1; }
[[ -d $3 ]] || { echo "repertory $3 do not exist"; exit 1; }
################## variables
netcode=`awk '{print $1}' $1 | sort -u`
net=( `awk '{print $1}' $1` )
stalist=( `awk '{print $2}' $1` )
locid=( `awk '{print $4}' $1` )
chan=( `awk '{print $3}' $1` )
ybeg=( `awk '{print $5}' $1 | awk -F "," '{print $1}'` )
dbeg=( `awk '{print $5}' $1| awk -F "," '{print $2}'` )
yend=( `awk '{print $6}' $1| awk -F "," '{ if ( $1 !=  "(null)" ) a=$1; else a="9999" } {print a}'` )
dend=( `awk '{print $6}' $1| awk -F "," '{ if ( length($2) != 0 ) a=$2; else a="366"}   {print a}' ` )

YEAR=$2
mainpath=$3
echo -e "\n********** execution of:$0  $@ ---------------->"
echo -e "\n********** Checking dataless versus SDS structures  ---------------->"
	for i in `seq 0 $((${#stalist[*]} - 1))`
	do
	  if (( "${ybeg[i]}" <= "$YEAR"  &&  "${yend[i]}" >= "$YEAR" ))
	   then
		if (( "${ybeg[i]}" == "$YEAR" ))
		 then 
			startday=${dbeg[i]}
		 else
		        startday=1
		fi
		if (( "${yend[i]}" == "$YEAR" ))
		 then 
			endday=${dend[i]}
		 else
			endday=$(date -d $YEAR"-12-31" +%j)
		fi
		echo -e "--------> CHECK !!  ${net[$i]}.${stalist[$i]}.${locid[$i]}.${chan[$i]} - from $YEAR.$startday to $YEAR.$endday "
		allpath=`paste -d '/' <(echo "$mainpath") <(echo "$YEAR") <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "${chan[i]}")`
                if [[ ! -d $allpath ]]
                 then
                        echo -e "----------------> WARNING !! The path $allpath does not exist in the archive!!"
		 else
		   for day in `seq $startday  $endday`		
		    do
			filename=`paste -d '.' <(echo "${net[i]}") <(echo "${stalist[i]}") <(echo "${locid[i]}") <(echo "${chan[i]}") <(echo "$YEAR") <(printf "%03.f" $day) `
			fullpath="$allpath/$filename"
			[[ ! -s "$fullpath"  ]] &&	echo -e  "--------> WARNING !! no file $fullpath in the SDS archive ( $mainpath ) "
		    done
		fi
	  fi
	done	

echo -e "\n********** Checking SDS versus channels declared in dataless   ---------------->"

	[[ -d "$mainpath/$YEAR/${net[1]}" ]] || { echo -e  "--------> WARNING !! $mainpath/$YEAR/${net[1]} repertory do not exist " ; exit 1; }
    Sortstalist=( `awk '{print $2}' $1 | sort -u` )
    for i in `seq 0 $((${#Sortstalist[*]} - 1))`
     do
	for file in $mainpath/$YEAR/${net[1]}/${Sortstalist[i]}/[EH][HN]*/*
	 do
           fnameArch=`echo $file | awk -F'/' '{print $NF}' | awk -F'.' '{print $1"."$2"."$3"."$4"."$5"."$6}'`
	   tsta=`echo $file | awk -F'/' '{print $NF}' | awk -F'.' '{print $2}'`
	   tloc=`echo $file | awk -F'/' '{print $NF}' | awk -F'.' '{print $3}'`
	   tcha=`echo $file | awk -F'/' '{print $NF}' | awk -F'.' '{print $4}'`
	   tday=`echo $file | awk -F'/' '{print $NF}' | awk -F'.' '{print $7}'`
           fnameArchfull=`echo $file | awk -F'/' '{print $NF}' | awk -F'.' '{OFS=".";print $0}'`
          if [[ ! "$fnameArchfull" =~ [A-Z0-9]{1,2}.[A-Z][A-Z0-9]{2,4}.[A-Z0-9]{2}.[A-Z][A-Z][A-Z0-9].D.[0-9][0-9][0-9][0-9].[0-9][0-9][0-9] ]] 
	  then
		 echo -e "\t----------------> WARNING !! $fnameArchfull is not a standard name !!"
		continue
	  fi
	  tybeg=( `grep $tsta  $1 | grep "$tcha.D $tloc" | awk '{print $5}' | awk -F "," '{print $1}'` )
	  tdbeg=( `grep $tsta  $1 | grep "$tcha.D $tloc" | awk '{print $5}' | awk -F "," '{print $2}'` )
	  tyend=( `grep $tsta  $1 | grep "$tcha.D $tloc" | awk '{print $6}' | awk -F "," '{ if ( $1 !=  "(null)" ) a=$1; else a="9999" } {print a}'` )
	  tdend=( `grep $tsta  $1 | grep "$tcha.D $tloc" | awk '{print $6}' | awk -F "," '{ if ( length($2) != 0 ) a=$2; else a="366"}   {print a}' ` )
	  if [[ -z $tybeg  ]]
	  then
		echo -e "\t----------------> WARNING !! no entry for $file in $1 !!"
		continue
	  fi
## remarque syntaxe $((10#$variable))  convertit la chaine variable  en entier en base 10
	  filedate=$( date -d  "$YEAR/01/01  + $(( $((10#$tday-1)) )) day " +%s )  
	  k=0;
	  for j in `seq 0 $((${#tybeg[*]} - 1))`
	   do
	    starttime=$(date -d  "$((10#${tybeg[j]}))/01/01 +  $(( $((10#${tdbeg[j]}))-1 ))  day " +%s )
	    if [[ $((10#${tyend[j]})) == "9999" ]]
	    then
		endtime=$(  date -d  "2400/01/01 " +%s )
	    else
	    	endtime=$(  date -d  "$((10#${tyend[j]}))/01/01 +  $(( $((10#${tdend[j]}))-1 ))  day " +%s ) 
	    fi
	    ((  $starttime <= $filedate   &&     $endtime >= $filedate )) && (( k +=1 ))
	  done
	  (( $k == O ))  && echo -e "\t----------------> WARNING !! $file has no response defined in $1 for the day :$tday"
	  (( $k >  1 ))  && echo -e "\t----------------> WARNING !! $file has too many responses defined in datalesses"
	done
    done
exit
