/* bench_std.c — uniform timing harness for a single PQClean scheme.
 * Compile one executable per scheme so each links its own copy of
 * PQClean/common (no duplicate-symbol conflicts). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "bench.h"

#define REPS 31

static double now_us(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e6 + (double)ts.tv_nsec / 1e3;
}

static int cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

/* Matches the linear-interpolation IQR used in experiment_v2.py. */
static double quantile(const double *v, int n, double p) {
    double idx = p * (n - 1);
    int lo = (int)idx;
    int hi = (lo + 1 < n) ? lo + 1 : n - 1;
    double f = idx - lo;
    return v[lo] + f * (v[hi] - v[lo]);
}

static double median(const double *v, int n) { return quantile(v, n, 0.5); }
static double iqr(const double *v, int n) {
    return quantile(v, n, 0.75) - quantile(v, n, 0.25);
}

int main(void) {
    size_t pkb = bench_pkbytes(), skb = bench_skbytes(), sigb = bench_sigbytes();
    uint8_t *pk = malloc(pkb), *sk = malloc(skb), *sig = malloc(sigb);
    if (!pk || !sk || !sig) { fprintf(stderr, "alloc failed\n"); return 2; }

    uint8_t msg[64];
    for (int i = 0; i < 64; i++) msg[i] = (uint8_t)(i * 7 + 3);

    double kg[REPS], sg[REPS], vf[REPS];
    size_t sl = 0;
    int fail = 0;

    /* warm-up (3 iterations, discarded) */
    for (int i = 0; i < 3; i++) {
        if (bench_keypair(pk, sk)) { fprintf(stderr, "keypair fail\n"); return 3; }
        if (bench_sign(sig, &sl, msg, sizeof msg, sk)) { fprintf(stderr, "sign fail\n"); return 3; }
        if (bench_verify(sig, sl, msg, sizeof msg, pk)) { fprintf(stderr, "verify fail\n"); return 3; }
    }

    for (int i = 0; i < REPS; i++) {
        double t = now_us();
        if (bench_keypair(pk, sk)) { fprintf(stderr, "keypair fail\n"); return 3; }
        kg[i] = now_us() - t;
    }
    for (int i = 0; i < REPS; i++) {
        double t = now_us();
        if (bench_sign(sig, &sl, msg, sizeof msg, sk)) { fprintf(stderr, "sign fail\n"); return 3; }
        sg[i] = now_us() - t;
    }
    for (int i = 0; i < REPS; i++) {
        double t = now_us();
        if (bench_verify(sig, sl, msg, sizeof msg, pk)) { fail = 1; }
        vf[i] = now_us() - t;
    }

    qsort(kg, REPS, sizeof(double), cmp_d);
    qsort(sg, REPS, sizeof(double), cmp_d);
    qsort(vf, REPS, sizeof(double), cmp_d);

    printf("{\"scheme\":\"%s\",\"pk\":%zu,\"sk\":%zu,\"sig\":%zu,"
           "\"keygen_ms\":%.4f,\"keygen_iqr\":%.4f,"
           "\"sign_ms\":%.4f,\"sign_iqr\":%.4f,"
           "\"verify_ms\":%.4f,\"verify_iqr\":%.4f,\"verify_ok\":%d}\n",
           bench_name(), pkb, skb, sigb,
           median(kg, REPS) / 1000.0, iqr(kg, REPS) / 1000.0,
           median(sg, REPS) / 1000.0, iqr(sg, REPS) / 1000.0,
           median(vf, REPS) / 1000.0, iqr(vf, REPS) / 1000.0,
           fail ? 0 : 1);

    free(pk); free(sk); free(sig);
    return fail ? 4 : 0;
}
