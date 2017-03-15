#include "crypto_export_table.h"
#include "ssl_export_table.h"
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

static char NULL_PTR_STR[] = "NULL";

int main(int argc, char** argv)
{
    int retcode = 126;
    const char* shlib_crypto_path = NULL;
    const char* shlib_ssl_path = NULL;
    void* shlib_crypto = NULL;
    void* shlib_ssl = NULL;
    if (argc >= 2)
    {
        shlib_crypto_path = argv[1];
    }
    if (argc >= 3)
    {
        shlib_ssl_path = argv[2];
    }
    if (!shlib_crypto_path || !shlib_crypto_path[0])
    {
        printf("ERROR: crypto shlib path is not given as first arument of command line.\n");
        goto exit;
    }
    if (!shlib_ssl_path || !shlib_ssl_path[0])
    {
        printf("ERROR: ssl shlib path is not given as second arument of command line.\n");
        goto exit;
    }

    int omit_crypto = strcmp(shlib_crypto_path, "-");
    int omit_ssl = strcmp(shlib_ssl_path, "-");

    if (!omit_crypto)
    {
        shlib_crypto = dlopen(shlib_crypto_path, RTLD_LAZY);
        if (shlib_crypto == NULL)
        {
            const char* lasterr = dlerror();
            if (lasterr == NULL)
                 lasterr = NULL_PTR_STR;
            printf("ERROR: cannot load library: '%s', dlerror: %s\n", shlib_crypto_path, lasterr);
        }
    }

    if (!omit_ssl)
    {
        shlib_ssl = dlopen(shlib_ssl_path, RTLD_LAZY);
        if (shlib_ssl == NULL)
        {
            const char* lasterr = dlerror();
            if (lasterr == NULL)
                 lasterr = NULL_PTR_STR;
            printf("ERROR: cannot load library: '%s', dlerror: %s\n", shlib_ssl_path, lasterr);
        }
    }

    if (shlib_crypto != NULL)
    {
        printf("INFO: loaded library: '%s'\n", shlib_crypto_path);
        int idx = 0;
        int bad_count = 0;
        int good_count = 0;
        for (;;++idx)
        {
            const char* sym = CRYPTO_EXPORT_TABLE[idx];
            if (sym == NULL)
                break;

            void* code = dlsym(shlib_crypto, sym);
            if (code == NULL)
            {
                bad_count += 1;
                const char* lasterr = dlerror();
                if (lasterr == NULL)
                     lasterr = NULL_PTR_STR;
                printf("    BAD SYMBOL: '%s', dlerror: %s\n", sym, lasterr);
            }
            else
            {
                good_count += 1;
            }
        }
        printf("SYMBOLS: good / bad / total --- %d / %d / %d\n", good_count, bad_count, idx);
    }

    if (shlib_ssl != NULL)
    {
        printf("INFO: loaded library: '%s'\n", shlib_ssl_path);
        int idx = 0;
        int bad_count = 0;
        int good_count = 0;
        for (;;++idx)
        {
            const char* sym = SSL_EXPORT_TABLE[idx];
            if (sym == NULL)
                break;

            void* code = dlsym(shlib_ssl, sym);
            if (code == NULL)
            {
                bad_count += 1;
                const char* lasterr = dlerror();
                if (lasterr == NULL)
                     lasterr = NULL_PTR_STR;
                printf("    BAD SYMBOL: '%s', dlerror: %s\n", sym, lasterr);
            }
            else
            {
                good_count += 1;
            }
        }
        printf("SYMBOLS: good / bad / total --- %d / %d / %d\n", good_count, bad_count, idx);
    }

exit:
  if (shlib_crypto != NULL)
    dlclose(shlib_crypto);

  if (shlib_ssl != NULL)
    dlclose(shlib_ssl);

  return retcode;
}
