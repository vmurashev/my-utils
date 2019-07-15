#!/usr/bin/env python

import os
import os.path
import sys

DIR_HERE = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))

with open(os.path.join(DIR_HERE, 'conf.sh'), mode='rt') as conf_sh:
    exec(compile(conf_sh.read(), os.path.join(DIR_HERE, 'conf.sh'), 'exec'))

DIR_PROJECT_ROOT = os.path.normpath(os.path.join(DIR_HERE, 'draft'))
DIR_OPENSSL_SUBMODULE = os.path.join(DIR_PROJECT_ROOT, 'openssl')
DIR_OPENSSL_SUBMODULE_VENDOR = os.path.join(DIR_OPENSSL_SUBMODULE, 'vendor')

DIR_OBJ_TO_SCAN = os.path.join(DIR_PROJECT_ROOT, 'output/obj')

SCAN_ENTRIES = ['crypto', 'crypto_static', 'openssl', 'ssl', 'ssl_static']
SRC_EXT = ['.c', '.s', '.S']

def load_py_object(fname):
    with open(fname, mode='rt') as file:
        source = file.read()
    ast = compile(source, fname, 'eval')
    return eval(ast, {"__builtins__": None}, {})


def load_fnames(dpath, headers, sources):
    for root, _, files in os.walk(dpath, topdown=False):
        for fname in files:
            if not fname.endswith('.dep'):
                continue
            sources.add(fname[0:-4])
            dep_info = load_py_object(os.path.join(root, fname))
            for hf in dep_info:
                norm_hf = os.path.normpath(os.path.join(DIR_PROJECT_ROOT, hf))
                if norm_hf.startswith(DIR_OPENSSL_SUBMODULE_VENDOR):
                    headers.add(os.path.basename(hf))


def eval_unused_files(used_headers, used_sources, required_files, unused_files):
    for root, _, files in os.walk(DIR_OPENSSL_SUBMODULE_VENDOR, topdown=False):
        for fname in files:
            file_in_use = False
            if fname in used_headers:
                file_in_use = True
            if not file_in_use:
                for e in SRC_EXT:
                    if fname.endswith(e):
                        b = fname[0:-len(e)]
                        if b in used_sources:
                            file_in_use =True

            unused_subject = os.path.join(root, fname)
            if not file_in_use:
                if unused_subject in required_files:
                    file_in_use = True
                if 'msvs-win32' in unused_subject:
                    file_in_use = True
                elif 'msvs-win64' in unused_subject:
                    file_in_use = True

                if not file_in_use:
                    unused_files.append(unused_subject)


def main():
    required_files = [
        os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'NEWS'),
        os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'CHANGES'),
        os.path.join(DIR_OPENSSL_SUBMODULE_VENDOR, 'LICENSE')
    ]
    used_headers = set()
    used_sources = set()
    unused_files = []
    for dname in SCAN_ENTRIES:
        dpath = os.path.join(DIR_OBJ_TO_SCAN, dname)
        load_fnames(dpath, used_headers, used_sources)
    eval_unused_files(used_headers, used_sources, required_files, unused_files)
    force_remove = True if len(sys.argv) > 1 and sys.argv[1] == '-f' else False
    if not force_remove:
        for x in unused_files:
            print(x)
        return
    for f in unused_files:
        os.remove(f)
        print("> Removed file: {}".format(f))
    for root, dirs, _ in os.walk(DIR_OPENSSL_SUBMODULE_VENDOR, topdown=False):
        for dname in dirs:
            dir_subject = os.path.join(root, dname)
            if not os.listdir(dir_subject):
                os.rmdir(dir_subject)
                print("> Removed directory: {}".format(dir_subject))

if __name__ == '__main__':
    main()
