import os
import os.path
import shutil
import subprocess
import hashlib
import io


DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
DIR_OBJ = os.path.join(DIR_HERE,'obj')

with open(os.path.join(DIR_HERE, 'conf.sh'), mode='rt') as conf_sh:
    exec(compile(conf_sh.read(), os.path.join(DIR_HERE, 'conf.sh'), 'exec'))


def md5_of_file(path):
    m = hashlib.md5()
    data = io.FileIO(path).readall().replace(b'\r\n', b'\n').rstrip(b'\r\n')
    m.update(data)
    return m.hexdigest()


def is_text_files_equal(file1, file2):
    h1 = md5_of_file(file1)
    h2 = md5_of_file(file2)
    return h1 == h2


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


def parse_build_log(arch, input_log, output_ini):
    dir_nasm = os.path.join(DIR_OBJ, arch)
    if os.path.exists(dir_nasm):
        shutil.rmtree(dir_nasm)
    os.makedirs(dir_nasm)

    lines = [line.rstrip('\r\n') for line in open(input_log)]
    asm_files_list = []

    for line in lines:
        bits = line.strip().split()
        if not bits:
            continue

        if 'nasm' in bits[0]:
            item = bits[-1]
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            item = item.replace('\\', '/')
            item_title = os.path.basename(item)
            if item_title.startswith('uplink'):
                continue
            asm_files_list.append(item)

    for item in asm_files_list:
        src_path = os.path.normpath(os.path.join(DIR_OBJ, 'openssl-src-{}'.format(arch), item))
        dst_path = os.path.join(dir_nasm, os.path.basename(item))
        print("::: {} >>> {}".format(src_path, dst_path))
        shutil.copyfile(src_path, dst_path)

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

        perl_gen_env = apply_environ_patch({'ASM':'nasm','PATH':[NASM_DIR]})

        asm_target_model = 'nasm' if arch == 'msvs-win64' else 'win32n'
        dst_path_autogen = dst_path + '.2' 
        perl_gen_cmd = [PERL_FOR_WINDOWS, perl_generator, asm_target_model]
        if arch == 'msvs-win32':
            perl_gen_cmd += ['-DOPENSSL_IA32_SSE2']
        perl_gen_cmd += [dst_path_autogen]

        print("::: EXEC ::: {}".format(' '.join(perl_gen_cmd)))
        subprocess.check_call(perl_gen_cmd, env=perl_gen_env)
        if not os.path.isfile(dst_path_autogen):
            raise Exception("Generated file not found - '{}'".format(dst_path_autogen))
        print("::: Generated file ::: {}".format(dst_path_autogen))

    all_ok = True
    for item in asm_files_list:
        dst_path = os.path.join(dir_nasm, os.path.basename(item))
        dst_path_autogen = dst_path + '.2'
        eq = is_text_files_equal(dst_path, dst_path_autogen)
        if eq:
            print('OK     - {}'.format(os.path.basename(dst_path)))
        else:
            print('FAILED - {}'.format(os.path.basename(dst_path)))
            all_ok = False

    if not all_ok:
        raise Exception("ASM files autogeneration doesn't work.")

    with open(output_ini, mode='wt') as fh:
        print("[NASM]", file=fh)
        print('', file=fh)
        print("BUILD_LIST = ", file=fh)
        for item in asm_files_list:
            print("    {}".format(item), file=fh)
        print('', file=fh)


if __name__ == '__main__':
    arch_list = ['msvs-win32', 'msvs-win64']
    for arch in arch_list:
        playback_log = os.path.normpath(os.path.join(DIR_OBJ, 'bin-trace/{}/build.log'.format(arch)))
        playback_ini = os.path.normpath(os.path.join(DIR_OBJ, 'bin-trace/{}/build.ini'.format(arch)))

        parse_build_log(arch, playback_log, playback_ini)

    print('parsed!')
