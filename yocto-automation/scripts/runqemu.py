#!/usr/bin/env python

from __future__ import print_function
import argparse
import os
import os.path
import sys
if sys.version_info[0] < 3:
    import ConfigParser as configparser
else:
    import configparser
import subprocess


DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
DIR_ROOT = os.path.normpath(os.path.join(DIR_HERE, '..'))
DIR_OUTPUT = os.path.join(DIR_ROOT, 'output')

TAG_INI_SECTION_CONFIG = 'CONFIG'
TAG_INI_BUILD_ID = 'BUILD_ID'
TAG_INI_MACHINE_ARCH = 'MACHINE_ARCH'


def load_ini_config(path):
    config = configparser.RawConfigParser()
    config.optionxform=str
    config.read(path)
    return config


def get_ini_conf_string1(config, section, option):
    return config.get(section, option).strip()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs=1, required=True)
    args = parser.parse_args()
    config_file = args.config[0]

    if not os.path.isfile(config_file):
        print("ERROR: File not found - '{0}'".format(config_file))
        exit(1)

    poky_config = load_ini_config(config_file)
    build_id = get_ini_conf_string1(poky_config, TAG_INI_SECTION_CONFIG, TAG_INI_BUILD_ID)
    machine_arch = get_ini_conf_string1(poky_config, TAG_INI_SECTION_CONFIG, TAG_INI_MACHINE_ARCH)
    dir_build = os.path.join(DIR_OUTPUT, build_id)

    if not os.path.isdir(dir_build):
        print("ERROR: Directory not found - '{0}'".format(dir_build))
        exit(1)

    arch_info_file = os.path.join(dir_build, 'machine.arch')
    if not os.path.isfile(arch_info_file):
        with open(arch_info_file, mode='wt') as fdst:
            print(machine_arch, file=fdst)

    subprocess.call([os.path.join(DIR_HERE, 'runqemu.sh')], cwd=dir_build)
