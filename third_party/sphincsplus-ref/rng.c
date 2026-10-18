/* Minimal rng.c replacement: /dev/urandom + SHA-256 counter expander. */
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "rng.h"
#include "sha2.h"

int randombytes(unsigned char *x, unsigned long long xlen) {
    FILE *f = fopen("/dev/urandom", "rb");
    if (!f) return -1;
    size_t n = fread(x, 1, xlen, f);
    fclose(f);
    return (n == xlen) ? 0 : -1;
}

int seedexpander_init(AES_XOF_struct *ctx, const unsigned char *seed,
                      const unsigned char *div, unsigned long maxlen) {
    memset(ctx, 0, sizeof(*ctx));
    memcpy(ctx->key, seed, 32);
    memcpy(ctx->ctr, div, 8);
    ctx->length_remaining = maxlen;
    return 0;
}

int seedexpander(AES_XOF_struct *ctx, unsigned char *x, unsigned long xlen) {
    unsigned char block[32];
    uint32_t ctr = 0;
    while (xlen > 0) {
        unsigned char buf[40];
        memcpy(buf, ctx->key, 32);
        memcpy(buf + 32, ctx->ctr, 8);
        buf[39] = (unsigned char)(ctr >> 24);
        buf[38] = (unsigned char)(ctr >> 16);
        buf[37] = (unsigned char)(ctr >> 8);
        buf[36] = (unsigned char)(ctr);
        ctr++;
        sha256(block, buf, 40);
        unsigned long chunk = xlen < 32 ? xlen : 32;
        memcpy(x, block, chunk);
        x += chunk;
        xlen -= chunk;
    }
    return 0;
}
void randombytes_init(unsigned char *e, unsigned char *p) {}
