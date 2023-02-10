#ifndef FATSTD
#define FATSTD

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdlib.h>

typedef int32_t i32_H3513744743;
typedef uint32_t ui32_H303069193;
typedef int64_t i64_H1943915801;
typedef uint64_t ui64_H298652222;
typedef size_t usize_H1664078523;
typedef void void_H4184162244;
typedef float f32_H1412933138;
typedef double f64_H1422766186;
typedef char char_H2392350458;
typedef bool bool_H2867760811;

#define i32 int32_t
#define ui32 uint32_t
#define i64 int64_t
#define ui64 uint64_t
#define usize size_t
#define f32 float
#define f64 double

static inline i32 __ext_add_i32(i32 x, i32 y) { return x + y; }
static inline i32 __ext_sub_i32(i32 x, i32 y) { return x - y; }
static inline i32 __ext_mul_i32(i32 x, i32 y) { return x * y; }
static inline i32 __ext_div_i32(i32 x, i32 y) { return x / y; }
static inline i32 __ext_and_i32(i32 x, i32 y) { return x & y; }
static inline i32 __ext_or_i32(i32 x, i32 y) { return x | y; }
static inline i32 __ext_xor_i32(i32 x, i32 y) { return x ^ y; }
static inline i32 __ext_mod_i32(i32 x, i32 y) { return x % y; }
static inline i32 __ext_lshift_i32(i32 x, i32 y) { return x << y; }
static inline i32 __ext_rshift_i32(i32 x, i32 y) { return x >> y; }
static inline bool __ext_less_i32(i32 x, i32 y) { return x < y; }
static inline bool __ext_less_eq_i32(i32 x, i32 y) { return x <= y; }
static inline bool __ext_greater_i32(i32 x, i32 y) { return x > y; }
static inline bool __ext_greater_eq_i32(i32 x, i32 y) { return x >= y; }
static inline bool __ext_eq_i32(i32 x, i32 y) { return x == y; }
static inline bool __ext_not_eq_i32(i32 x, i32 y) { return x != y; }

static inline ui32 __ext_add_ui32(ui32 x, ui32 y) { return x + y; }
static inline ui32 __ext_sub_ui32(ui32 x, ui32 y) { return x - y; }
static inline ui32 __ext_mul_ui32(ui32 x, ui32 y) { return x * y; }
static inline ui32 __ext_div_ui32(ui32 x, ui32 y) { return x / y; }
static inline ui32 __ext_and_ui32(ui32 x, ui32 y) { return x & y; }
static inline ui32 __ext_or_ui32(ui32 x, ui32 y) { return x | y; }
static inline ui32 __ext_xor_ui32(ui32 x, ui32 y) { return x ^ y; }
static inline ui32 __ext_mod_ui32(ui32 x, ui32 y) { return x % y; }
static inline ui32 __ext_lshift_ui32(ui32 x, ui32 y) { return x << y; }
static inline ui32 __ext_rshift_ui32(ui32 x, ui32 y) { return x >> y; }
static inline bool __ext_less_ui32(ui32 x, ui32 y) { return x < y; }
static inline bool __ext_less_eq_ui32(ui32 x, ui32 y) { return x <= y; }
static inline bool __ext_greater_ui32(ui32 x, ui32 y) { return x > y; }
static inline bool __ext_greater_eq_ui32(ui32 x, ui32 y) { return x >= y; }
static inline bool __ext_eq_ui32(ui32 x, ui32 y) { return x == y; }
static inline bool __ext_not_eq_ui32(ui32 x, ui32 y) { return x != y; }

static inline i64 __ext_add_i64(i64 x, i64 y) { return x + y; }
static inline i64 __ext_sub_i64(i64 x, i64 y) { return x - y; }
static inline i64 __ext_mul_i64(i64 x, i64 y) { return x * y; }
static inline i64 __ext_div_i64(i64 x, i64 y) { return x / y; }
static inline i64 __ext_and_i64(i64 x, i64 y) { return x & y; }
static inline i64 __ext_or_i64(i64 x, i64 y) { return x | y; }
static inline i64 __ext_xor_i64(i64 x, i64 y) { return x ^ y; }
static inline i64 __ext_mod_i64(i64 x, i64 y) { return x % y; }
static inline i64 __ext_lshift_i64(i64 x, i64 y) { return x << y; }
static inline i64 __ext_rshift_i64(i64 x, i64 y) { return x >> y; }
static inline bool __ext_less_i64(i64 x, i64 y) { return x < y; }
static inline bool __ext_less_eq_i64(i64 x, i64 y) { return x <= y; }
static inline bool __ext_greater_i64(i64 x, i64 y) { return x > y; }
static inline bool __ext_greater_eq_i64(i64 x, i64 y) { return x >= y; }
static inline bool __ext_eq_i64(i64 x, i64 y) { return x == y; }
static inline bool __ext_not_eq_i64(i64 x, i64 y) { return x != y; }

static inline ui64 __ext_add_ui64(ui64 x, ui64 y) { return x + y; }
static inline ui64 __ext_sub_ui64(ui64 x, ui64 y) { return x - y; }
static inline ui64 __ext_mul_ui64(ui64 x, ui64 y) { return x * y; }
static inline ui64 __ext_div_ui64(ui64 x, ui64 y) { return x / y; }
static inline ui64 __ext_and_ui64(ui64 x, ui64 y) { return x & y; }
static inline ui64 __ext_or_ui64(ui64 x, ui64 y) { return x | y; }
static inline ui64 __ext_xor_ui64(ui64 x, ui64 y) { return x ^ y; }
static inline ui64 __ext_mod_ui64(ui64 x, ui64 y) { return x % y; }
static inline ui64 __ext_lshift_ui64(ui64 x, ui64 y) { return x << y; }
static inline ui64 __ext_rshift_ui64(ui64 x, ui64 y) { return x >> y; }
static inline bool __ext_less_ui64(ui64 x, ui64 y) { return x < y; }
static inline bool __ext_less_eq_ui64(ui64 x, ui64 y) { return x <= y; }
static inline bool __ext_greater_ui64(ui64 x, ui64 y) { return x > y; }
static inline bool __ext_greater_eq_ui64(ui64 x, ui64 y) { return x >= y; }
static inline bool __ext_eq_ui64(ui64 x, ui64 y) { return x == y; }
static inline bool __ext_not_eq_ui64(ui64 x, ui64 y) { return x != y; }


static inline usize __ext_add_usize(usize x, usize y) { return x + y; }
static inline usize __ext_sub_usize(usize x, usize y) { return x - y; }
static inline usize __ext_mul_usize(usize x, usize y) { return x * y; }
static inline usize __ext_div_usize(usize x, usize y) { return x / y; }
static inline usize __ext_and_usize(usize x, usize y) { return x & y; }
static inline usize __ext_or_usize(usize x, usize y) { return x | y; }
static inline usize __ext_xor_usize(usize x, usize y) { return x ^ y; }
static inline usize __ext_mod_usize(usize x, usize y) { return x % y; }
static inline usize __ext_lshift_usize(usize x, usize y) { return x << y; }
static inline usize __ext_rshift_usize(usize x, usize y) { return x >> y; }
static inline bool __ext_less_usize(usize x, usize y) { return x < y; }
static inline bool __ext_less_eq_usize(usize x, usize y) { return x <= y; }
static inline bool __ext_greater_usize(usize x, usize y) { return x > y; }
static inline bool __ext_greater_eq_usize(usize x, usize y) { return x >= y; }
static inline bool __ext_eq_usize(usize x, usize y) { return x == y; }
static inline bool __ext_not_eq_usize(usize x, usize y) { return x != y; }

static inline usize __ext_and_bool(bool x, bool y) { return x && y; }
static inline usize __ext_or_bool(bool x, bool y) { return x || y; }
static inline bool __ext_eq_bool(bool x, bool y) { return x == y; }
static inline bool __ext_not_eq_bool(bool x, bool y) { return x != y; }
static inline bool __ext_not_bool(bool x) { return !x; }

static inline i32 __ext_unary_minus_i32(i32 x) { return -x; }
static inline i64 __ext_unary_minus_i64(i64 x) { return -x; }
static inline f32 __ext_unary_minus_f32(f32 x) { return -x; }
static inline f64 __ext_unary_minus_f64(f64 x) { return -x; }


static inline ui32 __ext_cast_i32_ui32(i32 v) { return (ui32)v; }
static inline i64 __ext_cast_i32_i64(i32 v) { return (i64)v; }
static inline ui64 __ext_cast_i32_ui64(i32 v) { return (ui64)v; }
static inline usize __ext_cast_i32_usize(i32 v) { return (usize)v; }
static inline f32 __ext_cast_i32_f32(i32 v) { return (f32)v; }
static inline f64 __ext_cast_i32_f64(i32 v) { return (f64)v; }

static inline i32 __ext_cast_ui32_i32(ui32 v) { return (i32)v; }
static inline i64 __ext_cast_ui32_i64(ui32 v) { return (i64)v; }
static inline ui64 __ext_cast_ui32_ui64(ui32 v) { return (ui64)v; }
static inline usize __ext_cast_ui32_usize(ui32 v) { return (usize)v; }
static inline f32 __ext_cast_ui32_f32(ui32 v) { return (f32)v; }
static inline f64 __ext_cast_ui32_f64(ui32 v) { return (f64)v; }

static inline i32 __ext_cast_i64_i32(i64 v) { return (i32)v; }
static inline ui32 __ext_cast_i64_ui32(i64 v) { return (ui32)v; }
static inline ui64 __ext_cast_i64_ui64(i64 v) { return (ui64)v; }
static inline usize __ext_cast_i64_usize(i64 v) { return (usize)v; }
static inline f32 __ext_cast_i64_f32(i64 v) { return (f32)v; }
static inline f64 __ext_cast_i64_f64(i64 v) { return (f64)v; }

static inline i32 __ext_cast_ui64_i32(ui64 v) { return (i32)v; }
static inline ui32 __ext_cast_ui64_ui32(ui64 v) { return (ui32)v; }
static inline i64 __ext_cast_ui64_i64(ui64 v) { return (i64)v; }
static inline usize __ext_cast_ui64_usize(ui64 v) { return (usize)v; }
static inline f32 __ext_cast_ui64_f32(ui64 v) { return (f32)v; }
static inline f64 __ext_cast_ui64_f64(ui64 v) { return (f64)v; }

static inline i32 __ext_cast_usize_i32(usize v) { return (i32)v; }
static inline ui32 __ext_cast_usize_ui32(usize v) { return (ui32)v; }
static inline i64 __ext_cast_usize_i64(usize v) { return (i64)v; }
static inline ui64 __ext_cast_usize_ui64(usize v) { return (ui64)v; }
static inline f32 __ext_cast_usize_f32(usize v) { return (f32)v; }
static inline f64 __ext_cast_usize_f64(usize v) { return (f64)v; }

static inline f64 __ext_cast_f32_f64(f32 v) { return (f64)v; }
static inline i32 __ext_cast_f32_i32(f32 v) { return (i32)v; }
static inline ui32 __ext_cast_f32_ui32(f32 v) { return (ui32)v; }
static inline i64 __ext_cast_f32_i64(f32 v) { return (i64)v; }
static inline ui64 __ext_cast_f32_ui64(f32 v) { return (ui64)v; }
static inline usize __ext_cast_f32_usize(f32 v) { return (usize)v; }

static inline f32 __ext_cast_f64_f32(f64 v) { return (f32)v; }
static inline i32 __ext_cast_f64_i32(f64 v) { return (i32)v; }
static inline ui32 __ext_cast_f64_ui32(f64 v) { return (ui32)v; }
static inline i64 __ext_cast_f64_i64(f64 v) { return (i64)v; }
static inline ui64 __ext_cast_f64_ui64(f64 v) { return (ui64)v; }
static inline usize __ext_cast_f64_usize(f64 v) { return (usize)v; }

static inline void __ext_exit(i32 code) {
    exit(code);
}

#endif
