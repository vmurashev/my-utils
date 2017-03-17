#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)
DIR_OBJ="$DIR_HERE/obj"
mkdir -p $DIR_OBJ

source "$DIR_HERE/conf.sh"

OPENSSL_ARC_NAME=$(basename $OPENSSL_URL)

THIS_MACHINE_BUILD=$($DIR_HERE/config.guess)

if [ ! -f "$DIR_OBJ/${THIS_MACHINE_BUILD}.stamp" ]; then
    echo "THIS_MACHINE_BUILD=$THIS_MACHINE_BUILD"
    touch "$DIR_OBJ/${THIS_MACHINE_BUILD}.stamp"
fi

if [ ! -f "$DIR_OBJ/$OPENSSL_ARC_NAME" ]; then
    curl -L -o "$DIR_OBJ/$OPENSSL_ARC_NAME" $OPENSSL_URL
fi


OPENSSL_SRCDIR="$DIR_OBJ/openssl-src-defgen"
rm -rf $OPENSSL_SRCDIR

if [ ! -f "$DIR_OBJ/$OPENSSL_ARC_NAME" ]; then
    echo "ERROR: file not found: '$DIR_OBJ/$OPENSSL_ARC_NAME'"
    exit 1
fi

mkdir -p $OPENSSL_SRCDIR
tar xf "$DIR_OBJ/$OPENSSL_ARC_NAME" --strip-components=1 -C $OPENSSL_SRCDIR
echo "tarball '$DIR_OBJ/$OPENSSL_ARC_NAME' extracted in '$OPENSSL_SRCDIR'"

OPENSSL_GEN_EXPORT_OPTIONS="enable-static-engine"

CRYPTO_DEF="$DIR_HERE/tweaks/libcrypto.orig.def"
CRYPTO_DEF_OUTPUT="$DIR_HERE/tweaks/libcrypto.def"
CRYPTO_TEST_EXPORT_H="$DIR_HERE/shlib_verify_export/crypto_export_table.h"

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

if [ -f "SSL_TEST_EXPORT_H" ]; then
    echo "Genarated: $SSL_TEST_EXPORT_H"
fi

echo "Done!"
