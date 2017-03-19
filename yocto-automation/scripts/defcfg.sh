#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)
DIR_WRAP=$(cd $DIR_HERE/../bin && pwd)

export PATH=$DIR_WRAP:$PATH
source $DIR_HERE/../poky/oe-init-build-env
