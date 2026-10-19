/* bench_proto.c — C port of the JCE *repaired research variant*.
 *
 * This file is a byte-for-byte structural mirror of
 * experiments/experiment_submission.py.  Earlier versions of this harness
 * measured a different construction (MSS-LEAF / MSS-NODE tags, random OTS
 * keys), which made the Python/C comparison a cross-implementation one.
 * The tags, key derivation, tree layout, serialization and verification
 * path below now match the Python implementation exactly:
 *
 *   H_message(m)      = SHA256("HBS-PQ-MSG-v1" || m)
 *   chain(x, s, n)    = n times x <- SHA256("WOTS-CHAIN" || x)
 *   leaf_seed(ts, i)  = H("SUB-LEAF" || ts || i_be16)
 *   sk[i]             = H("SUB-SK"   || leaf_seed || i_be16)
 *   leaf_hash(pk)     = H("UMT-LEAF" || 0x01 || pk[0] || ... || pk[66])
 *   node_hash(l, r)   = H("UMT-NODE" || l || r)
 *   pk  = "HBP1" || base_code || h || root                    (38 bytes)
 *   sig = "HBS1" || mode || base_code || h || idx(n_idx)
 *         || elements || [endpoints] || path
 *
 * Timing boundaries also match: key generation builds all 2^h one-time keys,
 * their leaves and the whole tree; signing reads the authentication path
 * from the precomputed layers (it does not rebuild the tree); verification
 * parses the serialized bytes and performs exactly one chain pass per
 * element in both modes.  The earlier harness rebuilt the tree inside the
 * signing loop and did the compact-mode chain work twice.
 *
 * Output: one JSON object per line (JSONL) on stdout.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>

#include "sha2.h"
#include "randombytes.h"

#define N       32
#define LEN1    64
#define LEN2    3
#define LEN     67
#define W       16
#define REPS    31
#define MAXH    8
#define PK_BYTES 38

static double now_us(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e6 + (double)ts.tv_nsec / 1e3;
}
static int cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}
static double quantile(const double *v, int n, double p) {
    double idx = p * (n - 1);
    int lo = (int)idx, hi = (lo + 1 < n) ? lo + 1 : n - 1;
    return v[lo] + (idx - lo) * (v[hi] - v[lo]);
}
static double median(const double *v, int n) { return quantile(v, n, 0.5); }
static double iqr(const double *v, int n) { return quantile(v, n, 0.75) - quantile(v, n, 0.25); }

/* ---- primitives ------------------------------------------------------- */
static uint8_t SCRATCH[8 + 1 + LEN * N];

static void H_msg(uint8_t out[N], const uint8_t *m, size_t ml) {
    memcpy(SCRATCH, "HBS-PQ-MSG-v1", 13);
    memcpy(SCRATCH + 13, m, ml);
    sha256(out, SCRATCH, 13 + ml);
}

static long chain_calls = 0;

static void chain(uint8_t *x, int start, int steps) {
    uint8_t buf[10 + N];
    memcpy(buf, "WOTS-CHAIN", 10);
    for (int i = start; i < start + steps; i++) {
        memcpy(buf + 10, x, N);
        sha256(x, buf, 10 + N);
        chain_calls++;
    }
}

static void base_w(const uint8_t *in, int out_len, uint8_t *digits) {
    int in_pos = 0, in_bits = 0, total = 0;
    for (int i = 0; i < out_len; i++) {
        while (in_bits < 4) {
            total = (total << 8) | in[in_pos++];
            in_bits += 8;
        }
        in_bits -= 4;
        digits[i] = (uint8_t)((total >> in_bits) & 15);
        total &= (1 << in_bits) - 1;
    }
}

/* d[0] = most significant base-16 digit, d[2] = least significant */
static void wots_checksum(int c, uint8_t *d) {
    d[0] = (uint8_t)(c / 256);
    d[1] = (uint8_t)((c / 16) % 16);
    d[2] = (uint8_t)(c % 16);
}

static void wots_digits(const uint8_t *m, size_t ml, uint8_t *digits) {
    uint8_t mu[N];
    H_msg(mu, m, ml);
    base_w(mu, LEN1, digits);
    int c = 0;
    for (int i = 0; i < LEN1; i++) c += 15 - digits[i];
    wots_checksum(c, digits + LEN1);
}

static void leaf_seed(const uint8_t ts[N], uint16_t idx, uint8_t out[N]) {
    memcpy(SCRATCH, "SUB-LEAF", 8);
    memcpy(SCRATCH + 8, ts, N);
    SCRATCH[8 + N] = (uint8_t)(idx >> 8);
    SCRATCH[8 + N + 1] = (uint8_t)(idx & 0xFF);
    sha256(out, SCRATCH, 8 + N + 2);
}

typedef struct { uint8_t sk[LEN][N]; uint8_t pk[LEN][N]; } WotsKey;

static void wots_key(const uint8_t ls[N], WotsKey *k) {
    uint8_t seed[N];
    for (int i = 0; i < LEN; i++) {
        memcpy(SCRATCH, "SUB-SK", 6);
        memcpy(SCRATCH + 6, ls, N);
        SCRATCH[6 + N] = (uint8_t)(i >> 8);
        SCRATCH[6 + N + 1] = (uint8_t)(i & 0xFF);
        sha256(seed, SCRATCH, 6 + N + 2);
        memcpy(k->sk[i], seed, N);
        memcpy(k->pk[i], seed, N);
        chain(k->pk[i], 0, W - 1);
    }
}

static void leaf_hash(uint8_t out[N], const uint8_t pk[LEN][N]) {
    memcpy(SCRATCH, "UMT-LEAF", 8);
    SCRATCH[8] = 0x01;                       /* LEAF_TAG_OTS */
    memcpy(SCRATCH + 9, pk, LEN * N);
    sha256(out, SCRATCH, 9 + LEN * N);
}

static void node_hash(uint8_t out[N], const uint8_t *l, const uint8_t *r) {
    memcpy(SCRATCH, "UMT-NODE", 8);
    memcpy(SCRATCH + 8, l, N);
    memcpy(SCRATCH + 8 + N, r, N);
    sha256(out, SCRATCH, 8 + 2 * N);
}

/* layers holds all levels back to back: n + n/2 + ... + 1 nodes */
static void build_tree(const uint8_t ts[N], int h, WotsKey *keys,
                       uint8_t *layers, int *off, uint8_t root[N]) {
    int n = 1 << h;
    off[0] = 0;
    for (int l = 0; l < h; l++) off[l + 1] = off[l] + (n >> l) * N;  /* byte offsets */

    for (int i = 0; i < n; i++) {
        uint8_t ls[N];
        leaf_seed(ts, (uint16_t)i, ls);
        wots_key(ls, &keys[i]);
        leaf_hash(layers + off[0] + (size_t)i * N, keys[i].pk);
    }
    for (int l = 0; l < h; l++) {
        int m = n >> l;
        for (int i = 0; i < m / 2; i++)
            node_hash(layers + off[l + 1] + (size_t)i * N,
                      layers + off[l] + (size_t)(2 * i) * N,
                      layers + off[l] + (size_t)(2 * i + 1) * N);
    }
    memcpy(root, layers + off[h], N);
}

static void write_u16(uint8_t *p, unsigned v) { p[0] = (uint8_t)(v >> 8); p[1] = (uint8_t)v; }

/* ---- WOTS sign / verify ------------------------------------------------ */
static void wots_sign(const WotsKey *k, const uint8_t *m, size_t ml,
                      uint8_t sig[LEN][N]) {
    uint8_t d[LEN];
    wots_digits(m, ml, d);
    for (int i = 0; i < LEN; i++) {
        memcpy(sig[i], k->sk[i], N);
        chain(sig[i], 0, d[i]);
    }
}

/* Recover the public endpoints from (message, signature elements). */
static void wots_recover(const uint8_t sig[LEN][N], const uint8_t *m, size_t ml,
                         uint8_t pk[LEN][N]) {
    uint8_t d[LEN];
    wots_digits(m, ml, d);
    for (int i = 0; i < LEN; i++) {
        memcpy(pk[i], sig[i], N);
        chain(pk[i], d[i], W - 1 - d[i]);
    }
}

static int merkle_root(const uint8_t leaf[N], int idx, const uint8_t *path,
                       int h, const uint8_t root[N]) {
    uint8_t cur[N], nxt[N];
    memcpy(cur, leaf, N);
    for (int l = 0; l < h; l++) {
        const uint8_t *sib = path + (size_t)l * N;
        if ((idx >> l) & 1) node_hash(nxt, sib, cur);
        else                node_hash(nxt, cur, sib);
        memcpy(cur, nxt, N);
    }
    return memcmp(cur, root, N) != 0;
}

/* ---- serialized interface --------------------------------------------- */
static size_t pack_pk(uint8_t *out, int h, const uint8_t root[N]) {
    memcpy(out, "HBP1", 4);
    out[4] = 1;              /* base code for w = 16 */
    out[5] = (uint8_t)h;
    memcpy(out + 6, root, N);
    return PK_BYTES;
}

static size_t pack_sig(uint8_t *out, int h, int idx, int mode,
                       const uint8_t sig[LEN][N], const uint8_t eps[LEN][N],
                       const uint8_t *path) {
    int n_idx = (h + 7) / 8;
    uint8_t *p = out;
    memcpy(p, "HBS1", 4); p += 4;
    *p++ = (uint8_t)mode;
    *p++ = 1;                                   /* base code */
    *p++ = (uint8_t)h;
    if (n_idx == 1) {
        *p++ = (uint8_t)idx;
    } else {
        write_u16(p, (unsigned)idx); p += 2;
    }
    memcpy(p, sig, LEN * N); p += LEN * N;
    if (mode == 0) { memcpy(p, eps, LEN * N); p += LEN * N; }
    memcpy(p, path, (size_t)h * N); p += (size_t)h * N;
    return (size_t)(p - out);
}

/* Strict parse + full verification, mirroring experiment_submission.verify. */
static int verify_serialized(const uint8_t *sig_bytes, size_t slen,
                             const uint8_t *pk_bytes, size_t plen,
                             const uint8_t *m, size_t ml) {
    if (plen != PK_BYTES || memcmp(pk_bytes, "HBP1", 4) != 0) return 1;
    int code = pk_bytes[4];
    int h = pk_bytes[5];
    if (code != 1 || h < 1 || h > MAXH) return 1;
    const uint8_t *root = pk_bytes + 6;

    if (slen < 8 || memcmp(sig_bytes, "HBS1", 4) != 0) return 1;
    int mode = sig_bytes[4];
    if (mode != 0 && mode != 1) return 1;
    if (sig_bytes[5] != code || sig_bytes[6] != h) return 1;

    int n_idx = (h + 7) / 8;
    size_t off = 7 + (size_t)n_idx;
    unsigned idx = (n_idx == 1) ? sig_bytes[7]
                                : (unsigned)(sig_bytes[7] << 8 | sig_bytes[8]);
    if (idx >= (1u << h)) return 1;

    size_t need = off + (size_t)LEN * N + (size_t)h * N;
    if (mode == 0) need += (size_t)LEN * N;
    if (slen != need) return 1;

    const uint8_t (*sig)[N] = (const uint8_t (*)[N])(sig_bytes + off);
    off += (size_t)LEN * N;
    const uint8_t *eps = NULL;
    if (mode == 0) { eps = sig_bytes + off; off += (size_t)LEN * N; }
    const uint8_t *path = sig_bytes + off;

    uint8_t rpk[LEN][N];
    wots_recover(sig, m, ml, rpk);
    if (mode == 0 && memcmp(rpk, eps, (size_t)LEN * N) != 0) return 1;

    uint8_t leaf[N];
    leaf_hash(leaf, rpk);
    return merkle_root(leaf, (int)idx, path, h, root);
}

/* ---- benchmark -------------------------------------------------------- */
static void run_case(int compact, int h) {
    int n = 1 << h;
    size_t ots = (size_t)LEN * N;
    size_t sig_bytes = 7 + (size_t)((h + 7) / 8) + ots
                       + (compact ? 0 : ots) + (size_t)h * N;

    uint8_t tree_seed[N];
    memcpy(SCRATCH, "SUB-TREE", 8);
    SCRATCH[8] = 1; SCRATCH[9] = (uint8_t)h; SCRATCH[10] = 0;
    sha256(tree_seed, SCRATCH, 11);

    WotsKey *keys = malloc((size_t)n * sizeof(WotsKey));
    uint8_t *layers = malloc((size_t)(2 * n - 1) * N);
    int *off = malloc((size_t)(h + 1) * sizeof(int));
    uint8_t root[N];
    uint8_t *path = malloc((size_t)h * N);
    uint8_t *pk_bytes = malloc(PK_BYTES);
    uint8_t *sig_bytes_buf = malloc(sig_bytes);
    if (!keys || !layers || !off || !path || !pk_bytes || !sig_bytes_buf) {
        fprintf(stderr, "alloc failed\n"); exit(2);
    }

    uint8_t msg[64];
    for (int i = 0; i < 64; i++) msg[i] = (uint8_t)(i * 7 + 3);

    double kg[REPS], sg[REPS], vf[REPS];
    uint8_t sig[LEN][N];

    /* warm-up */
    build_tree(tree_seed, h, keys, layers, off, root);
    pack_pk(pk_bytes, h, root);
    for (int l = 0; l < h; l++) memcpy(path + (size_t)l * N,
                                      layers + off[l] + (size_t)((0 ^ 1)) * N, N);
    wots_sign(&keys[0], msg, sizeof msg, sig);
    pack_sig(sig_bytes_buf, h, 0, compact, sig, keys[0].pk, path);
    if (verify_serialized(sig_bytes_buf, sig_bytes, pk_bytes, PK_BYTES,
                          msg, sizeof msg) != 0) {
        fprintf(stderr, "warm-up verify failed (h=%d compact=%d)\n", h, compact);
        exit(3);
    }

    /* key generation: all 2^h one-time keys, leaves and tree */
    for (int r = 0; r < REPS; r++) {
        double t = now_us();
        build_tree(tree_seed, h, keys, layers, off, root);
        kg[r] = now_us() - t;
    }

    /* signing: OTS chains + authentication path read from precomputed layers */
    pack_pk(pk_bytes, h, root);
    long sign_chain = 0;
    for (int r = 0; r < REPS; r++) {
        int leaf = r % n;
        for (int l = 0; l < h; l++)
            memcpy(path + (size_t)l * N,
                   layers + off[l] + (size_t)((leaf >> l) ^ 1) * N, N);
        chain_calls = 0;
        double t = now_us();
        wots_sign(&keys[leaf], msg, sizeof msg, sig);
        pack_sig(sig_bytes_buf, h, leaf, compact, sig, keys[leaf].pk, path);
        sg[r] = now_us() - t;
        sign_chain += chain_calls;
    }

    /* verification: parse serialized bytes, one chain pass per element */
    int bad = 0;
    long ver_chain = 0;
    for (int r = 0; r < REPS; r++) {
        int leaf = r % n;
        for (int l = 0; l < h; l++)
            memcpy(path + (size_t)l * N,
                   layers + off[l] + (size_t)((leaf >> l) ^ 1) * N, N);
        wots_sign(&keys[leaf], msg, sizeof msg, sig);
        pack_sig(sig_bytes_buf, h, leaf, compact, sig, keys[leaf].pk, path);
        chain_calls = 0;
        double t = now_us();
        int rc = verify_serialized(sig_bytes_buf, sig_bytes, pk_bytes, PK_BYTES,
                                   msg, sizeof msg);
        vf[r] = now_us() - t;
        ver_chain += chain_calls;
        if (rc) bad = 1;
    }

    qsort(kg, REPS, sizeof(double), cmp_d);
    qsort(sg, REPS, sizeof(double), cmp_d);
    qsort(vf, REPS, sizeof(double), cmp_d);

    printf("{\"kind\":\"wots\",\"compact\":%s,\"h\":%d,\"n\":%d,"
           "\"keygen_ms\":%.4f,\"keygen_iqr\":%.4f,"
           "\"sign_ms\":%.4f,\"sign_iqr\":%.4f,"
           "\"verify_ms\":%.4f,\"verify_iqr\":%.4f,"
           "\"sign_chain_calls\":%ld,\"verify_chain_calls\":%ld,"
           "\"sig_bytes\":%zu,\"verify_ok\":%d}\n",
           compact ? "true" : "false", h, n,
           median(kg, REPS) / 1000.0, iqr(kg, REPS) / 1000.0,
           median(sg, REPS) / 1000.0, iqr(sg, REPS) / 1000.0,
           median(vf, REPS) / 1000.0, iqr(vf, REPS) / 1000.0,
           sign_chain / REPS, ver_chain / REPS, sig_bytes, bad ? 0 : 1);
    fflush(stdout);

    free(keys); free(layers); free(off); free(path);
    free(pk_bytes); free(sig_bytes_buf);
}

/* Print the root and first leaf hash for a given height so the Python and C
 * constructions can be compared byte for byte (same tree seed derivation). */
static int dump_root(int h) {
    int n = 1 << h;
    uint8_t tree_seed[N];
    memcpy(SCRATCH, "SUB-TREE", 8);
    SCRATCH[8] = 1; SCRATCH[9] = (uint8_t)h; SCRATCH[10] = 0;
    sha256(tree_seed, SCRATCH, 11);

    WotsKey *keys = malloc((size_t)n * sizeof(WotsKey));
    uint8_t *layers = malloc((size_t)(2 * n - 1) * N);
    int *off = malloc((size_t)(h + 1) * sizeof(int));
    uint8_t root[N];
    build_tree(tree_seed, h, keys, layers, off, root);

    printf("h=%d root=", h);
    for (int i = 0; i < N; i++) printf("%02x", root[i]);
    printf("\nleaf0=");
    for (int i = 0; i < N; i++) printf("%02x", layers[i]);
    printf("\n");
    free(keys); free(layers); free(off);
    return 0;
}

int main(int argc, char **argv) {
    if (argc > 2 && strcmp(argv[1], "--root") == 0) return dump_root(atoi(argv[2]));
    for (int h = 1; h <= MAXH; h++) run_case(0, h);
    for (int h = 1; h <= MAXH; h++) run_case(1, h);
    return 0;
}
