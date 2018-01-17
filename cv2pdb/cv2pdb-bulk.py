from __future__ import print_function
import os.path
import sys
import shutil
import subprocess


TMP_DIRNAME = 'pdbgen'
CV2PDB_EXECUTABLE = 'cv2pdb.exe'


def is_exe(fpath):
    with open(fpath, "rb") as f:
        magic = f.read(4)
    if magic[0:2] == b'\x4D\x5A': # MZ
        return True
    return False


def cv2pdb_bulk(srcdir):
    for root, _, files in os.walk(srcdir):
        exe_files = []
        for fname in files:
            fpath = os.path.join(root, fname)
            if is_exe(fpath):
                exe_files.append(fname)
        if not exe_files:
            continue
        work_dir = os.path.join(root, TMP_DIRNAME)
        if os.path.isdir(work_dir):
            print("CV2PDB: ERROR: found unexpectedly: '{}'".format(work_dir))
            exit(1)
        os.mkdir(work_dir)
        for exe_name in exe_files:
            shutil.move(os.path.join(root, exe_name), work_dir)
            pdb_name = os.path.splitext(exe_name)[0] + '.pdb'
            cv2pdb_args = [CV2PDB_EXECUTABLE, os.path.join(work_dir, exe_name), os.path.join(root, exe_name), os.path.join(root, pdb_name)]
            print(cv2pdb_args)
            subprocess.check_call(cv2pdb_args)
        shutil.rmtree(work_dir)


if __name__ == '__main__':
    srcdir = os.path.normpath(os.path.abspath(sys.argv[1]))
    print("CV2PDB: SOURCE: '{}'".format(srcdir))
    if not os.path.isdir(srcdir):
        print('CV2PDB: ERROR: Source directory is not found.')
        exit(1)
    cv2pdb_bulk(srcdir)
