import argparse
import os.path
import shutil

def dir_del(dir_base, subject):
    if os.path.exists(subject):
        shutil.rmtree(subject)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--subject', required=True)
    args = parser.parse_args()
    dir_del(args.target, args.subject)
