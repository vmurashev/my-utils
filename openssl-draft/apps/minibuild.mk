module_type = 'executable'
module_name = 'openssl'

src_search_dir_list = [
  '../../vendor/apps',
]

include_dir_list = [
  '../../include',
  '../../vendor/include',
  '../../vendor',
]

lib_list = [
  '../ssl_static',
  '../crypto_static',
  '../../../zlib',
]

build_list = [
    'app_rand.c',
    'apps.c',
    'asn1pars.c',
    'bf_prefix.c',
    'ca.c',
    'ciphers.c',
    'cms.c',
    'crl.c',
    'crl2p7.c',
    'dgst.c',
    'dhparam.c',
    'dsa.c',
    'dsaparam.c',
    'ec.c',
    'ecparam.c',
    'enc.c',
    'engine.c',
    'errstr.c',
    'gendsa.c',
    'genpkey.c',
    'genrsa.c',
    'nseq.c',
    'ocsp.c',
    'openssl.c',
    'opt.c',
    'passwd.c',
    'pkcs12.c',
    'pkcs7.c',
    'pkcs8.c',
    'pkey.c',
    'pkeyparam.c',
    'pkeyutl.c',
    'prime.c',
    'rand.c',
    'rehash.c',
    'req.c',
    'rsa.c',
    'rsautl.c',
    's_cb.c',
    's_client.c',
    's_server.c',
    's_socket.c',
    's_time.c',
    'sess_id.c',
    'smime.c',
    'speed.c',
    'spkac.c',
    'srp.c',
    'storeutl.c',
    'ts.c',
    'verify.c',
    'version.c',
    'x509.c',
]

build_list_windows = [
     'win32_init.c'
]

definitions = ['MONOLITH']
definitions_windows = ['WIN32_LEAN_AND_MEAN']
win_console = 1

prebuilt_lib_list_linux = ['dl','pthread']
prebuilt_lib_list_windows = ['crypt32','ws2_32', 'advapi32', 'user32']

if BUILDSYS_TOOLSET_NAME == 'msvs':
    disabled_warnings = ['4090']
