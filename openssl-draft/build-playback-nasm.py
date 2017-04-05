import os.path

DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

def parse_build_log(input_log, output_ini):
    lines = [line.rstrip('\r\n') for line in open(input_log)]
    line_number = 0
    count = 0
    for line in lines:
        line_number += 1
        bits = line.strip().split()
        if not bits:
            continue
        if 'nasm' in bits[0]:
            count += 1
            print(bits)
    print("TOTAL: {}".format(count))


if __name__ == '__main__':
    arch_list = ['msvs-win32', 'msvs-win64']
    for arch in arch_list:
        playback_log = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/{}/build.log'.format(arch)))
        playback_ini = os.path.normpath(os.path.join(DIR_HERE, 'obj/bin-trace/{}/build.ini'.format(arch)))

        parse_build_log(playback_log, playback_ini)

    print('parsed!')
