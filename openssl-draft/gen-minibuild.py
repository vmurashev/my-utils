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

SSL_STATIC_MAKE_DIR = os.path.join(DIR_OPENSSL_SUBMODULE, 'build/ssl_static')
SSL_SHARED_MAKE_DIR = os.path.join(DIR_OPENSSL_SUBMODULE, 'build/ssl')

APPS_MAKE_DIR = os.path.join(DIR_OPENSSL_SUBMODULE, 'build/apps')

CRYPTO_WELLKNOWN_DEFINES = ['L_ENDIAN', 'OPENSSL_USE_NODELETE', 'NO_WINDOWS_BRAINDEATH']
OPENSSL_USELESS_FILES_LIST = OPENSSL_USELESS_FILES.split()
OPENSSL_POSIX_FILES_LIST = OPENSSL_POSIX_FILES.split()
OPENSSL_WINDOWS_FILES_LIST = OPENSSL_WINDOWS_FILES.split()

def init():
    stamp_file = os.path.join(DIR_HERE, 'obj', 'draft-init.stamp')
    if os.path.isdir(DIR_PROJECT_ROOT):
        if os.path.isfile(stamp_file):
            return
        shutil.rmtree(DIR_PROJECT_ROOT)

    os.makedirs(DIR_OPENSSL_SUBMODULE)
    subprocess.check_call(['git', 'clone', 'https://github.com/vmurashev/openssl.git', '.'], cwd=DIR_OPENSSL_SUBMODULE)
    shutil.rmtree(os.path.join(DIR_OPENSSL_SUBMODULE, 'build'))
    shutil.rmtree(os.path.join(DIR_OPENSSL_SUBMODULE, 'include'))
    shutil.rmtree(os.path.join(DIR_OPENSSL_SUBMODULE, 'vendor'))

    os.makedirs(DIR_OPENSSL_SUBMODULE_VENDOR)
    os.makedirs(OPENSSL_HEADERS_DIR)
    subprocess.check_call(['tar', 'xf', os.path.join(DIR_HERE, 'obj', os.path.basename(OPENSSL_URL)), '--strip-components=1', '-C', DIR_OPENSSL_SUBMODULE_VENDOR])
    subprocess.check_call("find . -name '*.s' -exec rm -f {} \;", shell=True, cwd=DIR_OPENSSL_SUBMODULE_VENDOR)
    subprocess.check_call("find . -name '*.S' -exec rm -f {} \;", shell=True, cwd=DIR_OPENSSL_SUBMODULE_VENDOR)
    subprocess.check_call("find . -name '*.h.in' -exec rm -f {} \;", shell=True, cwd=DIR_OPENSSL_SUBMODULE_VENDOR)
    subprocess.check_call("find . -type f -exec chmod ugo-x {} \;", shell=True, cwd=DIR_OPENSSL_SUBMODULE_VENDOR)
    subprocess.check_call("patch -p0 -i {}".format(os.path.join(DIR_HERE, 'tweaks', 'eng_list.c.patch')), shell=True, cwd=DIR_OPENSSL_SUBMODULE_VENDOR)
    subprocess.check_call(['git', 'clone', 'https://github.com/vmurashev/zlib.git'], cwd=DIR_PROJECT_ROOT)
    shutil.copyfile(os.path.join(DIR_HERE, 'shlib_verify_export', 'minibuild.ini'), os.path.join(DIR_PROJECT_ROOT, 'minibuild.ini'))

    for twh in os.listdir(os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'include/openssl')):
        if not twh.startswith('__') and twh.endswith('.h'):
            shutil.copyfile(os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'include/openssl', twh), os.path.join(OPENSSL_HEADERS_DIR, twh))

    shutil.rmtree(os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'include/openssl'))
    shutil.rmtree(os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'ms'))
    shutil.rmtree(os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'demos'))
    shutil.rmtree(os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'fuzz'))

    for twh in os.listdir(os.path.join(DIR_HERE, 'tweaks')):
        # if twh.startswith('opensslconf') and twh.endswith('.h'):
        if twh == 'opensslconf.h':
            shutil.copyfile(os.path.join(DIR_HERE, 'tweaks', twh), os.path.join(OPENSSL_HEADERS_DIR, twh))

    shutil.copyfile(os.path.join(DIR_HERE, 'tweaks', 'bn_conf.h'), os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'crypto/include/internal', 'bn_conf.h'))
    shutil.copyfile(os.path.join(DIR_HERE, 'tweaks', 'dso_conf.h'), os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'crypto/include/internal', 'dso_conf.h'))

    with open(stamp_file, mode='w'):
        pass


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
        posix_and_win_files = []
        flist_tmp = get_ini_conf_strings(arch_map[arch], lib_ini_name, 'BUILD_LIST')
        arch_files_map[arch] = []
        for f in flist_tmp:
            if os.path.basename(f) in OPENSSL_USELESS_FILES_LIST:
                continue
            if os.path.basename(f) in OPENSSL_POSIX_FILES_LIST:
                posix_and_win_files.append(f)
                continue
            if os.path.basename(f) in OPENSSL_WINDOWS_FILES_LIST:
                posix_and_win_files.append(f)
                continue
            arch_files_map[arch].append(f)
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
        if not f.endswith('.c'):
            in_all = False
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
            if f.endswith('.c'):
                dir_name = os.path.dirname(f)
                dir_names.add(dir_name)
    if lib_make_name.startswith('crypto'):
        for f in posix_and_win_files:
            if '/' in f:
                if f.endswith('.c'):
                    dir_name = os.path.dirname(f)
                    dir_names.add(dir_name)

    if not os.path.isdir(makedir):
        os.makedirs(makedir)

    if is_shared:
        shutil.copyfile(def_file, os.path.join(makedir, os.path.basename(def_file)))
        with open(os.path.join(makedir, 'minibuild.mk'), mode='wt') as fh:
            if lib_make_name == 'crypto':
                print('#include "../crypto_static/crypto.inc"', file=fh)
            if lib_make_name == 'ssl':
                print('#include "../ssl_static/ssl.inc"', file=fh)
            print("", file=fh)
            print("module_type = 'lib-shared'", file=fh)
            print("module_name = '{}'".format(lib_make_name), file=fh)
            if lib_make_name == 'crypto':
                print("", file=fh)
                print("symbol_visibility_default = 1", file=fh)
                print("", file=fh)
                print("prebuilt_lib_list_linux = ['dl','pthread']", file=fh)
                print("prebuilt_lib_list_windows = ['crypt32', 'ws2_32', 'advapi32', 'user32']", file=fh)
                print("", file=fh)
                print("lib_list = ['${@project_root}/zlib']", file=fh)
                print("", file=fh)

            if lib_make_name == 'ssl':
                print("", file=fh)
                print("lib_list = ['../crypto']", file=fh)
                print("", file=fh)
                print("symbol_visibility_default = 1", file=fh)
                print("", file=fh)

            print("export_def_file = '{}'".format(os.path.basename(def_file)), file=fh)
            print("", file=fh)


    if is_shared:
        return
    inc_file = None
    if lib_make_name == 'crypto_static':
        inc_file = os.path.join(makedir, 'crypto.inc')
    if lib_make_name == 'ssl_static':
        inc_file = os.path.join(makedir, 'ssl.inc')

    with open(os.path.join(makedir, 'minibuild.mk'), mode='wt') as fh:
        if lib_make_name == 'crypto_static':
            print('#include "crypto.inc"', file=fh)
        if lib_make_name == 'ssl_static':
            print('#include "ssl.inc"', file=fh)
        print("", file=fh)
        print("module_type = 'lib-static'", file=fh)
        print("module_name = '{}'".format(lib_make_name), file=fh)

    with open(inc_file, mode='wt') as fh:
        print("include_dir_list = [", file=fh)
        for inc in incd:
            print("  '{}',".format(inc), file=fh)
        print("]", file=fh)
        print("", file=fh)
        print("src_search_dir_list = [", file=fh)
        for dir_name in sorted(dir_names):
            dir_name_norm = '/'.join([vendor_prefix, dir_name])
            print("  '{}',".format(dir_name_norm), file=fh)
        print("]", file=fh)
        print("", file=fh)

        if lib_make_name.startswith('crypto'):
            print("if BUILDSYS_TOOLSET_NAME == 'msvs':", file=fh)
            print("    disabled_warnings = ['4090']", file=fh)
            print("    nasm = 1", file=fh)
            print("    asm_definitions_windows_x86_64 = ['NEAR']",  file=fh)
            print("    asm_search_dir_list_windows_x86 = [ '{}/crypto/arch/msvs-win32' ]".format(vendor_prefix), file=fh)
            print("    asm_search_dir_list_windows_x86_64 = [ '{}/crypto/arch/msvs-win64' ]".format(vendor_prefix), file=fh)
            print("else:", file=fh)
            print("    asm_search_dir_list_windows_x86 = [ '{}/crypto/arch/mingw-win32' ]".format(vendor_prefix), file=fh)
            print("    asm_search_dir_list_windows_x86_64 = [ '{}/crypto/arch/mingw-win64' ]".format(vendor_prefix), file=fh)
            print("", file=fh)
            for arch in arch_list:
                if arch == 'mingw':
                    pass
                elif arch == 'mingw64':
                    pass
                else:
                    print("asm_search_dir_list_linux_{} = [ '{}/crypto/arch/linux-{}' ]".format(arch, vendor_prefix, arch), file=fh)
            if 'x86_64' in arch_list:
                    print("asm_search_dir_list_macosx = [ '{}/crypto/arch/macosx' ]".format(vendor_prefix), file=fh)
            print("", file=fh)

        if lib_make_name.startswith('crypto'):
            print("definitions_windows = ['DSO_WIN32', 'WIN32_LEAN_AND_MEAN', '_UNICODE', 'UNICODE']", file=fh)
            print("definitions_posix = ['DSO_DLFCN', 'HAVE_DLFCN_H']", file=fh)
            print("", file=fh)

        if lib_make_name.startswith('ssl'):
            print("definitions_windows = ['WIN32_LEAN_AND_MEAN', '_UNICODE', 'UNICODE']", file=fh)
            print("", file=fh)

        print("definitions = [", file=fh)

        if lib_make_name.startswith('crypto'):
            for d in CRYPTO_WELLKNOWN_DEFINES:
                print("  '{}',".format(d), file=fh)
        for d in sorted(common_defs):
            print("  '{}',".format(d), file=fh)
        print("]", file=fh)
        print("", file=fh)

        if lib_make_name.startswith('crypto'):
            for arch in arch_list:
                if arch == 'mingw':
                    print("definitions_windows_x86 = [", file=fh)
                elif arch == 'mingw64':
                    print("definitions_windows_x86_64 = [", file=fh)
                else:
                    print("definitions_linux_{} = [".format(arch), file=fh)
                for d in sorted(arch_def_map[arch]):
                    if d in common_defs:
                        continue
                    print("  '{}',".format(d), file=fh)
                print("]", file=fh)
                print("", file=fh)
            if 'x86_64' in arch_list:
                print("definitions_macosx = [", file=fh)
                for d in sorted(arch_def_map['x86_64']):
                    if d in common_defs:
                        continue
                    print("  '{}',".format(d), file=fh)
                print("]", file=fh)
                print("", file=fh)

        if lib_make_name.startswith('crypto'):
            if OPENSSL_POSIX_FILES_LIST:
                print("build_list_posix = [", file=fh)
                for f_name in sorted(OPENSSL_POSIX_FILES_LIST):
                    print("  '{}',".format(f_name), file=fh)
                print("]", file=fh)
                print("", file=fh)
            if OPENSSL_WINDOWS_FILES_LIST:
                print("build_list_windows = [", file=fh)
                for f_name in sorted(OPENSSL_WINDOWS_FILES_LIST):
                    print("  '{}',".format(f_name), file=fh)
                print("]", file=fh)
                print("", file=fh)

        print("build_list = [", file=fh)
        for f_name in sorted(common_files_names):
            print("  '{}',".format(f_name), file=fh)
        print("]", file=fh)
        print("", file=fh)

        if lib_make_name.startswith('crypto'):
            for arch in arch_list:
                arch_asm_files[arch] = []
                if arch == 'mingw':
                    print("build_spec_mingw_win32 = [", file=fh)
                elif arch == 'mingw64':
                    print("build_spec_mingw_win64 = [", file=fh)
                else:
                    print("build_list_linux_{} = [".format(arch), file=fh)
                for f in sorted(arch_files_map[arch]):
                    f_name = os.path.basename(f)
                    if f_name.endswith('.c') and f_name in common_files_names:
                        continue
                    print("  '{}',".format(f_name), file=fh)
                    if not f_name.endswith(".c"):
                        if f not in arch_asm_files[arch]:
                            arch_asm_files[arch].append(f)
                print("]", file=fh)
                print("", file=fh)
            if 'x86_64' in arch_list:
                print("build_list_macosx = [", file=fh)
                for f in sorted(arch_files_map['x86_64']):
                    f_name = os.path.basename(f)
                    if f_name.endswith('.c') and f_name in common_files_names:
                        continue
                    print("  '{}',".format(f_name), file=fh)
                print("]", file=fh)
                print("", file=fh)

            for arch in arch_list:
                if arch == 'mingw':
                    print("build_spec_msvs_win32 = [", file=fh)
                elif arch == 'mingw64':
                    print("build_spec_msvs_win64 = [", file=fh)
                else:
                    continue
                for f in sorted(arch_files_map[arch]):
                    f_name = os.path.basename(f)
                    if f_name.endswith('.c') and f_name in common_files_names:
                        continue
                    if f_name.endswith('.c'):
                        f_name_msvs = f_name
                    else:
                        f_name_msvs = os.path.splitext(f_name)[0] + '.asm'
                    print("  '{}',".format(f_name_msvs), file=fh)
                print("]", file=fh)
                print("", file=fh)

            print("if BUILDSYS_TOOLSET_NAME == 'msvs':", file=fh)
            print("    build_list_windows_x86 = build_spec_msvs_win32", file=fh)
            print("    build_list_windows_x86_64 = build_spec_msvs_win64", file=fh)
            print("else:", file=fh)
            print("    build_list_windows_x86 = build_spec_mingw_win32", file=fh)
            print("    build_list_windows_x86_64 = build_spec_mingw_win64", file=fh)

    if lib_make_name.startswith('crypto'):
        for arch in arch_list:
            if arch == 'mingw':
                af_dst_dir = os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'crypto/arch/mingw-win32')
            elif arch == 'mingw64':
                af_dst_dir = os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'crypto/arch/mingw-win64')
            else:
                af_dst_dir = os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'crypto/arch/linux-{}'.format(arch))
            if not os.path.isdir(af_dst_dir):
                os.makedirs(af_dst_dir)
            for af in arch_asm_files[arch]:
                src = os.path.normpath(os.path.join(DIR_HERE, 'obj/openssl-src-{}'.format(arch), af))
                dst = os.path.join(af_dst_dir, os.path.basename(af))
                if not os.path.isfile(dst):
                    print("Copy: {} >>> {}".format(src, dst))
                    shutil.copyfile(src, dst)

        if 'mingw' in arch_list or mingw64 in arch_list:
            # working nasm is required for correct generation asm files for MSVS
            subprocess.check_output(['nasm', '-v'])

        for arch in arch_list:
            if arch == 'mingw':
                af_dst_dir = os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'crypto/arch/msvs-win32')
            elif arch == 'mingw64':
                af_dst_dir = os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'crypto/arch/msvs-win64')
            elif arch == 'x86_64':
                af_dst_dir = os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'crypto/arch/macosx')
            else:
                continue
            if not os.path.isdir(af_dst_dir):
                os.makedirs(af_dst_dir)
            for af in arch_asm_files[arch]:
                if arch in ['mingw', 'mingw64']:
                    dst_path_autogen = os.path.join(af_dst_dir, os.path.splitext(os.path.basename(af))[0] + '.asm')
                else:
                    dst_path_autogen = os.path.join(af_dst_dir, os.path.splitext(os.path.basename(af))[0] + '.s')
                if os.path.isfile(dst_path_autogen):
                    continue
                if arch in ['mingw', 'mingw64']:
                    src_path = os.path.normpath(os.path.join(DIR_HERE, 'obj/openssl-src-{}'.format(arch), af))
                else:
                    src_path = os.path.normpath(os.path.join(DIR_HERE, 'obj/openssl-src-x86_64', af))
                perl_gen_title = os.path.splitext(os.path.basename(src_path))[0]
                while True:
                    perl_generator = os.path.join(os.path.dirname(src_path), 'asm', perl_gen_title + '.pl')
                    if not os.path.isfile(perl_generator):
                        perl_generator = os.path.join(os.path.dirname(src_path), perl_gen_title + '.pl')
                    if not os.path.isfile(perl_generator):
                        if perl_gen_title == 'sha256-x86_64':
                            perl_gen_title = 'sha512-x86_64'
                            continue
                    break
                if not os.path.isfile(perl_generator):
                    raise Exception("File not found - '{}'".format(perl_generator))

                perl_gen_env = {}
                perl_gen_env.update(os.environ)
                if arch in ['mingw', 'mingw64']:
                    perl_gen_env['ASM'] = 'nasm'
                    asm_target_model = 'nasm' if arch == 'mingw64' else 'win32n'
                else:
                    perl_gen_env['CC'] = 'cc'
                    asm_target_model = 'macosx'
                perl_gen_cmd = ['perl', perl_generator, asm_target_model]
                if arch == 'mingw':
                    perl_gen_cmd += ['-DOPENSSL_IA32_SSE2']
                perl_gen_cmd += [dst_path_autogen]

                print("::: EXEC ::: {}".format(' '.join(perl_gen_cmd)))
                subprocess.check_call(perl_gen_cmd, env=perl_gen_env)
                if not os.path.isfile(dst_path_autogen):
                    raise Exception("Generated file not found - '{}'".format(dst_path_autogen))
                print("::: Generated file ::: {}".format(dst_path_autogen))


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


def main():
    init()
    arch_map = {}
    arch_list = ABI_ALL.split(',')
    for arch in arch_list:
        playback_ini_config = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/{}/build.ini'.format(arch)))
        arch_map[arch] = load_ini_config(playback_ini_config)

    crypto_incd = [
        '../../include',
        '../../vendor/include',
        '../../vendor',
        '../../vendor/crypto/include',
        '../../vendor/crypto',
        '../../vendor/crypto/modes',
        '${@project_root}/zlib/include',
    ]

    ssl_incd = [
        '../../include',
        '../../vendor/include',
        '../../vendor',
    ]

    crypto_def_file = os.path.join(DIR_HERE, 'tweaks', 'libcrypto.def')
    ssl_def_file = os.path.join(DIR_HERE, 'tweaks', 'libssl.def')

    gen_makefile_for_lib('crypto', 'crypto_static', '../../vendor', crypto_incd, CRYPTO_STATIC_MAKE_DIR, arch_map)
    gen_makefile_for_lib('crypto', 'crypto', '../../vendor', crypto_incd, CRYPTO_SHARED_MAKE_DIR, arch_map, crypto_def_file)

    gen_makefile_for_lib('ssl', 'ssl_static', '../../vendor', ssl_incd, SSL_STATIC_MAKE_DIR, arch_map)
    gen_makefile_for_lib('ssl', 'ssl', '../../vendor', ssl_incd, SSL_SHARED_MAKE_DIR, arch_map, ssl_def_file)

    if not os.path.isdir(APPS_MAKE_DIR):
        os.makedirs(APPS_MAKE_DIR)
    shutil.copyfile(os.path.join(DIR_HERE, 'apps', 'minibuild.mk'), os.path.join(APPS_MAKE_DIR, 'minibuild.mk'))


if __name__ == '__main__':
    main()
    print('Generated!')
