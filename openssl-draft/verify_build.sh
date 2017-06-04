#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)

minibuild --directory $DIR_HERE/draft/0/build/crypto --model mingw-win32 --config release
minibuild --directory $DIR_HERE/draft/0/build/crypto --model mingw-win64 --config release
minibuild --directory $DIR_HERE/draft/0/build/crypto --model gcc-xt-linux-x86 --config release
minibuild --directory $DIR_HERE/draft/0/build/crypto --model gcc-xt-linux-x86_64 --config release
minibuild --directory $DIR_HERE/draft/0/build/crypto --model gcc-xt-linux-arm --config release
minibuild --directory $DIR_HERE/draft/0/build/crypto --model gcc-xt-linux-arm64 --config release

minibuild --directory $DIR_HERE/draft/0/build/ssl --model mingw-win32 --config release
minibuild --directory $DIR_HERE/draft/0/build/ssl --model mingw-win64 --config release
minibuild --directory $DIR_HERE/draft/0/build/ssl --model gcc-xt-linux-x86 --config release
minibuild --directory $DIR_HERE/draft/0/build/ssl --model gcc-xt-linux-x86_64 --config release
minibuild --directory $DIR_HERE/draft/0/build/ssl --model gcc-xt-linux-arm --config release
minibuild --directory $DIR_HERE/draft/0/build/ssl --model gcc-xt-linux-arm64 --config release

minibuild --directory $DIR_HERE/draft/0/build/apps --model mingw-win32 --config release
minibuild --directory $DIR_HERE/draft/0/build/apps --model mingw-win64 --config release
minibuild --directory $DIR_HERE/draft/0/build/apps --model gcc-xt-linux-x86 --config release
minibuild --directory $DIR_HERE/draft/0/build/apps --model gcc-xt-linux-x86_64 --config release
minibuild --directory $DIR_HERE/draft/0/build/apps --model gcc-xt-linux-arm --config release
minibuild --directory $DIR_HERE/draft/0/build/apps --model gcc-xt-linux-arm64 --config release

minibuild --directory $DIR_HERE/shlib_verify_export --model gcc-xt-linux-x86 --config release
minibuild --directory $DIR_HERE/shlib_verify_export --model gcc-xt-linux-x86_64 --config release
minibuild --directory $DIR_HERE/shlib_verify_export --model gcc-xt-linux-arm --config release
minibuild --directory $DIR_HERE/shlib_verify_export --model gcc-xt-linux-arm64 --config release


(
  $DIR_HERE/shlib_verify_export/output/exe/gcc-xt-linux-x86/release/shlib_verify_export \
      $DIR_HERE/draft/output/shared/gcc-xt-linux-x86/release/libcrypto.so \
      -
)

(
  export LD_PRELOAD=$DIR_HERE/draft/output/shared/gcc-xt-linux-x86/release/libcrypto.so
  $DIR_HERE/shlib_verify_export/output/exe/gcc-xt-linux-x86/release/shlib_verify_export \
    - \
    $DIR_HERE/draft/output/shared/gcc-xt-linux-x86/release/libssl.so
)

(
  $DIR_HERE/shlib_verify_export/output/exe/gcc-xt-linux-x86_64/release/shlib_verify_export \
      $DIR_HERE/draft/output/shared/gcc-xt-linux-x86_64/release/libcrypto.so \
      -
)

(
  export LD_PRELOAD=$DIR_HERE/draft/output/shared/gcc-xt-linux-x86_64/release/libcrypto.so
  $DIR_HERE/shlib_verify_export/output/exe/gcc-xt-linux-x86_64/release/shlib_verify_export \
    - \
    $DIR_HERE/draft/output/shared/gcc-xt-linux-x86_64/release/libssl.so
)
