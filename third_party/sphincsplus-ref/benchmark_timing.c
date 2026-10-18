/*
 * benchmark_timing.c -- same-machine timing for the SPHINCS+ reference
 * implementation (FIPS 205 parameter sets), used as the standardized
 * baseline in Table 7 of the JCE revision.
 *
 * Built by run_sphincs_benchmark.py with -DPARAMS=... ; deterministic
 * seed and message; times keypair / sign / verify with CLOCK_MONOTONIC.
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "api.h"
#include "params.h"
#include "randombytes.h"

#ifndef ROUNDS
#define ROUNDS 100
#endif

static double now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e3 + (double)ts.tv_nsec / 1e6;
}

int main(void) {
    unsigned char pk[CRYPTO_PUBLICKEYBYTES];
    unsigned char sk[CRYPTO_SECRETKEYBYTES];
    unsigned char sm[CRYPTO_BYTES + 64];
    unsigned char m[64];
    unsigned char m2[64];
    unsigned char seed[CRYPTO_SEEDBYTES];
    unsigned long long smlen, mlen;
    int i, r;
    double t0, t1;
    double keygen_ms, sign_ms, open_ms;

    for (i = 0; i < (int)sizeof(seed); i++) seed[i] = (unsigned char)(i * 7 + 3);
    for (i = 0; i < (int)sizeof(m); i++) m[i] = (unsigned char)(i * 13 + 1);

    /* warm-up */
    crypto_sign_seed_keypair(pk, sk, seed);
    crypto_sign(sm, &smlen, m, sizeof(m), sk);
    if (crypto_sign_open(m2, &mlen, sm, smlen, pk) != 0) {
        fprintf(stderr, "warmup verify failed\n");
        return 1;
    }

    printf("alg=%s\n", CRYPTO_ALGNAME);
    printf("pk_bytes=%u\n", CRYPTO_PUBLICKEYBYTES);
    printf("sk_bytes=%u\n", CRYPTO_SECRETKEYBYTES);
    printf("sig_bytes=%u\n", CRYPTO_BYTES);
    printf("rounds=%d\n", ROUNDS);

    for (r = 0; r < ROUNDS; r++) {
        t0 = now_ms();
        crypto_sign_seed_keypair(pk, sk, seed);
        t1 = now_ms();
        keygen_ms = t1 - t0;

        t0 = now_ms();
        crypto_sign(sm, &smlen, m, sizeof(m), sk);
        t1 = now_ms();
        sign_ms = t1 - t0;

        t0 = now_ms();
        if (crypto_sign_open(m2, &mlen, sm, smlen, pk) != 0) {
            fprintf(stderr, "verify failed at round %d\n", r);
            return 1;
        }
        t1 = now_ms();
        open_ms = t1 - t0;

        printf("keygen_ms=%.6f sign_ms=%.6f verify_ms=%.6f\n",
               keygen_ms, sign_ms, open_ms);
    }
    return 0;
}
