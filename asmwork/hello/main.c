#include <stdio.h>
extern int asm_main();

int main()
{
    int ret = 0;
    ret = asm_main();
    printf("asm_main() - return code: %d\n", ret);
    return ret;
}
