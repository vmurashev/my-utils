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
TARGET_TITLE='x86_64-w64-mingw32'

export CC="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-gcc -m32"
export CXX="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-g++ -m32"
export CPP="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-gcc -m32 -E"
export CXXPP="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-g++ -m32 -E"
export AR="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-ar"
export RANLIB="$DIR_HOME/x-tools/${TARGET_TITLE}/bin/${TARGET_TITLE}-ranlib"

exec $DIR_FFI_SRC/configure --host=${TARGET_TITLE} --build=${BUILD_ON_PLATFORM} --prefix=$DIR_HERE/install
