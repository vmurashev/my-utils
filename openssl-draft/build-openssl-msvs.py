import argparse
import os.path
import inspect
import subprocess
import struct
import ctypes
import sys


DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
DIR_OBJ = os.path.join(DIR_HERE,'obj')
MSVS_VARS_WRAPPER32 = os.path.join(DIR_OBJ, 'vars_dump32.bat')
MSVS_VARS_WRAPPER64 = os.path.join(DIR_OBJ, 'vars_dump64.bat')

ENV_DUMP_BATCH = '''@echo off
call "{0}" 1>nul 2>nul
if errorlevel 0 set
'''

MSVS_COMPILER_EXECUTABLE = 'cl.exe'

if not os.path.exists(DIR_OBJ):
    os.makedirs(DIR_OBJ)

with open(os.path.join(DIR_HERE, 'conf.sh'), mode='rt') as conf_sh:
    exec(compile(conf_sh.read(), os.path.join(DIR_HERE, 'conf.sh'), 'exec'))


class BuildLogicError(Exception):
    def __init__(self, text, frame=1):
        frame_info = inspect.stack()[frame]
        msg = '[{}({})] {}'.format(os.path.basename(frame_info[1]), frame_info[2], text)
        Exception.__init__(self, msg)


def is_windows_64bit():
    if sys.platform == 'win32':
        if struct.calcsize("P") == 8:
            return True
        kernel32 = ctypes.windll.kernel32
        process = kernel32.GetCurrentProcess()
        ret = ctypes.c_int()
        kernel32.IsWow64Process(process, ctypes.byref(ret))
        is64bit = (ret.value != 0)
        return is64bit
    return False


def mkdir_safe(dname):
    if os.path.exists(dname):
        return
    try:
        os.makedirs(dname)
    except:
        if os.path.exists(dname):
            return
        raise


def split_path(value):
    paths = []
    for path in value.split(';'):
        if path:
            paths.append(path)
    return paths


def split_if_path(value):
    if ';' not in value:
        return value
    return split_path(value)


def get_path_difference(original, final):
    orig_paths = split_path(original)
    final_paths = split_path(final)
    new_paths = []
    for path in final_paths:
        if path not in orig_paths:
            new_paths.append(path)
    return new_paths


def resolve_compiler_path(msvs_new_paths):
    for msvs_path in msvs_new_paths:
        cl_path_variant = os.path.normpath(os.path.join(msvs_path, MSVS_COMPILER_EXECUTABLE))
        if os.path.isfile(cl_path_variant):
            return cl_path_variant
    return None


def get_cl_and_envmap_from_dump(env_dump):
    env_map = {}
    cl_path = None
    for env_entry in env_dump.splitlines():
        var_name, var_value = env_entry.split('=', 1)
        is_path = var_name.upper() == 'PATH'
        if not is_path and var_name in os.environ:
            continue
        if is_path:
            paths_to_add = get_path_difference(os.environ[var_name], var_value)
            cl_path = resolve_compiler_path(paths_to_add)
            env_map[var_name] = paths_to_add
        else:
            env_map[var_name] = split_if_path(var_value)
    if cl_path is None:
        raise BuildLogicError("Cannot bootstrap MSVS: file '{}' not found.".format(MSVS_COMPILER_EXECUTABLE))
    return (cl_path, env_map)


def build_openssl_by_msvs(is_win64):
    is_on_win64 = is_windows_64bit()
    msvs_vars_dir = os.environ.get(MSVS_LANDMARK)
    if msvs_vars_dir is None:
        raise BuildLogicError("Cannot bootstrap MSVS: variable '{}' not found in environment.".format(MSVS_LANDMARK))
    msvs_vars_batch32 = os.path.join(msvs_vars_dir, 'vsvars32.bat')
    if not os.path.exists(msvs_vars_batch32):
        raise BuildLogicError("Cannot bootstrap MSVS: file '{}' not found.".format(msvs_vars_batch32))
    with open(MSVS_VARS_WRAPPER32, mode='wt') as wrapper_file32:
        wrapper_file32.write(ENV_DUMP_BATCH.format(msvs_vars_batch32))
    env_dump32 = subprocess.check_output(MSVS_VARS_WRAPPER32, shell=True, universal_newlines=True)
    cl_path32, env_map32 = get_cl_and_envmap_from_dump(env_dump32)
    cl_home = os.path.dirname(cl_path32)
    if is_on_win64:
        msvs_vars_batch64_variants = [ os.path.join(cl_home, 'amd64', 'vcvarsamd64.bat'), os.path.join(cl_home, 'amd64', 'vcvars64.bat') ]
    else:
        msvs_vars_batch64_variants = [ os.path.join(cl_home, 'x86_amd64', 'vcvarsx86_amd64.bat') ]
    msvs_vars_batch64 = None
    for batch64 in msvs_vars_batch64_variants:
        if os.path.isfile(batch64):
            msvs_vars_batch64 = batch64
            break
    if msvs_vars_batch64 is None:
        if len(msvs_vars_batch64_variants) == 1:
            raise BuildLogicError("Cannot bootstrap MSVS: file '{}' not found.".format(msvs_vars_batch64_variants[0]))
        else:
            raise BuildLogicError("Cannot bootstrap MSVS: files not found:\n    {}".format('\n    '.join(msvs_vars_batch64_variants)))
    with open(MSVS_VARS_WRAPPER64, mode='wt') as wrapper_file64:
        wrapper_file64.write(ENV_DUMP_BATCH.format(msvs_vars_batch64))
    env_dump64 = subprocess.check_output(MSVS_VARS_WRAPPER64, shell=True, universal_newlines=True)
    cl_path64, env_map64 = get_cl_and_envmap_from_dump(env_dump64)

    raise BuildLogicError('TODO')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs=1, choices=['win32', 'win64'], required=True)
    args = parser.parse_args()
    try:
        is_win64 = True if args.config[0] == 'win64' else False
        build_openssl_by_msvs(is_win64)
    except BuildLogicError as ex:
        print("ERROR: {}".format(ex))


if __name__ == '__main__':
    exit(main())
