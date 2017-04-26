section .data
HelloMsg: db 'Hello world!',0

section .text

extern puts
global asm_main

asm_main:
    push ebp
    mov ebp,esp
    push ebx
    push esi
    push edi

    push HelloMsg
    call puts
    add esp,4

    mov esp,ebp
    pop ebp
    ret
