module_type = 'executable'
module_name = 'shlib_verify_export'
build_list = ['main.c']
include_dir_list = ['${@project_root}/minicmn']
lib_list = ['${@project_root}/minicmn']
prebuilt_lib_list_linux = ['dl']
win_console=1
