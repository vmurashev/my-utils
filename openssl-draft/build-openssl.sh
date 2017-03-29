#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)
DIR_OBJ="$DIR_HERE/obj"
mkdir -p $DIR_OBJ

source "$DIR_HERE/conf.sh"

ZLIB_ARC_NAME=$(basename $ZLIB_URL)
OPENSSL_ARC_NAME=$(basename $OPENSSL_URL)

THIS_MACHINE_BUILD=$($DIR_HERE/config.guess)

if [ ! -f "$DIR_OBJ/${THIS_MACHINE_BUILD}.stamp" ]; then
    echo "THIS_MACHINE_BUILD=$THIS_MACHINE_BUILD"
    touch "$DIR_OBJ/${THIS_MACHINE_BUILD}.stamp"
fi

if [ ! -f "$DIR_OBJ/$OPENSSL_ARC_NAME" ]; then
    curl -L -o "$DIR_OBJ/$OPENSSL_ARC_NAME" $OPENSSL_URL
fi

if [ ! -f "$DIR_OBJ/$ZLIB_ARC_NAME" ]; then
    curl -L -o "$DIR_OBJ/$ZLIB_ARC_NAME" $ZLIB_URL
fi

if [ ! -d "$DIR_OBJ/zlib" ]; then
    mkdir -p "$DIR_OBJ/zlib"
    tar xf "$DIR_OBJ/$ZLIB_ARC_NAME" --strip-components=1 -C "$DIR_OBJ/zlib"
fi

# $1: ABI
build_target_openssl ()
{
    local ABI=$1
    local XT_DIR XT_PREFIX

    local OPENSSL_SRCDIR="$DIR_OBJ/openssl-src-$abi"
    rm -rf $OPENSSL_SRCDIR

    if [ ! -f "$DIR_OBJ/$OPENSSL_ARC_NAME" ]; then
        echo "ERROR: file not found: '$DIR_OBJ/$OPENSSL_ARC_NAME'"
        exit 1
    fi

    mkdir -p $OPENSSL_SRCDIR
    tar xf "$DIR_OBJ/$OPENSSL_ARC_NAME" --strip-components=1 -C $OPENSSL_SRCDIR
    echo "tarball '$DIR_OBJ/$OPENSSL_ARC_NAME' extracted in '$OPENSSL_SRCDIR'"

    case $ABI in
        mingw64)
            XT_DIR="$HOME/x-tools/x86_64-w64-mingw32/bin"
            XT_PREFIX='x86_64-w64-mingw32-'
            OPENSSL_TARGET=mingw64
            ;;
        mingw)
            XT_DIR="$HOME/x-tools/x86_64-w64-mingw32/bin"
            XT_PREFIX='x86_64-w64-mingw32-'
            OPENSSL_TARGET=mingw
            ;;
        x86_64)
            XT_DIR="$HOME/x-tools/x86_64-unknown-linux-gnu/bin"
            XT_PREFIX='x86_64-unknown-linux-gnu-'
            OPENSSL_TARGET=linux-x86_64
            ;;
        x86)
            XT_DIR="$HOME/x-tools/i686-unknown-linux-gnu/bin"
            XT_PREFIX='i686-unknown-linux-gnu-'
            OPENSSL_TARGET=linux-elf
            ;;
        arm64)
            XT_DIR="$HOME/x-tools/aarch64-unknown-linux-gnueabi/bin"
            XT_PREFIX='aarch64-unknown-linux-gnueabi-'
            OPENSSL_TARGET=linux-aarch64
            ;;
        arm)
            XT_DIR="$HOME/x-tools/arm-unknown-linux-gnueabi/bin"
            XT_PREFIX='arm-unknown-linux-gnueabi-'
            OPENSSL_TARGET=linux-armv4
            ;;
        *)
            echo "ERROR: Unknown ABI: '$ABI'" && false
            ;;
    esac

    if [ ! -d "$XT_DIR" ]; then
        echo "ERROR: Directory not found: '$XT_DIR'" && false
    fi


    local BIN_WRAP_DIR="$DIR_OBJ/bin/$ABI"
    rm -rf $BIN_WRAP_DIR
    mkdir -p "$BIN_WRAP_DIR"

    local BIN_TRACE_DIR="$DIR_OBJ/bin-trace/$ABI"
    rm -rf $BIN_TRACE_DIR
    mkdir -p "$BIN_TRACE_DIR"

    local BUILDDIR="$DIR_OBJ/build/$ABI"
    rm -rf $BUILDDIR
    mkdir -p $BUILDDIR

    (cd $XT_DIR; find . -type f) | while read F; do
        local XT_EXE_WRAPPER=$BIN_WRAP_DIR/$F
        {
            echo '#!/bin/bash -e'
            echo "XT_EXE='$XT_DIR/$F'"
            echo 'ME=$(basename $0)'
            echo 'ARGS='
            echo 'for p in "$@"; do'
            echo '    if [ -n "$p" ]; then'
            echo '        ARGS="$ARGS $p"'
            echo '    fi'
            echo 'done'
            echo "echo \"\$ARGS\ | \$ME | \$(pwd)\" >> $BIN_TRACE_DIR/build.log"
            echo 'exec $XT_EXE $ARGS'
        } > $XT_EXE_WRAPPER

        chmod +x $XT_EXE_WRAPPER
    done

    local OPENSSL_OPTIONS='shared zlib-dynamic no-gost -DOPENSSL_NO_DEPRECATED'

    local BUILD_WRAPPER=$BUILDDIR/build.sh
    {
        echo '#!/bin/bash -e'
        echo "export PATH=\"$BIN_WRAP_DIR:\$PATH\""
        echo "cd $OPENSSL_SRCDIR"
        echo "perl ./Configure --cross-compile-prefix=$XT_PREFIX $OPENSSL_OPTIONS $OPENSSL_TARGET"
        echo "cp -t include $DIR_OBJ/zlib/zlib.h"
        echo "cp -t include $DIR_OBJ/zlib/zconf.h"
        echo "make"
    } >$BUILD_WRAPPER

    chmod +x $BUILD_WRAPPER

    $BUILD_WRAPPER
}


for abi in $(echo $ABI_ALL | tr ',' ' '); do
    build_target_openssl $abi
done

echo "Done!"
