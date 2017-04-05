#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)
DIR_OBJ="$DIR_HERE/obj"
mkdir -p $DIR_OBJ

source "$DIR_HERE/conf.sh"

ZLIB_ARC_NAME=$(basename $ZLIB_URL)
OPENSSL_ARC_NAME=$(basename $OPENSSL_URL)

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

# $1: ABI
copy_config_headers ()
{
    local ABI=$1
    local DST_SUFIX=$ABI
    local OPENSSL_SRCDIR="$DIR_OBJ/openssl-src-$abi"

    case $ABI in
        mingw)
            DST_SUFIX=mingw32
            ;;
    esac

    cp -T "$OPENSSL_SRCDIR/include/openssl/opensslconf.h" "$DIR_HERE/tweaks/opensslconf_${DST_SUFIX}.h"
}

gen_def_files ()
{
    local OPENSSL_SRCDIR="$DIR_OBJ/openssl-src-mingw64"

    local CRYPTO_DEF="$DIR_HERE/tweaks/libcrypto.orig.def"
    local CRYPTO_DEF_OUTPUT="$DIR_HERE/tweaks/libcrypto.def"
    local CRYPTO_TEST_EXPORT_H="$DIR_HERE/shlib_verify_export/crypto_export_table.h"

    SSL_DEF="$DIR_HERE/tweaks/libssl.orig.def"
    SSL_DEF_OUTPUT="$DIR_HERE/tweaks/libssl.def"
    SSL_TEST_EXPORT_H="$DIR_HERE/shlib_verify_export/ssl_export_table.h"

    rm -rf "$CRYPTO_DEF" "$CRYPTO_DEF_OUTPUT" "$CRYPTO_TEST_EXPORT_H"
    rm -rf "$SSL_DEF" "$SSL_DEF_OUTPUT" "$SSL_TEST_EXPORT_H"

    (
        cd $OPENSSL_SRCDIR
        perl util/mkdef.pl crypto $OPENSSL_GEN_EXPORT_OPTIONS > $CRYPTO_DEF
        perl util/mkdef.pl ssl $OPENSSL_GEN_EXPORT_OPTIONS > $SSL_DEF
    )

    $DIR_HERE/gen-export-table-h.py --lib-name crypto --def-file "$CRYPTO_DEF" --def-output "$CRYPTO_DEF_OUTPUT" --h-output "$CRYPTO_TEST_EXPORT_H"
    $DIR_HERE/gen-export-table-h.py --lib-name ssl    --def-file "$SSL_DEF"    --def-output "$SSL_DEF_OUTPUT"    --h-output "$SSL_TEST_EXPORT_H"

    if [ -f "$CRYPTO_DEF" ]; then
        echo "Genarated: $CRYPTO_DEF"
    fi

    if [ -f "$CRYPTO_DEF_OUTPUT" ]; then
        echo "Genarated: $CRYPTO_DEF_OUTPUT"
    fi

    if [ -f "$CRYPTO_TEST_EXPORT_H" ]; then
        echo "Genarated: $CRYPTO_TEST_EXPORT_H"
    fi

    if [ -f "$SSL_DEF" ]; then
        echo "Genarated: $SSL_DEF"
    fi

    if [ -f "$SSL_DEF_OUTPUT" ]; then
        echo "Genarated: $SSL_DEF_OUTPUT"
    fi

    if [ -f "$SSL_TEST_EXPORT_H" ]; then
        echo "Genarated: $SSL_TEST_EXPORT_H"
    fi
}

GEN_DEF_FILES='no'
for abi in $(echo $ABI_ALL | tr ',' ' '); do
    build_target_openssl $abi
    copy_config_headers $abi
    if [ "$abi" = "mingw64" ]; then
        GEN_DEF_FILES='yes'
    fi
done

if [ "$GEN_DEF_FILES" = "yes" ]; then
    gen_def_files
fi

echo "Done!"
