#ifndef FATSTDMEM
#define FATSTDMEM

#include <stdlib.h>
#include "std.h"

static inline void __ext_free(void* ptr) { free(ptr); }
static inline usize __ext_cast_voidptr_usize(void* p) { return (size_t)p; }
static inline void* __ext_cast_usize_voidptr(usize addr) { return (void*)addr; }
static inline void* __ext_malloc(usize s) { return malloc(s); }

#endif