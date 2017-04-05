import os
import os.path
import shutil

DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

def parse_build_log(arch, input_log, output_ini):
    dir_nasm = os.path.join(DIR_HERE, 'obj', arch)
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
            asm_files_list.append(item)

    for item in asm_files_list:
        src_path = os.path.normpath(os.path.join(DIR_HERE, 'obj', 'openssl-src-{}'.format(arch), item))
        dst_path = os.path.join(dir_nasm, os.path.basename(item))
        print("::: {} >>> {}".format(src_path, dst_path))
        shutil.copyfile(src_path, dst_path)

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
        playback_log = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/{}/build.log'.format(arch)))
        playback_ini = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/{}/build.ini'.format(arch)))

        parse_build_log(arch, playback_log, playback_ini)

    print('parsed!')
