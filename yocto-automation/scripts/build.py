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
import multiprocessing
import shutil


POKY_URL = 'git://git.yoctoproject.org/poky'
POKY_RELEASE = 'pyro'

DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
DIR_ROOT = os.path.normpath(os.path.join(DIR_HERE, '..'))
DIR_POKY = os.path.join(DIR_ROOT, 'poky')
DIR_OUTPUT = os.path.join(DIR_ROOT, 'output')
DIR_TARBALLS = os.path.join(DIR_ROOT, 'tarballs')

TAG_INI_SECTION_CONFIG = 'CONFIG'
TAG_INI_BUILD_ID = 'BUILD_ID'
TAG_INI_BITBAKE_TARGET = 'BITBAKE_TARGET'
TAG_INI_MACHINE_ARCH = 'MACHINE_ARCH'
TAG_INI_EXTRA_INSTALL = 'EXTRA_INSTALL'
TAG_INI_EXTRA_SPACE = 'EXTRA_SPACE'


def mkdir_safe(dname):
    if os.path.exists(dname):
        return
    try:
        os.makedirs(dname)
    except:
        if os.path.exists(dname):
            return
        raise


def load_ini_config(path):
    config = configparser.RawConfigParser()
    config.optionxform=str
    config.read(path)
    return config


def get_ini_conf_string1(config, section, option):
    return config.get(section, option).strip().replace('\n', ' ')


def touch_file(fname):
    with open(fname, mode='a') as _:
        pass


def poky_bootstrap():
    if os.path.isdir(DIR_POKY):
        shutil.rmtree(DIR_POKY)
    mkdir_safe(DIR_POKY)
    print ("> Clone '{0}' in '{1}'".format(POKY_URL, DIR_POKY))
    subprocess.check_call(["git", "clone", POKY_URL, "."], cwd=DIR_POKY)
    print ("> Checkout release '{0}'".format(POKY_RELEASE))
    subprocess.check_call(["git", "checkout", "-b", POKY_RELEASE, "origin/{0}".format(POKY_RELEASE)], cwd=DIR_POKY)


def build_image(poky_config):
    build_id        = get_ini_conf_string1(poky_config, TAG_INI_SECTION_CONFIG, TAG_INI_BUILD_ID)
    bitbake_target  = get_ini_conf_string1(poky_config, TAG_INI_SECTION_CONFIG, TAG_INI_BITBAKE_TARGET)
    machine_arch    = get_ini_conf_string1(poky_config, TAG_INI_SECTION_CONFIG, TAG_INI_MACHINE_ARCH)
    extra_install   = get_ini_conf_string1(poky_config, TAG_INI_SECTION_CONFIG, TAG_INI_EXTRA_INSTALL)
    extra_space     = get_ini_conf_string1(poky_config, TAG_INI_SECTION_CONFIG, TAG_INI_EXTRA_SPACE)

    dir_build = os.path.join(DIR_OUTPUT, build_id)
    mkdir_safe(dir_build)
    mkdir_safe(DIR_TARBALLS)
    config_draft = os.path.join(dir_build, 'build/conf/local.conf.orig')
    config_build = os.path.join(dir_build, 'build/conf/local.conf')
    if not os.path.isfile(config_draft):
        if not os.path.isfile(config_build):
            subprocess.check_call([os.path.join(DIR_HERE, 'defcfg.sh')], cwd=dir_build)
            shutil.copyfile(config_build, config_draft)

    with open(config_draft, mode='rt') as fsrc:
        with open(config_build, mode='wt') as fdst:
            print('DL_DIR = "{0}"'.format(DIR_TARBALLS), file=fdst)
            print('MACHINE = "{0}"'.format(machine_arch), file=fdst)
            print('CORE_IMAGE_EXTRA_INSTALL = "{0}"'.format(extra_install), file=fdst)
            print('IMAGE_ROOTFS_EXTRA_SPACE = "{0}"'.format(extra_space), file=fdst)
            print('', file=fdst)
            shutil.copyfileobj(fsrc, fdst)

    with open(os.path.join(dir_build, 'bitbake.target'), mode='wt') as fdst:
        print(bitbake_target, file=fdst)

    print ("> Build '{0}' for arch '{1}' ...".format(bitbake_target, machine_arch))
    subprocess.check_call([os.path.join(DIR_HERE, 'bake.sh')], cwd=dir_build)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs=1, required=True)
    args = parser.parse_args()
    config_file = args.config[0]
    init_only = False
    if config_file == '-':
        init_only = True

    if not init_only and not os.path.isfile(config_file):
        print("ERROR: File not found - '{0}'".format(config_file))
        exit(1)

    mkdir_safe(os.path.join(DIR_OUTPUT))
    poky_stamp = os.path.join(DIR_OUTPUT, 'poky.stamp')
    if not os.path.isfile(poky_stamp):
        poky_bootstrap()
        touch_file(poky_stamp)

    if init_only:
        exit(0)

    poky_config = load_ini_config(config_file)
    build_id = get_ini_conf_string1(poky_config, TAG_INI_SECTION_CONFIG, TAG_INI_BUILD_ID)
    build_id_stamp = os.path.join(DIR_OUTPUT, '{0}.stamp'.format(build_id))
    if not os.path.isfile(build_id_stamp):
        build_image(poky_config)
        touch_file(build_id_stamp)
    else:
        print("'{0}' is ready.".format(build_id))
