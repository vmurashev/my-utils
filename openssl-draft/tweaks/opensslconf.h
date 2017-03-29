#if defined(__MINGW32__)
#  if defined(_WIN64)
#    include "opensslconf_mingw64.h"
#  else
#    include "opensslconf_mingw32.h"
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
