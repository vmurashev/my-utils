#!/usr/bin/env python3

import sys
import configparser
import os
import os.path
import shutil
import subprocess

DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

with open(os.path.join(DIR_HERE, 'conf.sh'), mode='rt') as conf_sh:
    exec(compile(conf_sh.read(), os.path.join(DIR_HERE, 'conf.sh'), 'exec'))

DIR_PROJECT_ROOT = os.path.normpath(os.path.join(DIR_HERE, 'draft'))
DIR_OPENSSL_SUBMODULE = os.path.join(DIR_PROJECT_ROOT, '0')
DIR_OPENSSL_SUBMODULE_VENDOR = os.path.join(DIR_OPENSSL_SUBMODULE, 'vendor')

OPENSSL_HEADERS_DIR = os.path.join(DIR_OPENSSL_SUBMODULE, 'include/openssl')

CRYPTO_STATIC_MAKE_DIR = os.path.join(DIR_OPENSSL_SUBMODULE, 'build/crypto_static')
CRYPTO_SHARED_MAKE_DIR = os.path.join(DIR_OPENSSL_SUBMODULE, 'build/crypto')


FNAMES_TO_SKIP = ['cversion.c']

if not os.path.isfile(os.path.join(DIR_PROJECT_ROOT, 'minibuild.ini')):
    if not os.path.isdir(DIR_OPENSSL_SUBMODULE_VENDOR):
        os.makedirs(DIR_OPENSSL_SUBMODULE_VENDOR)
    subprocess.check_call(['tar', 'xf', os.path.join(DIR_HERE, 'obj', os.path.basename(OPENSSL_URL)), '--strip-components=1', '-C', DIR_OPENSSL_SUBMODULE_VENDOR])
    subprocess.check_call(['git', 'clone', 'https://github.com/vmurashev/zlib.git'], cwd=DIR_PROJECT_ROOT)
    shutil.copyfile(os.path.join(DIR_HERE, 'shlib_verify_export', 'minibuild.ini'), os.path.join(DIR_PROJECT_ROOT, 'minibuild.ini'))


def load_ini_config(path):
    if not os.path.isfile(path):
        raise Exception("File not found: '{}'".format(path))
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


ASM_COPIED = 0

def gen_makefile_for_lib(lib_ini_name, lib_make_name, vendor_prefix, incd, makedir, arch_map, def_file=None):
    is_shared = def_file is not None
    arch_list = sorted(arch_map.keys())

    all_files = set()
    arch_specific_files = set()
    arch_files_map = {}
    arch_asm_files = {}

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

    if not os.path.isdir(makedir):
        os.makedirs(makedir)

    with open(os.path.join(makedir, 'minibuild.mk'), mode='wt') as fh:
        if is_shared:
            print("module_type = 'lib-shared'", file=fh)
        else:
            print("module_type = 'lib-static'", file=fh)
        print("module_name = '{}'".format(lib_make_name), file=fh)

        if def_file is not None:
            print("", file=fh)
            print("exports_def_file = '{}'".format(os.path.basename(def_file)), file=fh)
            print("", file=fh)

        if lib_make_name == 'crypto':
            print("symbol_visibility_default = 1", file=fh)
            print("", file=fh)
            print("prebuilt_lib_list_linux = ['dl']", file=fh)
            print("", file=fh)
            print("lib_list = ['../../../zlib']", file=fh)
            print("", file=fh)

        print("", file=fh)
        print("src_search_dir_list = [", file=fh)
        for dir_name in sorted(dir_names):
            dir_name_norm = '/'.join([vendor_prefix, dir_name])
            print("  '{}',".format(dir_name_norm), file=fh)
        if lib_make_name.startswith('crypto'):
            for dir_name in ['../../vendor/engines']:
                print("  '{}',".format(dir_name), file=fh)

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
            print("definitions_linux_{} = [".format(arch), file=fh)
            for d in sorted(arch_def_map[arch]):
                if d in common_defs:
                    continue
                print("  '{}',".format(d), file=fh)
            print("]", file=fh)
            print("", file=fh)

        print("", file=fh)
        print("build_list = [", file=fh)
        for f_name in sorted(common_files_names):
            if f_name in FNAMES_TO_SKIP:
                continue
            print("  '{}',".format(f_name), file=fh)

        if lib_make_name.startswith('crypto'):
            for f_name in ['e_4758cca.c', 'e_aep.c', 'e_atalla.c', 'e_cswift.c', 'e_chil.c', 'e_nuron.c', 'e_sureware.c', 'e_ubsec.c', 'e_padlock.c' ]:
                print("  '{}',".format(f_name), file=fh)

        print("]", file=fh)
        print("", file=fh)

        for arch in arch_list:
            arch_asm_files[arch] = []
            print("build_list_linux_{} = [".format(arch), file=fh)
            for f in sorted(arch_files_map[arch]):
                f_name = os.path.basename(f)
                if f_name in FNAMES_TO_SKIP:
                    continue
                if f_name in common_files_names:
                    continue
                print("  '{}',".format(f_name), file=fh)
                if not f_name.endswith(".c"):
                    if f not in arch_asm_files[arch]:
                        arch_asm_files[arch].append(f)
            print("]", file=fh)
            print("", file=fh)


    if def_file is not None:
        shutil.copyfile(def_file, os.path.join(makedir, os.path.basename(def_file)))

    global ASM_COPIED
    if not ASM_COPIED:
        ASM_COPIED = 1
        for arch in arch_list:
            for af in arch_asm_files[arch]:
                src = os.path.normpath(os.path.join(DIR_HERE, 'obj/openssl-src-{}'.format(arch), af))
                dst = os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, af)
                print("Copy: {} >>> {}".format(src, dst))
                shutil.copyfile(src, dst)


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

    shutil.copyfile(os.path.join(DIR_HERE, 'tweaks', 'opensslconf.h'), os.path.join(h_dir, 'opensslconf.h'))


def main():
    arch_map = {}
    arch_list = ABI_ALL.split(',')
    for arch in arch_list:
        playback_ini_config = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/{}/build.ini'.format(arch)))
        arch_map[arch] = load_ini_config(playback_ini_config)

    gen_headers(OPENSSL_HEADERS_DIR, '../../vendor', arch_map)

    crypto_incd = [
        '../../include',
        '../../../zlib/include',
        '../../vendor',
        '../../vendor/crypto',
        '../../vendor/crypto/aes',
        '../../vendor/crypto/asn1',
        '../../vendor/crypto/evp',
        '../../vendor/crypto/modes',
    ]

    crypto_def_file = os.path.join(DIR_HERE, 'tweaks', 'libcrypto.def')

    gen_makefile_for_lib('crypto', 'crypto_static', '../../vendor', crypto_incd, CRYPTO_STATIC_MAKE_DIR, arch_map)
    gen_makefile_for_lib('crypto', 'crypto', '../../vendor', crypto_incd, CRYPTO_SHARED_MAKE_DIR, arch_map, crypto_def_file)



if __name__ == '__main__':
    main()
    print('Generated!')
