#!/bin/bash -e
set -e

DIR_HERE=$(cd $(dirname $0) && pwd)

rm -rf "$DIR_HERE/obj"
rm -rf "$DIR_HERE/draft"
rm -rf "$DIR_HERE/shlib_verify_export/output"
rm -f "$DIR_HERE/shlib_verify_export/crypto_export_table.h"
rm -f "$DIR_HERE/shlib_verify_export/ssl_export_table.h"

$DIR_HERE/build-openssl.sh
$DIR_HERE/build-playback.py
$DIR_HERE/gen-minibuild.py
$DIR_HERE/verify_build.sh
$DIR_HERE/sanitize.py -f
rm -rf $DIR_HERE/draft/output
$DIR_HERE/verify_build.sh
