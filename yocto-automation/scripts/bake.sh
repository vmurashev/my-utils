#!/bin/bash -e

BITBAKE_TARGET=$1
DIR_HERE=$(cd $(dirname $0) && pwd)
DIR_WRAP=$(cd $DIR_HERE/../bin && pwd)

export PATH=$DIR_WRAP:$PATH
source $DIR_HERE/../poky/oe-init-build-env

exec bitbake $BITBAKE_TARGET
