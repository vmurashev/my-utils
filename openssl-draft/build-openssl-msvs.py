import argparse
import os.path
import inspect
import subprocess
import struct
import ctypes
import sys
import time
import shutil


DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
DIR_OBJ = os.path.join(DIR_HERE,'obj')

if not os.path.exists(DIR_OBJ):
    os.makedirs(DIR_OBJ)

with open(os.path.join(DIR_HERE, 'conf.sh'), mode='rt') as conf_sh:
    exec(compile(conf_sh.read(), os.path.join(DIR_HERE, 'conf.sh'), 'exec'))

ZLIB_ARC_NAME = os.path.basename(ZLIB_URL)
OPENSSL_ARC_NAME = os.path.basename(OPENSSL_URL)

MSVS_VARS_WRAPPER32 = os.path.join(DIR_OBJ, '{}_vars_dump32.bat'.format(MSVS_LANDMARK.lower()))
MSVS_VARS_WRAPPER64 = os.path.join(DIR_OBJ, '{}_vars_dump64.bat'.format(MSVS_LANDMARK.lower()))

ENV_DUMP_BATCH = '''@echo off
call "{0}" 1>nul 2>nul
if errorlevel 0 set
'''

MSVS_COMPILER_EXECUTABLE = 'cl.exe'


class BuildLogicError(Exception):
    def __init__(self, text, frame=1):
        frame_info = inspect.stack()[frame]
        msg = '[{}({})] {}'.format(os.path.basename(frame_info[1]), frame_info[2], text)
        Exception.__init__(self, msg)


def load_py_object(fname):
    with open(fname, mode='rt') as file:
        source = file.read()
    ast = compile(source, fname, 'eval')
    return eval(ast, {"__builtins__": None}, {})


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


def escape_string(value):
    return value.replace('\\', '\\\\').replace('"', '\\"')


def merge_env_value(patch, original=None):
    if not isinstance(patch, list):
        return patch
    path_ext = os.pathsep.join(patch)
    if original is None:
        return path_ext
    return os.pathsep.join([path_ext, original])


def apply_environ_patch(env_patch, origin=None):
    if env_patch is None:
        return None
    custom_env = {}
    if origin is None:
        custom_env.update(os.environ)
    else:
        custom_env.update(origin)
    env_upkeys = { x.upper(): x for x in custom_env.keys() }
    for var_name, var_value_patch in env_patch.items():
        var_name_upper = var_name.upper()
        original_value = None
        patched_var_name = var_name
        if var_name_upper in env_upkeys:
            patched_var_name = env_upkeys[var_name_upper]
            original_value = custom_env.get(patched_var_name)
        patched_value = merge_env_value(var_value_patch, original_value)
        custom_env[patched_var_name] = patched_value
    return custom_env


def subprocess_with_msvs_environment(is_win64):
    env_patch_file32 = os.path.join(DIR_OBJ, '{}_env_patch32.txt'.format(MSVS_LANDMARK.lower()))
    env_patch_file64 = os.path.join(DIR_OBJ, '{}_env_patch64.txt'.format(MSVS_LANDMARK.lower()))
    env_patch_stamp  = os.path.join(DIR_OBJ, '{}_env_patch.stat'.format(MSVS_LANDMARK.lower()))
    if not os.path.exists(env_patch_stamp):
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

        for env_map, env_patch_file in [
                        (env_map32, env_patch_file32),
                        (env_map64, env_patch_file64) ]:
            align = 4 * ' '
            with open(env_patch_file, mode='wt') as env_file:
                env_file.writelines(['{\n'])
                for var_name in sorted(env_map.keys()):
                    env_file.writelines([align, '"', var_name, '"', ': '])
                    var_value = env_map[var_name]
                    if isinstance(var_value, list):
                        env_file.writelines(['['])
                        for pth in var_value:
                            env_file.writelines(['\n', 2 * align, '"', escape_string(pth), '",'])
                        env_file.writelines(['\n', align, '],', '\n'])
                    else:
                        env_file.writelines(['"', escape_string(var_value), '"', ',\n'])
                env_file.writelines(['}\n'])

        with open(env_patch_stamp, mode='w'):
            pass

    if is_win64:
        env_patch = load_py_object(env_patch_file64)
        trace_dir = os.path.join(DIR_OBJ, 'bin-trace', 'msvs-win64')
        openssl_srcdir = os.path.join(DIR_OBJ, 'openssl-src-msvs-win64')
    else:
        env_patch = load_py_object(env_patch_file32)
        trace_dir = os.path.join(DIR_OBJ, 'bin-trace', 'msvs-win32')
        openssl_srcdir = os.path.join(DIR_OBJ, 'openssl-src-msvs-win32')

    if os.path.exists(openssl_srcdir):
        shutil.rmtree(openssl_srcdir)

    mkdir_safe(openssl_srcdir)
    tar_custom_env = apply_environ_patch({'PATH':[os.path.dirname(TAR_FOR_WINDOWS)]})
    tar_argv = [TAR_FOR_WINDOWS, 'xf', os.path.join(DIR_OBJ, OPENSSL_ARC_NAME), '--strip-components=1', '--force-local', '-C', openssl_srcdir]
    print("EXEC:> {}".format(' '.join(tar_argv)))
    subprocess.check_call(tar_argv, env=tar_custom_env)

    shutil.copyfile(os.path.join(DIR_OBJ, 'zlib', 'zlib.h'), os.path.join(openssl_srcdir, 'include', 'zlib.h'))
    shutil.copyfile(os.path.join(DIR_OBJ, 'zlib', 'zconf.h'), os.path.join(openssl_srcdir, 'include', 'zconf.h'))

    mkdir_safe(trace_dir)

    build_custom_env = apply_environ_patch(env_patch)
    build_custom_env = apply_environ_patch({'PATH':[NASM_DIR]}, build_custom_env)

    ret_code = None
    output_file = os.path.join(trace_dir, 'build.log')
    with open(output_file, mode='wt') as ofh:
        with open(output_file, mode='rt') as ifh:
            p = subprocess.Popen([sys.executable, '-u', __file__, '--worker', '--config', 'win64' if is_win64 else 'win32'],
                env=build_custom_env, stdin=subprocess.DEVNULL, stdout=ofh, stderr=subprocess.STDOUT, universal_newlines=True)
            while True:
                line = ifh.readline()
                if not line:
                    ret_code = p.poll()
                    if ret_code is not None:
                        p.wait()
                        break
                    time.sleep(0.1)
                    continue
                print(line, end='')
    if ret_code == 0:
        print('Done!')
    else:
        print('ABORTED.')
    return ret_code


def build_openssl(is_win64):
    if is_win64:
        openssl_srcdir = os.path.join(DIR_OBJ, 'openssl-src-msvs-win64')
        openssl_target = 'VC-WIN64A'
    else:
        openssl_srcdir = os.path.join(DIR_OBJ, 'openssl-src-msvs-win32')
        openssl_target = 'VC-WIN32 -DUNICODE -D_UNICODE'

    openssl_conf_cmd = [PERL_FOR_WINDOWS, 'Configure']
    openssl_conf_cmd += OPENSSL_OPTIONS.split()
    openssl_conf_cmd += openssl_target.split()

    print("EXEC:> {}".format(' '.join(openssl_conf_cmd)))
    ret_code = subprocess.call(openssl_conf_cmd, cwd=openssl_srcdir)
    if ret_code != 0:
        return ret_code

    print("EXEC:> nmake")
    ret_code = subprocess.call(['nmake'], cwd=openssl_srcdir)
    return ret_code


def init():
    if not os.path.isfile(os.path.join(DIR_OBJ, OPENSSL_ARC_NAME)):
        curl_argv = [CURL_FOR_WINDOWS, '-L', '-o', os.path.join(DIR_OBJ, OPENSSL_ARC_NAME), OPENSSL_URL]
        print("EXEC:> {}".format(' '.join(curl_argv)))
        subprocess.check_call(curl_argv)

    if not os.path.isfile(os.path.join(DIR_OBJ, ZLIB_ARC_NAME)):
        curl_argv = [CURL_FOR_WINDOWS, '-L', '-o', os.path.join(DIR_OBJ, ZLIB_ARC_NAME), ZLIB_URL]
        print("EXEC:> {}".format(' '.join(curl_argv)))
        subprocess.check_call(curl_argv)
 
    if not os.path.isdir(os.path.join(DIR_OBJ, 'zlib')):
        os.makedirs(os.path.join(DIR_OBJ, 'zlib'))

    if not os.listdir(os.path.join(DIR_OBJ, 'zlib')):
        tar_custom_env = apply_environ_patch({'PATH':[os.path.dirname(TAR_FOR_WINDOWS)]})
        tar_argv = [TAR_FOR_WINDOWS, 'xf', os.path.join(DIR_OBJ, ZLIB_ARC_NAME), '--strip-components=1', '--force-local', '-C', os.path.join(DIR_OBJ, 'zlib')]
        print("EXEC:> {}".format(' '.join(tar_argv)))
        subprocess.check_call(tar_argv, env=tar_custom_env)


def main():
    ret_code = 126
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs=1, choices=['win32', 'win64'], required=True)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    try:
        is_win64 = True if args.config[0] == 'win64' else False
        if args.worker:
            ret_code = build_openssl(is_win64)
        else:
            init()
            ret_code = subprocess_with_msvs_environment(is_win64)
    except BuildLogicError as ex:
        print("ERROR: {}".format(ex))
    return ret_code

if __name__ == '__main__':
    exit(main())
