#!/usr/bin/env python3

import os.path

DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

with open(os.path.join(DIR_HERE, 'conf.sh'), mode='rt') as conf_sh:
    exec(compile(conf_sh.read(), os.path.join(DIR_HERE, 'conf.sh'), 'exec'))


KNOWN_TOOLS = ['gcc', 'ar', 'ranlib', 'windres']

DEFINES_DISABLED = [
    'ZLIB_SHARED',
    'L_ENDIAN',
    'OPENSSL_NO_DSO',
    'OPENSSL_USE_NODELETE',
    'DSO_WIN32',
    'DSO_DLFCN',
    'HAVE_DLFCN_H',
    'OPENSSL_USE_APPLINK',
    'WIN32_LEAN_AND_MEAN',
    '_UNICODE',
    'UNICODE',
    '_MT',
    '_WINDLL',
]

FILES_DISABLED = ['dso_dl.c', 'dso_openssl.c', 'applink.c', 'uplink.c']

def norm_build_dir(arg):
    bits = []
    got = False
    for v in arg.strip().split('/'):
        if got:
            bits.append(v)
        elif v.startswith('openssl-src-'):
            got = True
    return '/'.join(bits)


def is_define_enabled(d):
    if d in DEFINES_DISABLED:
        return False
    if d.startswith('ENGINESDIR'):
        return False
    return True


def parse_build_log(input_log, output_ini):
    SRC_MAP = {}
    SRC_DEF_MAP = {}
    LIBS_MAP = {}
    LIBS_DEF = {}

    crypto_linked = False
    ssl_linked = False

    lines = [line.rstrip('\r\n') for line in open(input_log)]
    line_number = 0
    for line in lines:
        if crypto_linked and ssl_linked:
            break
        line_number += 1
        bits = line.split('|')
        if len(bits) != 3:
            print("BAD LINE@{}: ---{}---".format(line_number, line))
            raise Exception("BAD LINE")

        cmdline = bits[0].strip().rstrip('\\').split()
        if len(cmdline) == 1 and cmdline[0] == '--version':
            continue
        if len(cmdline) == 3 and cmdline[0] == '-E' and cmdline[1] == '-P' and cmdline[2] == '-':
            continue
        tool = bits[1].rsplit('-',1)[1].strip()
        exec_dir = norm_build_dir(bits[2])

        if tool not in KNOWN_TOOLS:
            print("UNKNOWN TOOL '{}' AT LINE@{}: ---{}---".format(tool, line_number, line))
            raise Exception("BAD LINE")

        if tool == 'gcc':
            if '-c' not in cmdline:
                so_name = None
                exe_name = None
                for v in cmdline:
                    if v.startswith('-Wl,-soname='):
                        so_name = v[len('-Wl,-soname='):]
                        break
                else:
                    next_is_exe_fname = False
                    for v in cmdline:
                        if next_is_exe_fname:
                            exe_name = v
                            break
                        elif v == '-o':
                            next_is_exe_fname = True
                if so_name is None and exe_name is None:
                    if '-E' in cmdline:
                        continue
                    print("BAD LINE@{} (cannot eval soname): ---{}---".format(line_number, line))
                    raise Exception("BAD LINE")
                if so_name is not None:
                    print("Linking DSO: '{}' in '{}'".format(so_name, exec_dir))
                if exe_name is not None:
                    print("Linking EXE: '{}' in '{}'".format(exe_name, exec_dir))
            else:
                src_line = cmdline[-1]
                if src_line not in ['/dev/null']:
                    src_defs = []
                    for d in cmdline:
                        if d.startswith('-D'):
                            define_value = d[2:]
                            if is_define_enabled(define_value):
                                src_defs.append(d[2:])
                    src = src_line
                    if '/' in src:
                        src = os.path.basename(src_line)
                    if exec_dir:
                        src_path = '/'.join([exec_dir, src_line])
                    else:
                        src_path = src_line
                    src = os.path.splitext(src)[0]
                    print(src_path)
                    if src in SRC_MAP:
                        print("BAD LINE@{} (src '{}' already in map): ---{}---".format(line_number, src, line))
                        raise Exception("BAD LINE")
                    SRC_MAP[src] = src_path
                    SRC_DEF_MAP[src] = ' '.join(src_defs)
        elif tool == 'ar':
            if cmdline[0] != 'r':
                print("BAD LINE@{}: ---{}---".format(line_number, line))
                raise Exception("BAD LINE")
            lib_name = os.path.basename(cmdline[1].rstrip('\\').strip())
            if lib_name.startswith('lib') and lib_name.endswith('.a'):
                lib_name = lib_name[3:-2]
            if lib_name not in LIBS_MAP:
                LIBS_MAP[lib_name] = []

            for v in cmdline[2:]:
                item = os.path.splitext(os.path.basename(v))[0]
                if item in LIBS_MAP[lib_name]:
                    print("BAD LINE@{} (src '{}' already in lib '{}'): ---{}---".format(line_number, item, lib_name, line))
                    raise Exception("BAD LINE")
                if item not in SRC_MAP:
                    print("BAD LINE@{} (unkown item '{}'): ---{}---".format(line_number, item, line))
                    raise Exception("BAD LINE")
                LIBS_MAP[lib_name].append(item)
                print('{} <- {}'.format(lib_name, item))
            if lib_name == 'crypto':
                crypto_linked = True
            elif lib_name == 'ssl':
                ssl_linked = True

    for lib_name in sorted(LIBS_MAP.keys()):
        lib_def = None
        for item in LIBS_MAP[lib_name]:
            item_def = SRC_DEF_MAP[item]
            if lib_def is None:
                lib_def = item_def
            else:
                if lib_def != item_def:
                    print("DEF1: '{}'".format(lib_def))
                    print("DEF2: '{}'".format(item_def))
                    raise Exception("BAD LINE")
        LIBS_DEF[lib_name] = lib_def


    with open(output_ini, mode='wt') as fh:
        print("[CONFIG]", file=fh)
        print("LIB_NANES = {}".format(' '.join(sorted(LIBS_MAP.keys()))), file=fh)
        print('', file=fh)
        for lib_name in sorted(LIBS_MAP.keys()):
            lib_def = LIBS_DEF[lib_name]
            print("[{}]".format(lib_name), file=fh)
            print('', file=fh)
            if lib_def is not None:
                print("DEF_LIST = ", file=fh)
                for item in lib_def.split():
                    print("    {}".format(item), file=fh)
                print('', file=fh)
            print("BUILD_LIST = ", file=fh)
            for item in LIBS_MAP[lib_name]:
                item_path = SRC_MAP[item]
                if os.path.basename(item_path) not in FILES_DISABLED  and not os.path.basename(item_path).startswith('uplink'):
                    print("    {}".format(item_path), file=fh)
            print('', file=fh)


if __name__ == '__main__':
    arch_list = ABI_ALL.split(',')
    for arch in arch_list:
        playback_log = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/{}/build.log'.format(arch)))
        playback_ini = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/{}/build.ini'.format(arch)))

        parse_build_log(playback_log, playback_ini)

    print('parsed!')
