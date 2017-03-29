#!/usr/bin/env python3

import argparse
import os.path

DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

with open(os.path.join(DIR_HERE, 'conf.sh'), mode='rt') as conf_sh:
    exec(compile(conf_sh.read(), os.path.join(DIR_HERE, 'conf.sh'), 'exec'))

CRYPTO_DEPRECATED_API = [
    'BN_generate_prime',
    'BN_is_prime',
    'CRYPTO_get_id_callback',
    'CRYPTO_set_id_callback',
    'CRYPTO_thread_id',
    'DH_generate_parameters',
    'DSA_generate_parameters',
    'ERR_remove_state',
    'RSA_generate_key',
    'BN_CTX_init',
    'BN_set_params',
    'BN_get_params',
    'BN_is_prime_fasttest',
    'bn_dup_expand',
    'BN_BLINDING_get_thread_id',
    'BN_BLINDING_set_thread_id',
]

CRYPTO_DISABLED_API = [
    'ENGINE_load_gost',
    'OPENSSL_cpuid_setup',
]

CRYPTO_WINONLY_API = EXPORTS_CRYPTO_WINAPI_ONLY.split(',')

CRYPTO_DEPRECATED_API = []
CRYPTO_DISABLED_API = []
CRYPTO_WINONLY_API = []

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
            if tokens and not tokens[0].startswith('@'):
                symbol = tokens[0]
                symbol_enabled = True
                if lib_name == 'crypto':
                    if symbol in CRYPTO_DEPRECATED_API or symbol in CRYPTO_DISABLED_API:
                        symbol_enabled = False
                if symbol_enabled:
                    if symbol not in CRYPTO_WINONLY_API:
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
            print('  "{}",'.format(func_name), file=fh)
        print('  NULL', file=fh)
        print("};", file=fh)

    with open(def_output, mode='wt') as fh:
        print('LIBRARY {}'.format(lib_name), file=fh)
        print('', file=fh)
        print('EXPORTS', file=fh)
        for line in export_lines:
            print(line, file=fh)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lib-name', nargs=1, choices=['crypto', 'ssl'], required=True)
    parser.add_argument('--def-file', nargs=1, required=True)
    parser.add_argument('--def-output', nargs=1, required=True)
    parser.add_argument('--h-output', nargs=1, required=True)
    args = parser.parse_args()
    gen_export_table_h(args.lib_name[0], args.def_file[0], args.def_output[0], args.h_output[0])
