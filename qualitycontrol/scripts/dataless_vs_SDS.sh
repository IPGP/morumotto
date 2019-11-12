#!/bin/bash

# Kevin Juhel (septembre 2016)

# Ce script a pour vocation de remplacer le script "Check_DataFiles-vs-DatalessChannels.sh"
# ecrit par Arnaud Lemarchand en janvier 2016 et le script "Check-list_PathsArchive.sh"
# par Aurelien Mordret en 2013

# Le script Check-list_PathsArchive.sh gerait mal :
#	 - l'ouverture et la fermeture d'un meme canal
#	    Les verifications ne prennent pas en compte qu'un canal
#     identique peut se fermer puis s'ouvrir juste apres.
#	    En effet la verification considerait les entrees du
#	    fichier stalist independamment les unes des autres.
#	 - les locId d'un meme nom de canal sont mal geres aussi

# Le script Check_DataFiles-vs-DatalessChannels.sh a une approche differente :
#	 a - la verification se fait sur une annee
#	 b - pour chaque jour de l'annee qui est inclu dans une epoch des
#       entrees du stalist la presence du fichier associe est verifiee
#	 c - pour chaque fichier de l'arborescence, le script
#       verifie qu'il y a au moins une entree

# Nouvelle version :
# Sont verifies les cas suivants :
#   - data sans dataless
#   - data avec 2 dataless ou plus
# Ne sont plus verifies :
#   - dataless sans donnee
# La verification se fait maintenant a l'echantillon pres (0.01 seconde).


##############################################################
# CHECK THE EXECUTION OF COMMAND AND INPUT PARAMETERS FORMAT #
##############################################################

if [ "$#" != "3" ]
then
	echo -e "\nUsage: $0 STALIST YEAR datapath\n"
	exit
fi

[[ -e $1 ]] || { echo -e "stalist file $1 does not exist" ; exit 1; }
[[ $2 =~ ^20[0-9][0-9]$  ]] ||  { echo "$2 is not a year 20[0-9][0-9] expected"; exit 1; }
[[ -d $3 ]] || { echo "data directory $3 does not exist"; exit 1; }

YEAR=$2
mainpath=$3

###
###

sortnet=( `awk '{print $1}' $1 | sort -u` )
for h in `seq 0 $((${#sortnet[*]}-1))` # loop over the networks
do

  sortsta=( `awk '{print $2}' $1 | sort -u` )
  for i in `seq 0 $((${#sortsta[*]}-1))` # loop over the stations
  do

    sortchan=( `grep ${sortsta[i]} $1 | awk '{print $3}' | sort -u` )
    for j in `seq 0 $((${#sortchan[*]}-1))` # loop over the channels
    do

      # define sample rate (in seconds and milliseconds)
      if [[ "${sortchan[j]}" =~ H[HN][A-Z0-9].D ]]
      then
        sampledt=0.010
        millidt=10
      elif [[ "${sortchan[j]}" =~ BH[A-Z0-9].D ]]
      then
        sampledt=0.025
        millidt=25
      elif [[ "${sortchan[j]}" =~ LH[A-Z0-9].D ]]
      then
        sampledt=1.0
        millidt=1000
      elif [[ "${sortchan[j]}" =~ EH[A-Z0-9].D ]]
      then
        sampledt=0.010
        millidt=10
      else
        echo ${sortchan[j]} "is not a expected channel format !"
        exit 1
      fi

#####################
# 20180203 Lemarchand
# add a loop over locID
      sortloc=( `grep ${sortnet[h]} $1 | grep ${sortsta[i]} | grep ${sortchan[j]}  | awk '{print $4}' | sort -u` )
      for l in `seq 0 $((${#sortloc[*]}-1))` # loop over the locid
      do
#####################
      
      ####################################################
      # LOOK FOR GAPS AND OVERLAPS IN STAFILE (DATALESS) #
      ####################################################

        echo -e "--> INFO !! start checking epochs of  ${sortnet[h]} ${sortsta[i]} ${sortchan[j]} - ${sortloc[l]}"
      
      # initialize singularity arrays for gaps
      gaps_beg=()
      gaps_end=()

      # initialize singularity arrays for overlaps
      overlaps_beg=()
      overlaps_end=()

      count=`grep ${sortnet[h]} $1 | grep ${sortsta[i]} | grep  ${sortchan[j]} | grep -c "D ${sortloc[l]}" ` # number of epochs for a given station channel and locid

      epochs_beg=( `grep ${sortnet[h]} $1 | grep ${sortsta[i]} | grep ${sortchan[j]} | grep "D ${sortloc[l]}" | awk '{print $5}'` )
      epochs_end=( `grep ${sortnet[h]} $1 | grep ${sortsta[i]} | grep ${sortchan[j]} | grep "D ${sortloc[l]}" | awk '{if ( $6!="(null)" ) a=$6; else a="2400,001"} {print a}'` )

      # compute dates for the very first and last samples of epoch (with 1 sample margin)
      deb=$(date -d "`echo ${epochs_beg[0]} | awk -v a="$sampledt" -F, '{print $1"/01/01 +"$2-1"days -"a"seconds "$3}'`" +"%Y,%j,%T.%4N")
      fin=$(date -d "`echo ${epochs_end[-1]} | awk -v a="$sampledt" -F, '{print $1"/01/01 +"$2-1"days +"a"seconds "$3}'`" +"%Y,%j,%T.%4N")

      beg_year=`echo ${epochs_beg[0]} | awk -F, '{print $1}'`
      end_year=`echo ${epochs_end[-1]} | awk -F, '{print $1}'`

#####################
# 20170712 Lemarchand
# Skip  all the test if the year in not 
# the dataless epoch  
      if [[ $beg_year > $YEAR  ||  $end_year < $YEAR ]]
      then
        echo -e "--> INFO !! $YEAR not in the range of for station ${sortsta[i]} (${sortnet[h]} - ${sortchan[j]})"\
          "between ${epochs_beg[0]} and ${epochs_end[-1]} !"
        continue
      fi
# end modification
###################

      if [ $count -gt 1 ]
      then
        for k in `seq 0 $(($count-2))` # loop over the epochs
        do

          # compute date of last sample of the considered epoch (milliseconds from 1970)
          t1=$(date -d "`echo ${epochs_end[k]} | awk -F, '{print $1"/01/01 +"$2-1"days "$3}'`" +%s%4N)

          # compute date of first sample of the following epoch (milliseconds from 1970)
          t2=$(date -d "`echo ${epochs_beg[k+1]} | awk -F, '{print $1"/01/01 +"$2-1"days "$3}'`" +%s%4N)


          diff=$(($t2 - $t1))
#####################
# 20180203 Lemarchand
# do not output a message for overlpap in dataless
# do not output a message if diff is less than 1/samplerate
          if  [ $diff -eq $millidt ]
          then :
#           echo -e "--> OK !! no gap or overlap in dataless for station ${sortnet[h]}  ${sortsta[i]}  ${sortchan[j]}  ${sortloc[l]}"\
#              "between ${epochs_beg[0]} and ${epochs_end[-1]} !" >/dev/null

# 	  check for dataless gaps --> WARNING !
          elif [ $diff -gt $millidt ]
          then
           echo -e "--> WARNING !! dataless gap for station ${sortnet[h]}  ${sortsta[i]}  ${sortchan[j]}  ${sortloc[l]} "\
             "between ${epochs_end[k]} and ${epochs_beg[k+1]} !"

            gaps_beg+=(${epochs_end[k]})
            gaps_end+=(${epochs_beg[k+1]})

          # check for dataless overlaps --> WARNING !
          elif [ $diff -lt 0 ] || [ $diff -eq 0 ]
          then
            echo -e "--> ERROR !! dataless overlap for station ${sortnet[h]}  ${sortsta[i]}  ${sortchan[j]}  ${sortloc[l]} "\
              "between ${epochs_beg[k+1]} and ${epochs_end[k]} !"

            overlaps_beg+=(${epochs_beg[k+1]})
            overlaps_end+=(${epochs_end[k]})

          else :
#            echo -e "--> WARNING !! difference between epochs is less than a sample for station"\
#              "${sortnet[h]}  ${sortsta[i]}  ${sortchan[j]}  ${sortloc[l]}) between ${epochs_end[k]} and ${epochs_beg[k+1]} !"
          fi
        done # loop over epochs

      else :
#       echo -e "--> OK !! no gap or overlap in dataless for station ${sortnet[h]}  ${sortsta[i]}  ${sortchan[j]}  ${sortloc[l]} "\
#          "between ${epochs_beg[0]} and ${epochs_end[-1]} !"
      fi
#####################

      ####################################################
      # CHECK FOR SDS ARCHIVE / DATALESS INCOMPATIBILITY #
      #                                                  #
      # confront every SDS archive to deb, fin and every #
      # singularity (if present) : precision is now down #
      # to the sample (millisecond)                      #
      #                                                  #
      # are checked :                                    #
      #     - data without dataless                      #
      #           --> WARNING !!                         #
      #     - data with 2 or more datalesses             #
      #           --> ERROR !!                           #
      #                                                  #
      # are not checked :                                #
      #     - dataless without data : not important      #
      #     - no dataless and no data : that's ok !      #
      ####################################################

#####################
# 20170712 Lemarchand
# Skip  the scanned repertory does ot exits
# 
        if [ ! -d $mainpath/$YEAR/${sortnet[h]}/${sortsta[i]}/${sortchan[j]} ]
        then
	  echo -e "--> INFO !! $mainpath/$YEAR/${sortnet[h]}/${sortsta[i]}/${sortchan[j]} does not exist"
          continue
        fi	
# end modification
######################       

      for sds_file in $mainpath/$YEAR/${sortnet[h]}/${sortsta[i]}/${sortchan[j]}/*${sortloc[h]}*[0-9]
      do

      # check the data file name format
	filename="${sds_file##*/}"
        if [[ !  ${filename} =~ ^[A-Z0-9]{1,2}\.[A-Z][A-Z0-9]{2,4}\.[A-Z0-9]{2}\.[A-Z][A-Z][A-Z0-9]\.D\.[0-9][0-9][0-9][0-9]\.[0-9][0-9][0-9]$ ]]
        then
	  if [[ ${filename}  ==  "$mainpath/$YEAR/${sortnet[h]}/${sortsta[i]}/${sortchan[j]}/*${sortloc[h]}*[0-9]" ]]
	  then
	    echo "--> WARNING !! no file like regex ${filename}!!"
	  else
            echo "--> WARNING !! ${sds_file} is not a standard name !!"
	  fi
	  continue
        fi

        sds_day="${sds_file##*.}"  
        beg_day=`echo ${epochs_beg[0]} | awk -F"," '{print $2}'`
        end_day=`echo ${epochs_end[-1]} | awk -F"," '{print $2}'`

       # check if datafile is outside the recording epoch
        if [ "$sds_day" -le  "$beg_day" ]
        then
          dataselect -te "$deb" -Pe -o tmp.mseed $sds_file
          if [ -e tmp.mseed ]
          then
            echo "--> ERROR !! data $sds_file with no dataless before ${epochs_beg[0]}"
            rm tmp.mseed
          fi
        fi

        if [ "$sds_day" -ge "$end_day" ]
        then
          dataselect -ts "$fin" -Pe -o tmp.mseed $sds_file
          if [ -e tmp.mseed ]
          then
            echo "--> ERROR !! data $sds_file with no dataless after ${epochs_end[-1]}"
            rm tmp.mseed
          fi
        fi

        # check if datafile is within the recording epoch
        if [ "$sds_day" -ge  "$beg_day" ] && [ "$sds_day" -le "$end_day" ]
        then

          # 1 : GAPS
          if [ ${#gaps_beg[*]} != 0 ]
          then
            for l in `seq 0 $((${#gaps_beg[*]}-1))`
            do

              beg_day=`echo ${gaps_beg[l]} | awk -F, '{print $2}'`
              end_day=`echo ${gaps_end[l]} | awk -F, '{print $2}'`
              if [ $sds_day -ge $beg_day ] && [ $sds_day -le $end_day ]
              then

                dataselect -ts "${gaps_beg[l]}" -te "${gaps_end[l]}" -Pe -o tmp.mseed $sds_file
                if [ -e tmp.mseed ]
                then
                  rm tmp.mseed
                  echo "--> ERROR !! data $sds_file with no dataless inside the"\
                    "interval ${gaps_beg[l]} - ${gaps_end[l]}"
                fi

              fi
            done
          fi

          # 2 : OVERLAPS
          if [ ${#overlaps_beg[*]} != 0 ]
          then
            for l in `seq 0 $((${#overlaps_beg[*]}-1))`
            do

              beg_day=`echo ${overlaps_beg[l]} | awk -F, '{print $2}'`
              end_day=`echo ${overlaps_end[l]} | awk -F, '{print $2}'`
              if [ $sds_day -ge $beg_day ] && [ $sds_day -le $end_day ]
              then

                dataselect -ts "${overlaps_beg[l]}" -te "${overlaps_end[l]}" -Pe -o tmp.mseed $sds_file
                if [ -e tmp.mseed ]
                then
                  rm tmp.mseed
                  echo "--> ERROR !! data $sds_file with 2 or more datalesses inside the"\
                    "interval ${overlaps_beg[l]} - ${overlaps_end[l]}"
                fi

              fi
            done
          fi

        fi
      done # loop over SDS data files
     done # loop locId
    done # loop over channels
  done # loop over stations
done # loop over networks
                  echo "--> INFO !! end"\
exit
