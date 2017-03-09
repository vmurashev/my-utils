#!/usr/bin/env python3

import sys
import configparser
import os
import os.path
import shutil


DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

PLAYBACK_INI_x86 = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/x86/build.ini'))
PLAYBACK_INI_x86_64 = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/x86_64/build.ini'))

CRYPTO_STATIC_MAKE_DIR = '/home/vet/me/openssl/0/build/crypto_static'
OPENSSL_HEADERS_DIR = '/home/vet/me/openssl/0/include/openssl'


def load_ini_config(path):
    config = configparser.RawConfigParser()
    config.read(path)
    return config


def get_ini_conf_boolean0(config, section, option, default=None):
    if not config.has_option(section, option):
        return default
    return config.getboolean(section, option)


def get_ini_conf_string1(config, section, option):
    return config.get(section, option).strip()


def get_ini_conf_string0(config, section, option, default=None):
    if not config.has_option(section, option):
        return default
    return get_ini_conf_string1(config, section, option)


def get_ini_conf_strings(config, section, option):
    return config.get(section, option).split()


def get_ini_conf_strings_optional(config, section, option):
    if not config.has_option(section, option):
        return []
    return get_ini_conf_strings(config, section, option)


def gen_makefile_for_static_lib(lib_ini_name, lib_make_name, vendor_prefix, incd, makedir, arch_map):
    arch_list = sorted(arch_map.keys())

    all_files = set()
    arch_specific_files = set()
    arch_files_map = {}

    all_defs = set()
    arch_specific_defs = set()
    arch_def_map = {}

    for arch in arch_list:
        arch_files_map[arch] = get_ini_conf_strings(arch_map[arch], lib_ini_name, 'BUILD_LIST')
        arch_def_map[arch] = get_ini_conf_strings(arch_map[arch], lib_ini_name, 'DEF_LIST')
        for f in arch_files_map[arch]:
            all_files.add(f)
        for d in arch_def_map[arch]:
            all_defs.add(d)

    for f in all_files:
        in_all = True
        for arch in arch_list:
            if f not in arch_files_map[arch]:
                in_all = False
                break
        if not in_all:
            arch_specific_files.add(f)

    for d in all_defs:
        in_all = True
        for arch in arch_list:
            if d not in arch_def_map[arch]:
                in_all = False
                break
        if not in_all:
            arch_specific_defs.add(d)

    common_files_names = []
    for f in all_files:
        if f in arch_specific_files:
            continue
        common_files_names.append(os.path.basename(f))

    common_defs = []
    for d in all_defs:
        if d in arch_specific_defs:
            continue
        common_defs.append(d)

    dir_names = set()
    for f in all_files:
        if '/' in f:
            dir_name = os.path.dirname(f)
            dir_names.add(dir_name)


    with open(os.path.join(makedir, 'minibuild.mk'), mode='wt') as fh:
        print("module_type = 'lib-static'", file=fh)
        print("module_name = '{}'".format(lib_make_name), file=fh)

        print("", file=fh)
        print("src_search_dir_list = [", file=fh)
        for dir_name in sorted(dir_names):
            dir_name_norm = '/'.join([vendor_prefix, dir_name])
            print("  '{}',".format(dir_name_norm), file=fh)
        print("]", file=fh)
        print("", file=fh)

        print("", file=fh)
        print("definitions = [", file=fh)
        for d in sorted(common_defs):
            print("  '{}',".format(d), file=fh)
        print("]", file=fh)
        print("", file=fh)

        print("", file=fh)
        print("include_dir_list = [", file=fh)
        for inc in incd:
            print("  '{}',".format(inc), file=fh)
        print("]", file=fh)
        print("", file=fh)

        for arch in arch_list:
            print("definitions_{} = [".format(arch), file=fh)
            for d in sorted(arch_def_map[arch]):
                if d in common_defs:
                    continue
                print("  '{}',".format(d), file=fh)
            print("]", file=fh)
            print("", file=fh)

        print("", file=fh)
        print("build_list = [", file=fh)
        for f in sorted(common_files_names):
            print("  '{}',".format(f), file=fh)
        print("]", file=fh)
        print("", file=fh)

        for arch in arch_list:
            print("build_list_{} = [".format(arch), file=fh)
            for f in sorted(arch_files_map[arch]):
                f_name = os.path.basename(f)
                if f_name in common_files_names:
                    continue
                print("  '{}',".format(f_name), file=fh)
            print("]", file=fh)
            print("", file=fh)


def cleanup_dir(dir_name):
    if os.path.exists(dir_name):
        fsitems = os.listdir(dir_name)
        for fsitem in fsitems:
            path = os.path.join(dir_name, fsitem)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    else:
        os.makedirs(dir_name)

def gen_headers(h_dir, inc_prefix, arch_map):
    cleanup_dir(h_dir)
    all_headers = {}
    arch_list = sorted(arch_map.keys())
    for arch in arch_list:
        options = arch_map[arch].options('HEADERS')
        for h_name in options:
            h_ref = get_ini_conf_string1(arch_map[arch], 'HEADERS', h_name)
            all_headers[h_name] = h_ref
            for h_name, h_ref in all_headers.items():
                h_path = os.path.join(h_dir, h_name)
                with open(h_path, mode='wt') as fh:
                    print('#include "{}/{}"'.format(inc_prefix, h_ref), file=fh, end='')


def main():
    x86_cfg = load_ini_config(PLAYBACK_INI_x86)
    x86_64_cfg = load_ini_config(PLAYBACK_INI_x86_64)
    arch_map = {}
    arch_map['x86'] = x86_cfg
    arch_map['x86_64'] = x86_64_cfg

    gen_headers(OPENSSL_HEADERS_DIR, '../../vendor', arch_map)

    crypto_incd = ['../../include', '../../vendor', '../../vendor/crypto']
    gen_makefile_for_static_lib('crypto', 'crypto_static', '../../vendor', crypto_incd, CRYPTO_STATIC_MAKE_DIR, arch_map)



if __name__ == '__main__':
    main()
    print('Generated!')
