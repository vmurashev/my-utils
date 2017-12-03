import argparse
import os.path
import os
import shutil
import subprocess


def file_add(dir_from, dir_to, file_subject):
    source = os.path.normpath(os.path.join(dir_from, file_subject))
    target = os.path.normpath(os.path.join(dir_to, file_subject))
    if os.path.exists(target):
        os.remove(target)
    shutil.copy2(source, target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--subject', required=True)
    args = parser.parse_args()
    file_add(args.source, args.target, args.subject)
