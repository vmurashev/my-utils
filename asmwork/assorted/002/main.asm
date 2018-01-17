DEFAULT REL

section .data
n1: dd 17
n2: dd 0x2a
n3: dd -2
n4: dd -4

section .text

global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    movsxd r8,  dword [n1]
    movsxd r9,  dword [n2]
    movsxd r10, dword [n3]
    movsxd r11, dword [n4]
    mov rax, 0
    add rax, r8
    add rax, r9
    add rax, r10
    add rax, r11
    sub rax, r8
    sub rax, r9
    sub rax, r10
    sub rax, r11
    leave
    ret
