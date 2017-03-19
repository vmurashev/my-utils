#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)
DIR_WRAP=$(cd $DIR_HERE/../bin && pwd)

MY_MACHINE_ARCH_FILE="$(pwd)/machine.arch"

if [ ! -f "$MY_MACHINE_ARCH_FILE" ]; then
    echo "ERROR: file not found: $MY_MACHINE_ARCH_FILE"
    exit 1
fi

MY_MACHINE_ARCH=$(cat $MY_MACHINE_ARCH_FILE)

export PATH=$DIR_WRAP:$PATH
source $DIR_HERE/../poky/oe-init-build-env

sudo modprobe tun
exec runqemu $MY_MACHINE_ARCH
