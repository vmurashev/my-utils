#include "crypto_export_table.h"
#include "ssl_export_table.h"
#include <stdio.h>
#include <string.h>
#include <minicmn/shlib.h>

int main(int argc, char** argv)
{
    int retcode = 126;
    minicmn_Error* err = NULL;
    const char* shlib_crypto_path = NULL;
    const char* shlib_ssl_path = NULL;
    minicmn_SharedLibrary* shlib_crypto = NULL;
    minicmn_SharedLibrary* shlib_ssl = NULL;
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
        printf("ERROR: 'crypto' shlib path is not given as first arument of command line.\n");
        goto exit;
    }
    if (!shlib_ssl_path || !shlib_ssl_path[0])
    {
        printf("ERROR: 'ssl' shlib path is not given as second arument of command line.\n");
        goto exit;
    }

    int verify_crypto = (strcmp(shlib_crypto_path, "-") != 0);
    int verify_ssl = (strcmp(shlib_ssl_path, "-") != 0);

    if (!verify_crypto && !verify_ssl)
    {
        printf("ERROR: Nothing to verify.\n");
        goto exit;
    }

    if (verify_crypto)
    {
        if (minicmn_LoadLibrary(shlib_crypto_path, &shlib_crypto, &err) != 0)
        {
            printf("ERROR: cannot load library: '%s'\n", shlib_crypto_path);
            goto exit;
        }
    }

    if (verify_ssl)
    {
        if (minicmn_LoadLibrary(shlib_ssl_path, &shlib_ssl, &err) != 0)
        {
            printf("ERROR: cannot load library: '%s'\n", shlib_ssl_path);
            goto exit;
        }
    }

    int total_failures_count = 0;

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

            void* code = minicmn_GetProcAddress(shlib_crypto, sym);
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

            void* code = minicmn_GetProcAddress(shlib_ssl, sym);
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

    if ((err == NULL) && (total_failures_count == 0))
        retcode = 0;
    else
        retcode = 1;

exit:
    if (err != NULL)
    {
        printf("ERROR: %s\n", err->ErrorText);
        minicmn_DataFree(err);
    }
    minicmn_DataFree(shlib_crypto);
    minicmn_DataFree(shlib_ssl);
    return retcode;
}
