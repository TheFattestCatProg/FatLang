#ifndef FATSTDIO
#define FATSTDIO

#include <stdio.h>
#include <string.h>
#include "std.h"


static inline void __ext_print_char(char v) { printf("%c", v); }
static inline void __ext_println_char(char v) { printf("%c\n", v); }

static inline void __ext_print_i32(i32 v) { printf("%d", v); }
static inline void __ext_println_i32(i32 v) { printf("%d\n", v); }
static inline void __ext_print_ui32(ui32 v) { printf("%u", v); }
static inline void __ext_println_ui32(ui32 v) { printf("%u\n", v); }
static inline void __ext_print_i64(i64 v) { printf("%ld", v); }
static inline void __ext_println_i64(i64 v) { printf("%ld\n", v); }
static inline void __ext_print_ui64(ui64 v) { printf("%lu", v); }
static inline void __ext_println_ui64(ui64 v) { printf("%lu\n", v); }

static inline void __ext_print_f32(f32 v) { printf("%f", v); }
static inline void __ext_println_f32(f32 v) { printf("%f\n", v); }
static inline void __ext_print_f64(f64 v) { printf("%lf", v); }
static inline void __ext_println_f64(f64 v) { printf("%lf\n", v); }



struct __c_char_arr {
    void* ptr;
    usize len;
};

static inline void __ext_print_char_arr(struct __c_char_arr chars) {
    printf("%s", (char*)chars.ptr);
}
static inline void __ext_println_char_arr(struct __c_char_arr chars) {
    printf("%s\n", (char*)chars.ptr);
}

inline static i32 __ext_input_i32() { i32 i; scanf("%d", &i); return i; }
inline static ui32 __ext_input_ui32() { ui32 i; scanf("%u", &i); return i; }
inline static i64 __ext_input_i64() { i64 i; scanf("%ld", &i); return i; }
inline static ui64 __ext_input_ui64() { ui64 i; scanf("%lu", &i); return i; }
inline static f32 __ext_input_f32() { f32 i; scanf("%f", &i); return i; }
inline static f64 __ext_input_f64() { f64 i; scanf("%lf", &i); return i; }
inline static char __ext_input_char() { char i; scanf("%c", &i); return i; }
static struct __c_char_arr __ext_input_string() { char* i; scanf("%m[^\n]%*c", &i); return (struct __c_char_arr){(void*)i, strlen(i)+1}; }

#endif
