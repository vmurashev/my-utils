#!/bin/bash -e

DIR_HERE=$(cd $(dirname $0) && pwd)

minibuild --directory $DIR_HERE/draft/0/build/crypto --model clang-macosx-x86_64 --config release
minibuild --directory $DIR_HERE/draft/0/build/ssl    --model clang-macosx-x86_64 --config release
minibuild --directory $DIR_HERE/draft/0/build/apps   --model clang-macosx-x86_64 --config release
minibuild --directory $DIR_HERE/shlib_verify_export  --model clang-macosx-x86_64 --config release

(
  $DIR_HERE/shlib_verify_export/output/exe/clang-macosx-x86_64/release/shlib_verify_export \
      $DIR_HERE/draft/output/shared/clang-macosx-x86_64/release/libcrypto.so \
      -
)

(
  export DYLD_LIBRARY_PATH=$DIR_HERE/draft/output/shared/clang-macosx-x86_64/release
  $DIR_HERE/shlib_verify_export/output/exe/clang-macosx-x86_64/release/shlib_verify_export \
    - \
    $DIR_HERE/draft/output/shared/clang-macosx-x86_64/release/libssl.so
)
