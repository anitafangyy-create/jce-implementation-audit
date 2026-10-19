#ifndef BENCH_H
#define BENCH_H
#include <stddef.h>
#include <stdint.h>

const char *bench_name(void);
size_t bench_pkbytes(void);
size_t bench_skbytes(void);
size_t bench_sigbytes(void);
int bench_keypair(uint8_t *pk, uint8_t *sk);
int bench_sign(uint8_t *sig, size_t *siglen, const uint8_t *m, size_t mlen,
               const uint8_t *sk);
int bench_verify(const uint8_t *sig, size_t siglen, const uint8_t *m,
                 size_t mlen, const uint8_t *pk);
#endif
