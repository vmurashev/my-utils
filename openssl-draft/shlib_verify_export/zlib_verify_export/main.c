#include "zlib_export_table.h"
#include <stdio.h>
#include <string.h>
#include <minicmn/shlib.h>


int main(int argc, char** argv)
{
    int retcode = 126;
    const char* shlib_zlib_path = NULL;
    minicmn_SharedLibrary* shlib_zlib = NULL;
    minicmn_Error* err = NULL;
    if (argc >= 2)
    {
        shlib_zlib_path = argv[1];
    }
    if (!shlib_zlib_path || !shlib_zlib_path[0])
    {
        printf("ERROR: 'zlib' shlib path is not given as first arument of command line.\n");
        goto exit;
    }

    if (minicmn_LoadLibrary(shlib_zlib_path, &shlib_zlib, &err) != 0)
    {
        printf("ERROR: cannot load library: '%s'\n", shlib_zlib_path);
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
            void* code = minicmn_GetProcAddress(shlib_zlib, sym);
            if (code == NULL)
            {
                bad_count += 1;
                printf("    BAD SYMBOL: '%s'\n", sym);
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
    if (err != NULL)
    {
        printf("ERROR: %s\n", err->ErrorText);
        minicmn_DataFree(err);
    }
    minicmn_DataFree(shlib_zlib);
    return retcode;
}
