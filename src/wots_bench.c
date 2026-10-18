/*
 * WOTS+ microbenchmark in C (CommonCrypto SHA-256).
 *
 * Mirrors wots.py: n=32, w=16, len1=64, len2=3, len=67.
 * Measures keygen / sign / verify latency.
 */
#include <CommonCrypto/CommonDigest.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define N 32
#define W 16
#define LEN1 64
#define LEN2 3
#define LEN (LEN1 + LEN2)  /* 67 */

static void hash(const uint8_t *in, size_t inlen, uint8_t out[N]) {
    CC_SHA256_CTX c;
    CC_SHA256_Init(&c);
    CC_SHA256_Update(&c, "WOTS-CHAIN", 10);
    CC_SHA256_Update(&c, in, inlen);
    CC_SHA256_Final(out, &c);
}

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* base_w: split bytes into base-W digits, LEN1 digits */
static void base_w(const uint8_t *data, int out_len, int *digits) {
    int in_pos = 0, in_bits = 0, total = 0;
    for (int i = 0; i < out_len; i++) {
        while (in_bits < 4) {
            total = (total << 8) | data[in_pos++];
            in_bits += 8;
        }
        in_bits -= 4;
        digits[i] = (total >> in_bits) & (W - 1);
        total &= (1 << in_bits) - 1;
    }
}

/* chain: apply hash `steps` times starting at offset `start` */
static void chain(const uint8_t *x, int start, int steps, uint8_t *out) {
    uint8_t tmp[N];
    memcpy(tmp, x, N);
    for (int i = start; i < start + steps; i++) {
        hash(tmp, N, tmp);
    }
    memcpy(out, tmp, N);
}

int main(void) {
    /* Secret and public arrays */
    uint8_t sk[LEN][N], pk[LEN][N];
    uint8_t msg[] = "C microbenchmark message";
    uint8_t digest[N];
    CC_SHA256(msg, strlen((char *)msg), digest);

    int digits[LEN];

    /* ---- Keygen ---- */
    double t0 = now_sec();
    for (int rep = 0; rep < 100; rep++) {
        for (int i = 0; i < LEN; i++) {
            /* Use deterministic pseudo-random for reproducibility */
            for (int j = 0; j < N; j++) sk[i][j] = (uint8_t)(i * 31 + j * 7 + rep);
            chain(sk[i], 0, W - 1, pk[i]);
        }
    }
    double t1 = now_sec();
    printf("keygen per op: %.3f ms\n", (t1 - t0) / 100 * 1000);

    /* ---- Sign ---- */
    int md[LEN1], cd[LEN2];
    base_w(digest, LEN1, md);
    int cksum = 0;
    for (int i = 0; i < LEN1; i++) cksum += W - 1 - md[i];
    /* simple cksum to bytes */
    uint8_t cksum_bytes[N] = {0};
    cksum_bytes[N-1] = cksum & 0xff;
    base_w(cksum_bytes, LEN2, cd);
    for (int i = 0; i < LEN1; i++) digits[i] = md[i];
    for (int i = 0; i < LEN2; i++) digits[LEN1 + i] = cd[i];

    uint8_t sig[LEN][N];
    t0 = now_sec();
    for (int rep = 0; rep < 100; rep++) {
        for (int i = 0; i < LEN; i++) {
            chain(sk[i], 0, digits[i], sig[i]);
        }
    }
    t1 = now_sec();
    printf("sign per op:   %.3f ms\n", (t1 - t0) / 100 * 1000);

    /* ---- Verify ---- */
    t0 = now_sec();
    int ok = 1;
    for (int rep = 0; rep < 100; rep++) {
        for (int i = 0; i < LEN; i++) {
            uint8_t computed[N];
            chain(sig[i], digits[i], W - 1 - digits[i], computed);
            if (memcmp(computed, pk[i], N) != 0) ok = 0;
        }
    }
    t1 = now_sec();
    printf("verify per op: %.3f ms (%s)\n",
           (t1 - t0) / 100 * 1000, ok ? "OK" : "FAIL");

    printf("\nsizes: sk=%d B, pk=%d B, sig=%d B\n",
           LEN * N, LEN * N, LEN * N);
    return 0;
}
