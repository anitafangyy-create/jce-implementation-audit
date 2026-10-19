#include "api.h"
#include "bench.h"

const char *bench_name(void) { return "ML-DSA-65"; }
size_t bench_pkbytes(void) { return PQCLEAN_MLDSA65_CLEAN_CRYPTO_PUBLICKEYBYTES; }
size_t bench_skbytes(void) { return PQCLEAN_MLDSA65_CLEAN_CRYPTO_SECRETKEYBYTES; }
size_t bench_sigbytes(void) { return PQCLEAN_MLDSA65_CLEAN_CRYPTO_BYTES; }
int bench_keypair(uint8_t *pk, uint8_t *sk) {
    return PQCLEAN_MLDSA65_CLEAN_crypto_sign_keypair(pk, sk);
}
int bench_sign(uint8_t *sig, size_t *sl, const uint8_t *m, size_t ml,
               const uint8_t *sk) {
    return PQCLEAN_MLDSA65_CLEAN_crypto_sign_signature(sig, sl, m, ml, sk);
}
int bench_verify(const uint8_t *sig, size_t sl, const uint8_t *m, size_t ml,
                 const uint8_t *pk) {
    return PQCLEAN_MLDSA65_CLEAN_crypto_sign_verify(sig, sl, m, ml, pk);
}
