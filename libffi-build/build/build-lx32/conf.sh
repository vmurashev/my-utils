#!/bin/bash -e

SELF_SCRIPT="$0"
if [ -L "$SELF_SCRIPT" ]; then
    SELF_SCRIPT=$(readlink -e $SELF_SCRIPT)
fi
DIR_HERE=$(cd $(dirname $SELF_SCRIPT) && pwd)
DIR_HOME=$(cd ~ && pwd)
DIR_FFI_SRC=$(cd "$DIR_HERE/../.." && pwd)

BUILD_ON_PLATFORM=$($DIR_FFI_SRC/config.guess)
echo "BUILD_ON_PLATFORM=$BUILD_ON_PLATFORM"
TARGET_TITLE='i686-unknown-linux-gnu'

export CC="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-gcc"
export CXX="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-g++"
export CPP="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-gcc -E"
export CXXPP="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-g++ -E"
export AR="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-ar"
export RANLIB="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-ranlib"

exec $DIR_FFI_SRC/configure --host=${TARGET_TITLE} --build=${BUILD_ON_PLATFORM} --prefix=$DIR_HERE/install
