#if defined(_WIN32)
#  if defined(_WIN64)
#    if defined(_MSC_VER)
#      include "opensslconf_msvs64.h"
#    else
#      include "opensslconf_mingw64.h"
#    endif
#  else
#    if defined(_MSC_VER)
#      include "opensslconf_msvs32.h"
#    else
#      include "opensslconf_mingw32.h"
#    endif
#  endif
#elif defined(__linux__)
#  if defined(__x86_64__)
#    include "opensslconf_x86_64.h"
#  elif defined(__i386__)
#    include "opensslconf_x86.h"
#  elif defined(__arm__)
#    include "opensslconf_arm.h"
#  elif defined(__aarch64__)
#    include "opensslconf_arm64.h"
#  else
#    error "Unknown linux arch."
#  endif
#else
#  error "Unknown platform."
#endif
