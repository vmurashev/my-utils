import argparse
import os.path
import shutil
import subprocess


def dir_add(dir_from, dir_to, dir_subject):
    source = os.path.normpath(os.path.join(dir_from, dir_subject))
    target = os.path.normpath(os.path.join(dir_to, dir_subject))
    if os.path.exists(target):
        shutil.rmtree(target)
    shutil.copytree(source, target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--subject', required=True)
    args = parser.parse_args()
    dir_add(args.source, args.target, args.subject)
