#!/bin/bash

UPDATE_TIME_LIMIT=$(( 60 * 60 * 2))
# Check if we should try to update the package list
CURRENT_TIME=$(date +%s)
LAST_UPDATE=$(stat /var/cache/apt/pkgcache.bin -c %Y || echo ${CURRENT_TIME})
if (( ${CURRENT_TIME} - ${LAST_UPDATE} > $UPDATE_TIME_LIMIT )) ; then
  sudo apt-get update
fi
sudo apt-get install --force-yes -yq vlc -o DPkg::Options::=--force-confdef
exit 0
