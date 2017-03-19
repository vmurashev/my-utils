#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)

exec $DIR_HERE/scripts/runqemu.py --config $DIR_HERE/config/linux_x86_64.ini
