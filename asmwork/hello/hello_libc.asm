DEFAULT REL

%ifidn __OUTPUT_FORMAT__, win32
    %define EXTERNC_UNDERSCORE
    %define SYS_WINDOWS
%endif

%ifidn __OUTPUT_FORMAT__, win64
    %define SYS_WINDOWS
%endif

%macro cglobal_underscore 1
    global  _%1
    %define %1 _%1
%endmacro

%macro cextern_underscore 1
    extern  _%1
    %define %1 _%1
%endmacro

%ifdef EXTERNC_UNDERSCORE
    %define cextern cextern_underscore
    %define cglobal cglobal_underscore
%else
    %define cextern extern
    %define cglobal global
%endif


cextern puts
cglobal asm_main


section .data
HelloMsg: db 'Hello world!',0

section .text
asm_main:
%ifidn __BITS__,64            ; x86_64
    push rbp
    mov rbp, rsp

%ifdef SYS_WINDOWS
    lea rcx, [HelloMsg]
    call puts
%else
    lea rdi, [HelloMsg]
    call puts wrt ..plt
%endif
    mov rax, 42
    leave
    ret
%else                         ; x86
    push ebp
    mov ebp, esp

%ifdef SYS_WINDOWS
    push HelloMsg
    call puts
%else
    lea eax, [ebx + HelloMsg wrt ..gotoff]
    push eax
    call puts wrt ..plt
%endif
    add esp, 4

    mov eax, 42
    leave
    ret
%endif
