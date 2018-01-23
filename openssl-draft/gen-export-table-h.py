#!/usr/bin/env python3

from __future__ import print_function
import sys
import argparse
import os.path

DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

with open(os.path.join(DIR_HERE, 'conf.sh'), mode='rt') as conf_sh:
    exec(compile(conf_sh.read(), os.path.join(DIR_HERE, 'conf.sh'), 'exec'))

EXPORTS_DISABLED = OPENSSL_EXPORTS_DISABLED.split()
EXPORTS_WINAPI_SPECIFIC = OPENSSL_EXPORTS_CRYPTO_WINAPI_ONLY.split()


def load_export_list_from_def_file(lib_name, def_file):
    export_section_found = False
    export_list = []
    export_lines = []
    lines = [line.rstrip('\r\n') for line in open(def_file)]
    line_number = 0
    inside_export = False
    for line in lines:
        line_number += 1
        text = line.lstrip()
        if not text or text[0] == ';':
            continue
        tokens = text.split()
        line_is_keyword = False
        if len(line) == len(text):
            line_is_keyword = True
        if line_is_keyword:
            if inside_export:
                inside_export = False
            elif len(tokens) == 1 and tokens[0] == 'EXPORTS':
                if export_section_found:
                    raise Exception("'EXPORTS' section found more then once inside DEF file: '{}'".format(def_file))
                export_section_found = True
                inside_export = True
            continue
        if inside_export:
            if tokens:
                symbol = tokens[0]
                if symbol not in EXPORTS_DISABLED:
                    export_list.append(symbol)
                    export_lines.append(line)
    if not export_section_found:
        raise Exception("'EXPORTS' section not found inside DEF file: '{}'".format(def_file))
    if not export_list:
        raise Exception("Cannot load symbols information from 'EXPORTS' section inside DEF file: '{}'".format(def_file))
    return export_list, export_lines


def gen_export_table_h(lib_name, def_file, def_output, h_output):
    export_list, export_lines = load_export_list_from_def_file(lib_name, def_file)

    with open(h_output, mode='wt') as fh:
        print('#pragma once', file=fh)
        print('', file=fh)
        print('#include <stddef.h>', file=fh)
        print('', file=fh)
        print("static const char* {}_EXPORT_TABLE[] = {{".format(lib_name.upper()), file=fh)
        for func_name in export_list:
            winapi_wrap = False
            if func_name in EXPORTS_WINAPI_SPECIFIC:
                winapi_wrap = True
            if winapi_wrap:
                print('#ifdef _WIN32', file=fh)
            print('  "{}",'.format(func_name), file=fh)
            if winapi_wrap:
                print('#endif', file=fh)
        print('  NULL', file=fh)
        print("};", file=fh)

    if def_output is not None:
        with open(def_output, mode='wt') as fh:
            print('LIBRARY {}'.format(lib_name), file=fh)
            print('', file=fh)
            print('EXPORTS', file=fh)
            for line in export_lines:
                print(line, file=fh)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        h_crypto = os.path.normpath(os.path.join(DIR_HERE, "shlib_verify_export/crypto_export_table.h"))
        def_crypto = os.path.normpath(os.path.join(DIR_HERE, "draft/openssl/build/crypto/libcrypto.def"))
        h_ssl = os.path.normpath(os.path.join(DIR_HERE, "shlib_verify_export/ssl_export_table.h"))
        def_ssl = os.path.normpath(os.path.join(DIR_HERE, "draft/openssl/build/ssl/libssl.def"))
        gen_export_table_h('crypto', def_crypto, None, h_crypto)
        gen_export_table_h('ssl', def_ssl, None, h_ssl)

    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('--lib-name', nargs=1, choices=['crypto', 'ssl'], required=True)
        parser.add_argument('--def-file', nargs=1, required=True)
        parser.add_argument('--def-output', nargs=1, required=True)
        parser.add_argument('--h-output', nargs=1, required=True)
        args = parser.parse_args()
        gen_export_table_h(args.lib_name[0], args.def_file[0], args.def_output[0], args.h_output[0])
