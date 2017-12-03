#include "zlib_export_table.h"
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

static char NULL_PTR_STR[] = "NULL";

int main(int argc, char** argv)
{
    int retcode = 126;
    const char* shlib_zlib_path = NULL;
    void* shlib_zlib = NULL;
    if (argc >= 2)
    {
        shlib_zlib_path = argv[1];
    }
    if (!shlib_zlib_path || !shlib_zlib_path[0])
    {
        printf("ERROR: 'zlib' shlib path is not given as first arument of command line.\n");
        goto exit;
    }

    shlib_zlib = dlopen(shlib_zlib_path, RTLD_LAZY);
    if (shlib_zlib == NULL)
    {
        const char* lasterr = dlerror();
        if (lasterr == NULL)
             lasterr = NULL_PTR_STR;
        printf("ERROR: cannot load library: '%s', dlerror: %s\n", shlib_zlib_path, lasterr);
        goto exit;
    }

    int total_failures_count = 0;

    if (shlib_zlib != NULL)
    {
        printf("INFO: loaded library: '%s'\n", shlib_zlib_path);
        int idx = 0;
        int bad_count = 0;
        int good_count = 0;
        for (;;++idx)
        {
            const char* sym = ZLIB_EXPORT_TABLE[idx];
            if (sym == NULL)
                break;

            void* code = dlsym(shlib_zlib, sym);
            if (code == NULL)
            {
                bad_count += 1;
                const char* lasterr = dlerror();
                if (lasterr == NULL)
                     lasterr = NULL_PTR_STR;
                printf("    BAD SYMBOL: '%s', dlerror: %s\n", sym, lasterr);
                total_failures_count += 1;
            }
            else
            {
                good_count += 1;
            }
        }
        printf("SYMBOLS: good / bad / total --- %d / %d / %d\n", good_count, bad_count, idx);
    }

    if (total_failures_count == 0)
        retcode = 0;
    else
        retcode = 1;

exit:
  if (shlib_zlib != NULL)
    dlclose(shlib_zlib);

  return retcode;
}
