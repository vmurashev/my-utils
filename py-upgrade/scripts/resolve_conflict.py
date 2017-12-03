from __future__ import print_function
import argparse
import os.path
import os
import shutil
import subprocess

DIFF_TOOL = r'C:\Git\usr\bin\diff.exe'
PATCH_TOOL = r'C:\Git\usr\bin\patch.exe'


def resolve_conflict(vendor_dir_from, vendor_dir_to, repo_dir, work_dir, file_subject):
    old_vendor_source = os.path.normpath(os.path.join(vendor_dir_from, file_subject))
    new_vendor_source = os.path.normpath(os.path.join(vendor_dir_to, file_subject))
    repo_source = os.path.normpath(os.path.join(repo_dir, file_subject))

    fix_cwd = os.path.normpath(os.path.join(work_dir, os.path.dirname(file_subject)))
    if not os.path.exists(fix_cwd):
        os.makedirs(fix_cwd)

    diff_file_name = '{}.diff'.format(os.path.basename(file_subject))
    diff_file_pth = os.path.join(fix_cwd, diff_file_name)
    with open(diff_file_pth, mode='wt') as diff_file:
        cmdline = '{0} --strip-trailing-cr {1} {2}'.format(DIFF_TOOL, old_vendor_source, repo_source)
        print("> exec: '{}', stdout: '{}'".format(cmdline, diff_file_pth))
        exit_code = subprocess.call(cmdline, stdout=diff_file)
        if exit_code != 1:
            raise Exception("Unexpected diff-tool exit code: {}".format(exit_code))

    print(80*'-')
    with open(diff_file_pth, mode='rt') as diff_file:
        diff_text = diff_file.read()
    print(diff_text, end='')
    print(80*'-')

    new_file_name = '{}.new'.format(os.path.basename(file_subject))
    new_file_pth = os.path.join(fix_cwd, new_file_name)
    if os.path.exists(new_file_pth):
        os.remove(new_file_pth)
    shutil.copy2(new_vendor_source, new_file_pth)

    fixed_file_name = os.path.basename(file_subject)
    fixed_file_pth = os.path.join(fix_cwd, fixed_file_name)
    if os.path.exists(fixed_file_pth):
        os.remove(fixed_file_pth)
    cmdline = '{0} {1} {2} --output={3}'.format(PATCH_TOOL, new_file_name, diff_file_name, fixed_file_name)
    print("> exec: '{}' in '{}'".format(cmdline, fix_cwd))
    subprocess.check_call(cmdline, cwd=fix_cwd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vendor-from', required=True)
    parser.add_argument('--vendor-to', required=True)
    parser.add_argument('--repo-dir',  required=True)
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--subject', required=True)
    args = parser.parse_args()
    resolve_conflict(args.vendor_from, args.vendor_to, args.repo_dir, args.work_dir, args.subject)
