#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)
DIR_WRAP=$(cd $DIR_HERE/../bin && pwd)

MY_BITBAKE_TARGET_FILE="$(pwd)/bitbake.target"

if [ ! -f "$MY_BITBAKE_TARGET_FILE" ]; then
    echo "ERROR: file not found: $MY_BITBAKE_TARGET_FILE"
    exit 1
fi

MY_BITBAKE_TARGET=$(cat $MY_BITBAKE_TARGET_FILE)

export PATH=$DIR_WRAP:$PATH
source $DIR_HERE/../poky/oe-init-build-env

exec bitbake $MY_BITBAKE_TARGET
