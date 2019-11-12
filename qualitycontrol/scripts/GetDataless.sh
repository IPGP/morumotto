#!/bin/bash

racine=/data1/volobsis/miniseed/in/dataless/SEED

if [ !  -d $racine ]
then
 mkdir -p $racine
fi

for rep in GL MQ PF WI ovsm ovsg ovpf
do
 if [ !  -d $racine/$rep ]
 then
  mkdir -p $racine/$rep
 fi
done

if [ !  -d $racine/ovsg/.svn ]
then
 svn checkout https://svn.ipgp.fr/ovsg/dataless $racine/ovsg --username ovs --password "00000000"
else
 svn update $racine/ovsg --username ovs --password "000000000000000000"
fi

if [ !  -d $racine/ovsm/.svn ]
then
 svn checkout https://svn.ipgp.fr/ovsm/trunk/dataless/stations/  $racine/ovsm  --username ovs --password "o0000000000000"
else
 svn update $racine/ovsm --username ovs --password "00000000000000000000000"
fi

if [ !  -d $racine/ovpf/.svn ]
then
 svn checkout https://svn.ipgp.fr/ovpf/trunk/dataless  $racine/ovpf ovs --password "0000000000000000000000"
else
 svn update $racine/ovpf --username ovs --password "0000000000000000"
fi

rm -rf $racine/GL/* $racine/MQ/*  $racine/PF/* $racine/WI/*

rsync -av   $(find $racine/ovsg/GL/ -name GL*dataless)  $racine/GL
rsync -av   $(find $racine/ovsm/ -name MQ*dataless)  $racine/MQ
rsync -av   $(find $racine/ovpf/ -name OVPF*dataless)  $racine/PF
rsync -av   $(find $racine/ovs* -name WI*dataless)  $racine/WI

for NET in GL MQ PF WI VG
do
 if [ ! -d $racine/../RESP/$NET ]
 then
   mkdir -p $racine/../RESP/$NET
 fi
 rm $racine/../RESP/$NET/*
 rm $racine/$NET/*template*.dataless
 for dataless in $racine/$NET/*.dataless; do /usr/local/bin/rdseed -Rf  $dataless -q $racine/../RESP/$NET ; done
done

#export PQLXLOG=/opt/PQLX/PROD/log
export PQLXLOG=/data1/volobsis/miniseed/out/arnaudl/PQLX/log
/opt/PQLX/PROD/bin/LINUX/pqlxSrvr --dbName=PFdb 4
/opt/PQLX/PROD/bin/LINUX/pqlxSrvr --dbName=MQdb 4
/opt/PQLX/PROD/bin/LINUX/pqlxSrvr --dbName=GLdb 4
/opt/PQLX/PROD/bin/LINUX/pqlxSrvr --dbName=WIdb 4
/opt/PQLX/PROD/bin/LINUX/pqlxSrvr --dbName=KAdb 4
/opt/PQLX/PROD/bin/LINUX/pqlxSrvr --dbName=DJdb 4

echo " last update of datalesses:"$(date) > $racine/../DatalessUpdate.log 
