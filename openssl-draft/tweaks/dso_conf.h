#pragma once

#ifdef _WIN32
#  define DSO_EXTENSION ".dll"
#else
#  define DSO_EXTENSION ".so"
#endif
