#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)
DIR_OBJ="$DIR_HERE/obj"
mkdir -p $DIR_OBJ

source "$DIR_HERE/conf.sh"

OPENSSL_ARC_NAME=$(basename $OPENSSL_URL)

if [ ! -f "$DIR_OBJ/$OPENSSL_ARC_NAME" ]; then
    curl -L -o "$DIR_OBJ/$OPENSSL_ARC_NAME" $OPENSSL_URL
fi

build_openssl_macosx ()
{
    local OPENSSL_TARGET=darwin64-x86_64-cc
    local OPENSSL_SRCDIR="$DIR_OBJ/openssl-src-macosx"
    rm -rf $OPENSSL_SRCDIR

    if [ ! -f "$DIR_OBJ/$OPENSSL_ARC_NAME" ]; then
        echo "ERROR: file not found: '$DIR_OBJ/$OPENSSL_ARC_NAME'"
        exit 1
    fi

    mkdir -p $OPENSSL_SRCDIR
    tar xf "$DIR_OBJ/$OPENSSL_ARC_NAME" --strip-components=1 -C $OPENSSL_SRCDIR
    echo "tarball '$DIR_OBJ/$OPENSSL_ARC_NAME' extracted in '$OPENSSL_SRCDIR'"


    local BIN_WRAP_DIR="$DIR_OBJ/bin/macosx"
    rm -rf $BIN_WRAP_DIR
    mkdir -p "$BIN_WRAP_DIR"

    local BIN_TRACE_DIR="$DIR_OBJ/bin-trace/macosx"
    rm -rf $BIN_TRACE_DIR
    mkdir -p "$BIN_TRACE_DIR"

    local BUILDDIR="$DIR_OBJ/build/macosx"
    rm -rf $BUILDDIR
    mkdir -p $BUILDDIR

    # cc
    local CC_EXE=$(which cc)
    {
        echo '#!/bin/bash -ex'
        echo "XT_EXE=$CC_EXE"
        echo 'ME=$(basename $0)'
        echo 'ARGS='
        echo 'for p in "$@"; do'
        echo '    if [ -n "$p" ]; then'
        echo '        ARGS="$ARGS $p"'
        echo '    fi'
        echo 'done'
        echo "echo \"\$ARGS | \$ME | \$(pwd)\" >> $BIN_TRACE_DIR/build.log"
        echo 'exec $XT_EXE $ARGS'
    } > "$BIN_WRAP_DIR/cc"
    chmod +x "$BIN_WRAP_DIR/cc"

    # ar
    local AR_EXE=$(which ar)
    {
        echo '#!/bin/bash -e'
        echo "XT_EXE=$AR_EXE"
        echo 'ME=$(basename $0)'
        echo 'ARGS='
        echo 'for p in "$@"; do'
        echo '    if [ -n "$p" ]; then'
        echo '        ARGS="$ARGS $p"'
        echo '    fi'
        echo 'done'
        echo "echo \"\$ARGS | \$ME | \$(pwd)\" >> $BIN_TRACE_DIR/build.log"
        echo 'exec $XT_EXE $ARGS'
    } > "$BIN_WRAP_DIR/ar"
    chmod +x "$BIN_WRAP_DIR/ar"

    # ranlib
    local RANLIB_EXE=$(which ranlib)
    {
        echo '#!/bin/bash -e'
        echo "XT_EXE=$RANLIB_EXE"
        echo 'ME=$(basename $0)'
        echo 'ARGS='
        echo 'for p in "$@"; do'
        echo '    if [ -n "$p" ]; then'
        echo '        ARGS="$ARGS $p"'
        echo '    fi'
        echo 'done'
        echo "echo \"\$ARGS | \$ME | \$(pwd)\" >> $BIN_TRACE_DIR/build.log"
        echo 'exec $XT_EXE $ARGS'
    } > "$BIN_WRAP_DIR/ranlib"
    chmod +x "$BIN_WRAP_DIR/ranlib"

    local BUILD_WRAPPER=$BUILDDIR/build.sh
    {
        echo '#!/bin/bash -e'
        echo "export PATH=\"$BIN_WRAP_DIR:\$PATH\""
        echo "cd $OPENSSL_SRCDIR"
        echo "perl ./Configure $OPENSSL_OPTIONS $OPENSSL_TARGET"
        echo "make"
    } >$BUILD_WRAPPER

    chmod +x $BUILD_WRAPPER

    $BUILD_WRAPPER
    cp "$OPENSSL_SRCDIR/include/openssl/opensslconf.h" "$DIR_HERE/tweaks/opensslconf_macosx.h"

}

build_openssl_macosx

echo "Done!"
