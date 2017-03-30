#pragma once

#ifdef _LP64
#  undef SIXTY_FOUR_BIT
#  define SIXTY_FOUR_BIT_LONG
#  undef THIRTY_TWO_BIT
#elif defined(_WIN64) || __SIZEOF_POINTER__ == 8
#  define SIXTY_FOUR_BIT
#  undef SIXTY_FOUR_BIT_LONG
#  undef THIRTY_TWO_BIT
#else
#  undef SIXTY_FOUR_BIT
#  undef SIXTY_FOUR_BIT_LONG
#  define THIRTY_TWO_BIT
#endif
