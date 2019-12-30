#!/bin/bash -e
# Morumotto script to check all requirements are installed
# ************************************************************************#
#                                                                         #
#    Copyright (C) 2019 RESIF/IPGP                                        #
#                                                                         #
#    This program is free software: you can redistribute it and/or modify #
#    it under the terms of the GNU General Public License as published by #
#    the Free Software Foundation, either version 3 of the License, or    #
#    (at your option) any later version.                                  #
#                                                                         #
#    This program is distributed in the hope that it will be useful,      #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of       #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        #
#    GNU General Public License for more details.                         #
#                                                                         #
#    This program is part of 'Morumotto'.                                 #
#    It has been financed by RESIF (Réseau sismologique & géodésique      #
#    français )                                                           #
#                                                                         #
#  ***********************************************************************#

# DATASELECT
if ! [ -x "$(command -v dataselect)" ]; then
  echo >&2 "ERROR : dataselect is not\
  installed. Please install dataselect >= 3.20:\
  https://github.com/iris-edu/dataselect"
  exit 1
fi

DATASELECT_VERSION=$(dataselect -V 2>&1)
VERSION=${DATASELECT_VERSION##*: }

if (( $(echo "${VERSION} <= 3.19" |bc -l) )); then
  echo "Your dataselect software version is ${VERSION}, must be >= 3.20\
  Please install dataselect >= 3.20: https://github.com/iris-edu/dataselect"
  exit 1
fi

# MSI
if ! [ -x "$(command -v msi)" ]; then
  echo >&2 "ERROR : msi (miniSEED inspector)\
  is not installed. Please install msi\
  https://github.com/iris-edu/msi"
  exit 1
fi

# QMERGE
if ! [ -x "$(command -v qmerge)" ]; then
  echo >&2 "ERROR : qmerge \
  is not installed. Please install qmerge : \
  http://www.ncedc.org/qug/software/ucb/qmerge.2014.329.tar.gz"
  exit 1
fi

# CPULIMIT
if ! [ -x "$(command -v cpulimit)" ]; then
  echo >&2 "ERROR : cpulimit \
  is not installed. Please install cpulimit : \
  Package available on ubuntu, debian and centos repositories"
  exit 1
fi
