module_type = 'executable'
module_name = 'asmwork_assorted_002'
build_list = ['main.asm']
win_console = 1
nasm = 1
if BUILDSYS_TOOLSET_NAME == 'msvs': 
    prebuilt_lib_list_windows = ['msvcrt']
