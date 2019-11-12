#!/bin/bash
# 
# creation d'un environnement pour l'ajout d'un nouvel 
# utilisateur des routines de validation

user=$1
racine=/data1/volobsis/miniseed
function usage(){
    echo $0 user
    exit
}
for rep in \
  $racine/out/$user \
  $racine/out/$user/PQLX \
  $racine/out/$user/PQLX/log \
  $racine/out/$user/PQLX/LISTFILES \
  $racine/out/$user/listfiles \
  $racine/out/$user/plotresp \
  $racine/out/$user/plotresp/amp_phase_files \
  $racine/out/$user/log \
  $racine/out/$user/kml \
  $racine/out/$user/figures \
  $racine/out/$user/stalist \
  $racine/out/$user/SEEDVolume \
#  $racine/out/$user/FilesNotValidated \
#  $racine/out/$user/FilesWithBadBlocking \
#  $racine/out/$user/FilesWithBadNETSTACHAN \
#  $racine/out/$user/FilesWithBadSampleRate \
#  $racine/out/$user/FilesWithExtention \
#  $racine/out/$user/FilesWithLittleEndian \
# $racine/out/$user/FilesWithOverlaps \
#  $racine/out/$user/FilesWithSteim1 
do
if [ ! -d $rep ]
then
 mkdir -p $rep
fi
done
