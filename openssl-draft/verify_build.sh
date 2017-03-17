#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)

minibuild --directory $DIR_HERE/draft/0/build/crypto --model gcc-xt-linux-x86 --config release
minibuild --directory $DIR_HERE/draft/0/build/crypto --model gcc-xt-linux-x86_64 --config release

minibuild --directory $DIR_HERE/shlib_verify_export --model gcc-xt-linux-x86 --config release
minibuild --directory $DIR_HERE/shlib_verify_export --model gcc-xt-linux-x86_64 --config release

set +e
$DIR_HERE/shlib_verify_export/output/exe/gcc-xt-linux-x86/release/shlib_verify_export $DIR_HERE/draft/output/shared/gcc-xt-linux-x86/release/libcrypto.so -
$DIR_HERE/shlib_verify_export/output/exe/gcc-xt-linux-x86_64/release/shlib_verify_export $DIR_HERE/draft/output/shared/gcc-xt-linux-x86_64/release/libcrypto.so -