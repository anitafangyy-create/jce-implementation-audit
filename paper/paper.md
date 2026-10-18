# A Compact Hash-Based Post-Quantum Signature Scheme: Lamport–WOTS+ with Merkle Trees and an Empirical Comparison Against NIST Standards

**Abstract**

We present a from-scratch implementation of a hash-based post-quantum signature (HBS) scheme built on the same cryptographic family as NIST FIPS 205 (SLH-DSA/SPHINCS+). The scheme layers Winternitz one-time signatures (WOTS+) on top of a Merkle hash tree, producing a 32-byte public key and a ~4.5 KB signature at the 128-bit post-quantum security level. We report a controlled benchmark across tree heights (supporting 2–128 signatures per public key), compare our on-the-wire sizes against secp256k1 Schnorr, ML-DSA (FIPS 204), and SLH-DSA (FIPS 205), and analyze the size–state–latency trade-off inherent to hash-based signatures. Our WOTS+ implementation passes deterministic known-answer tests and tamper-rejection checks. The work is positioned as a research prototype motivated by BIP-0360 (Pay-to-Merkle-Root), which reserves a script-tree output type in Bitcoin for future post-quantum signature integration.

---

## 1. Introduction

The arrival of cryptographically relevant quantum computers (CRQCs) would invalidate the elliptic-curve discrete logarithm problem on which Bitcoin's secp256k1 signatures rest. Shor's algorithm [1] solves the discrete logarithm problem in polynomial time, allowing a quantum adversary to recover private keys from public keys exposed on chain. NIST has mandated that U.S. federal systems migrate to post-quantum cryptography (PQC) by 2035 [2], and the Commercial National Security Algorithm Suite (CNSA) 2.0 requires post-quantum upgrades by 2030–2033.

Post-quantum signatures fall into four families: lattice-based (ML-DSA/Falcon), hash-based (SLH-DSA/XMSS/LMS), code-based (Classic McEliece), and multivariate/isogeny-based (SQIsign). Among these, hash-based signatures have the weakest security assumption—only a collision- and preimage-resistant hash function—and the longest track record, dating to Lamport's 1979 construction [3] and Merkle's 1989 tree aggregation [4].

BIP-0360 (Pay-to-Merkle-Root, P2MR) [5] is a proposed soft fork that removes the key-path spend from Taproot (BIP-341 [6]), leaving a script-tree output type that commits to a 32-byte Merkle root. P2MR is itself *not* a post-quantum signature; it is a shell that (i) avoids long-exposure leakage of secp256k1 public keys and (ii) reserves the `OP_SUCCESSx` upgrade path for future post-quantum signature opcodes. This paper implements and benchmarks the hash-based signature layer that such a shell would host.

**Contributions.** (1) We implement Lamport OTS, WOTS+, and a generic Merkle signature scheme in pure Python, with self-contained known-answer tests. (2) We quantify the compression achieved by replacing Lamport with WOTS+: signature size drops from 24.8 KB to 4.5 KB (5.5×), at a cost of ~0.2 ms signing latency. (3) We place our prototype on the size–latency Pareto frontier against FIPS 204/205 standards. (4) We explicitly analyze the stateful-vs-stateless trade-off that separates our Merkle approach from SPHINCS+.

## 2. Background

### 2.1 Quantum threats to ECC

Two attack windows matter for on-chain public keys:

- **Long-exposure attacks**: public keys embedded in spent or unspent outputs (e.g., P2PK, P2TR internal keys) are exposed indefinitely. An attacker has as much time as the funds remain at that address. These are the first attacks a CRQC would enable.
- **Short-exposure attacks**: while a transaction sits unconfirmed in the mempool, its public key is exposed for minutes. Exploiting this requires a faster CRQC; protection requires post-quantum signature schemes.

BIP-0360 addresses long-exposure attacks by committing only to a hash of a script tree. This paper addresses the signature scheme that the script tree will eventually verify.

### 2.2 Hash-based signatures

A one-time signature (OTS) signs exactly one message; reusing a key pair leaks the private key. Lamport OTS [3] uses 256 secret/public pairs, one per bit of the message digest; the signer reveals one preimage per bit. Merkle [4] aggregates $N = 2^h$ OTS public keys into a hash tree whose root is the overall public key. A signature consists of the OTS signature, the OTS public key, and the Merkle authentication path.

WOTS (Winternitz OTS) compresses Lamport by encoding the message digest in base-$w$ digits and using hash chains; a checksum prevents existential forgery. WOTS+ as standardized in FIPS 205 [7] uses a keyed internal function and address separation.

### 2.3 NIST standards

FIPS 204 (ML-DSA) [8] standardizes lattice-based signatures at NIST security levels 2, 3, and 5. FIPS 205 (SLH-DSA) [7] standardizes stateless hash-based signatures. RFC 8391 [9] standardizes stateful XMSS. Representative parameter sets are listed in Table 1.

## 3. Design

### 3.1 Lamport OTS

For $n = 32$ bytes (SHA-256 output), the key generation samples $2 \times 256$ secrets $x^{(b)}_i \in \{0,1\}^{256}$ for $b \in \{0,1\}$, $i \in [0,256)$, and publishes $y^{(b)}_i = H(x^{(b)}_i)$. To sign, the digest bits $m_i \in \{0,1\}$ select which preimage to reveal. Verification recomputes the hashes and compares against the public array.

Sizes: secret key 16,384 B, public key 16,384 B, signature 8,192 B.

### 3.2 WOTS+

Following FIPS 205 [7], we use $n = 32$, base $w = 16$ (4 bits per digit):

- `len1 = ceil(8n / log2 w) = 64` message chains;
- `len2 = floor(log2(len1*(w-1))/log2 w) + 1 = 3` checksum chains;
- `len = 67` total chains.

Key generation samples 67 secrets and publishes each after iterating the hash function $w-1 = 15$ times. Signing splits the message digest into 64 base-16 digits, computes the checksum $\sum (w-1-d_i)$, splits it into 3 base-16 digits, and reveals the chain position $d_i$ along each chain. Verification re-iterates from the revealed position to $w-1$ and compares to the public key.

Sizes: secret key 2,144 B, public key 2,144 B, signature 2,144 B.

### 3.3 Merkle signature scheme

For tree height $h$, we generate $2^h$ OTS key pairs, hash each public key to a leaf, and build a binary hash tree. The root (32 B) is the overall public key. A signature at leaf index $k$ consists of:

1. the OTS signature on the message;
2. the OTS public key (required for OTS verification);
3. the $h$-node authentication path.

Verification recomputes the leaf hash from the OTS public key, walks the authentication path to the root, and compares to the public root.

### 3.4 Security assumption

Both schemes are existentially unforgeable under chosen-message attacks in the random oracle model, assuming SHA-256 is second-preimage resistant. Shor's algorithm gives no speedup against hash preimages; Grover's algorithm [10] halves the bit security, so a 256-bit hash yields ~128-bit post-quantum security.

## 4. Implementation

The implementation is in Python 3, using only the standard library (`hashlib.sha256`, `os.urandom`). Three modules:

- `hbs_signature.py` — Lamport OTS and generic Merkle scheme;
- `wots.py` — WOTS+ with `base_w` and `chain` functions;
- `experiment_v2.py` — benchmark harness supporting both OTS backends.

We use plain SHA-256 with domain-separation prefixes (`"WOTS-CHAIN"`, `"MSS-LEAF"`, `"MSS-NODE"`) rather than the keyed PRF/F/H/H_msg construction of production SPHINCS+. This is a deliberate simplification; it is sufficient for offline signature benchmarking but not for multi-target security claims.

Known-answer tests use a deterministic DRBG (SHA-256 in counter mode) seeded with `HBS-PQ-WOTS-KAT-v1-2026`; vectors are serialized to `kat_wots.json`.

## 5. Experimental Results

### 5.1 Setup

Benchmarks run on a single-core Apple Silicon (macOS, Python 3). Each data point is the median of three repetitions. We measure key-generation time (building the whole tree), signing time, and verification time, across heights $h \in [1,7]$ (supporting 2–128 signatures).

### 5.2 Sizes

Table 1 compares on-the-wire sizes against standardized schemes.

| Scheme | Public key (B) | Signature (B) | Quantum-resistant? |
|---|---:|---:|---|
| secp256k1 Schnorr (BIP-340) [11] | 32 | 64 | No (Shor) |
| ML-DSA-44 (FIPS 204, NIST L2) [8] | 1,312 | 2,420 | Yes |
| ML-DSA-65 (FIPS 204, NIST L3) [8] | 1,952 | 3,309 | Yes |
| SLH-DSA-128s (FIPS 205, NIST L1) [7] | 32 | 7,856 | Yes |
| SLH-DSA-128f (FIPS 205, NIST L1) [7] | 32 | 17,088 | Yes |
| This work: Lamport+MSS, h=7 | 32 | 24,800 | Yes |
| This work: WOTS+MSS, h=7 | 32 | **4,512** | Yes |

Table 1: Public-key and signature sizes. Our WOTS+MSS prototype (n=32, SHA-256) produces a smaller signature than SLH-DSA-128s (which uses n=16 internally), at the cost of being stateful.

![Figure 1: Cross-scheme signature size comparison on a log scale. Our WOTS+MSS (4,512 B) sits between ML-DSA-44 (2,420 B) and SLH-DSA-128s (7,856 B).](fig6_cross_scheme_v2.png)

![Figure 2: WOTS+ compression effect across tree heights. Signature size drops from ~24.8 KB (Lamport) to ~4.5 KB (WOTS+), with negligible growth as tree height increases.](fig5_wots_compression.png)

### 5.3 Benchmark across heights

| h | N | Keygen (ms) | Sign (ms) | Verify (ms) | Sig (B) |
|---:|---:|---:|---:|---:|---:|
| Lamport+MSS | | | | | |
| 1 | 2 | 1.31 | 0.017 | 0.101 | 24,608 |
| 4 | 16 | 10.35 | 0.021 | 0.102 | 24,704 |
| 7 | 128 | 85.22 | 0.064 | 0.102 | 24,800 |
| WOTS+MSS | | | | | |
| 1 | 2 | 0.76 | 0.180 | 0.173 | 4,320 |
| 4 | 16 | 6.14 | 0.184 | 0.173 | 4,416 |
| 7 | 128 | 51.58 | 0.231 | 0.177 | 4,512 |

Table 2: Latency and size across tree heights. WOTS+ costs ~0.15 ms extra signing time (hash chains) but cuts signature size by 5.5×.

### 5.4 Key observations

1. **Public key is 32 B** for both constructions, identical to secp256k1 and SLH-DSA. This is what makes Merkle-root commitment (BIP-341/0360) cheap on chain.
2. **WOTS+ compresses signatures by 5.5×** relative to Lamport (4,512 B vs. 24,800 B). The remaining size is dominated by the WOTS+ public key that must be transmitted for OTS verification (2,144 B) plus the OTS signature (2,144 B) plus the authentication path (≤224 B).
3. **Latency is sub-millisecond** in all configurations. Signing/verification are dominated by SHA-256 calls; WOTS+ adds at most 15 iterations × 67 chains ≈ 1,005 hash calls per operation.
4. **Key generation scales linearly in $N$**: 52 ms for $N=128$. This is a one-time cost per public key and is paid off across all $N$ signatures.
5. **Our 4.5 KB signature is smaller than SLH-DSA-128s (7.9 KB)** because our prototype is stateful: the Merkle tree pre-commits to 128 OTS keys, and we pay no FORS hypertree overhead. SLH-DSA's statelessness costs ~1.7× in signature size.

## 6. Security Analysis

- **Unforgeability**: Correctness of the Lamport and WOTS+ verification routines was tested against (i) valid round-trip signatures, (ii) single-byte tampering of the signature, and (iii) wrong-message signatures. All tamper attempts were rejected.
- **Long-exposure resistance**: Because the on-chain address commits only to a 32-byte hash of the script tree, the secp256k1 (or future post-quantum) public key is not revealed until spend time. This matches BIP-0360's threat model.
- **State management**: Each WOTS+ OTS key pair may be used exactly once. Reuse leaks the private key via two revealed chain positions. A production wallet must maintain an on-disk usage bitmap; this is the same model as XMSS/LMS (RFC 8391 [9], RFC 8554 [12]).
- **Side channels**: This Python prototype is not constant-time and must not be used in production without C/Rust hardening and constant-time hash implementations.
- **Hash function choice**: SHA-256 provides 128-bit post-quantum security after Grover. NIST SLH-DSA parameter sets at level 1 use n=16; our n=32 choice is conservative.

## 7. Discussion and Limitations

1. **Stateful vs. stateless**. Our Merkle scheme is stateful. SPHINCS+ removes state by combining a hypertree (many-layered XMSS) with FORS (Forest of Random Subsets), at the cost of larger signatures. For a Bitcoin context where a wallet controls its own keys and can persist state, the smaller signature of a stateful scheme may be preferable.
2. **No FORS/hypertree**. We did not implement SPHINCS+'s stateless components. A direct byte-level comparison against the official SPHINCS+ KAT (`.rsp` files) requires that implementation; we leave it as future work.
3. **No domain separation**. We use prefix-separated SHA-256 rather than SPHINCS+'s PRF/F/H_msg construction. This is acceptable for benchmarking but not for formal multi-target security proofs.
4. **No hybrid signatures**. NIST IR 8547 [2] recommends hybrid (ECC + PQ) signatures during transition. A leaf script that requires both a secp256k1 Schnorr signature and a WOTS+ signature is a natural next step.
5. **Python performance**. Our timings are Python-level; a C/Rust implementation would be 10–100× faster. Relative size comparisons are unaffected.

## 8. Conclusion

We implemented and benchmarked a from-scratch hash-based post-quantum signature scheme in the FIPS 205 family. WOTS+ compression reduces the signature from 24.8 KB (naive Lamport) to 4.5 KB, yielding a 32-byte public key and sub-millisecond verification—smaller on the wire than SLH-DSA-128s, at the cost of state management. The prototype is directly relevant to BIP-0360's vision of a script-tree output type that can host post-quantum signature opcodes. Future work includes hypertree/stateless construction, hybrid ECC+PQ leaf scripts, byte-level KAT conformance against the SPHINCS+ reference, and a production C/Rust implementation.

---

## References

[1] P. W. Shor, "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer," *SIAM J. Comput.*, 1997.
[2] NIST, "Transition to Post-Quantum Cryptography: NIST IR 8547," 2024.
[3] L. Lamport, "Constructing Digital Signatures from a One-Way Function," SRI CSL-98, 1979.
[4] R. C. Merkle, "A Certified Digital Signature," *CRYPTO 1989*.
[5] H. Beast, E. Heilman, I. Foxen Duke, "BIP-0360: Pay-to-Merkle-Root (P2MR)," Draft, 2026.
[6] R. Friedman et al., "BIP-341: Taproot: SegWit Version 1 Outputs," 2021.
[7] NIST, "FIPS 205: Module-Lattice-Based Digital Signature Standard" (SLH-DSA/SPHINCS+), 2024.
[8] NIST, "FIPS 204: Module-Lattice-Based Digital Signature Standard" (ML-DSA), 2024.
[9] RFC 8391, "XMSS: Extended Merkle Signature Scheme," IRTF, 2018.
[10] L. K. Grover, "A Fast Quantum Mechanical Algorithm for Database Search," *STOC 1996*.
[11] BIP-340, "Schnorr Signatures for secp256k1," 2020.
[12] RFC 8554, "LMS: Leighton-Micali Signatures," IRTF, 2019.

---

## Appendix A. Known-Answer Test Vector (WOTS+, n=32, w=16)

- Seed: `HBS-PQ-WOTS-KAT-v1-2026` (SHA-256 counter-mode DRBG)
- Message (hex): `506f73742d7175616e74756d207369676e6174757265204b415420766563746f72202330`
- Public key (hex, first 128 bytes shown): `d365850175988b1839d8a0850f36fa1fa26bd40849ca847f308acbf0f81f1a0ad5796301bed4b028…`
- Signature (hex, first 128 bytes shown): `3cabb405101b7ce4c532444157a97c0af78e614a033ddd566eaef5c710ffe73cd5796301bed4b028…`
- Full vectors: `kat_wots.json` (2,144 B each for sk/pk/sig).

Reproduce:

```bash
python3 wots.py          # self-test
python3 make_kat.py      # regenerate KAT vector
```
