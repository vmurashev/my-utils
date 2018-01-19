ABI_ALL='mingw,mingw64,x86,x86_64,arm,arm64'
ZLIB_URL='http://zlib.net/zlib-1.2.11.tar.gz'
OPENSSL_URL='https://www.openssl.org/source/openssl-1.1.0g.tar.gz'
OPENSSL_OPTIONS='shared zlib-dynamic disable-dynamic-engine --api=1.0.0'
OPENSSL_USELESS_FILES='m_md2.c e_rc5.c rsa_depr.c rand_egd.c ecp_nistputil.c ecp_nistp521.c ecp_nistp256.c ecp_nistp224.c ebcdic.c e_old.c dsa_depr.c dh_depr.c bn_depr.c async_null.c dso_vms.c rand_vms.c threads_none.c'
OPENSSL_POSIX_FILES='async_posix.c dso_dlfcn.c rand_unix.c threads_pthread.c'
OPENSSL_WINDOWS_FILES='async_win.c dso_win32.c rand_win.c threads_win.c'

MSVS_LANDMARK='VS140COMNTOOLS'
CURL_FOR_WINDOWS='C:\\Git\\usr\\bin\\curl.exe'
TAR_FOR_WINDOWS='C:\\Git\\usr\\bin\\tar.exe'
PERL_FOR_WINDOWS='C:\\Perl64\\bin\\perl.exe'
NASM_DIR='C:\\NASM'
