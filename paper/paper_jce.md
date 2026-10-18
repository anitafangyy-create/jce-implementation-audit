# Engineering Trade-offs in Merkle-Aggregated Winternitz Signatures

**Payload accounting, implementation reproducibility, and irreversible signing state under ledger reorganization**

**Abstract**

Merkle-aggregated Winternitz signatures offer a tunable communication–computation trade-off, but an implementation comparison must account for public-key transmission, complete verification, and signer state. We study a research artifact through source audit, analytical accounting, and a separately implemented repaired variant. The audit identifies a checksum-encoding defect and a mismatch between reported signature size and verifier inputs. For a 32-byte hash output and tree height four, explicit-public-key payloads span 8,640–2,304 bytes, whereas endpoint recovery reduces them to 4,384–1,216 bytes before framing. We define both wire formats and measure complete verification over three bases, two tree heights, and 270 fresh-message samples, retaining environment metadata and raw observations. The smallest repaired configuration serializes to 1,224 bytes including its eight-byte header. Exact checksum-distribution calculations refine the usual chain-work approximation. We also distinguish irreversible signing exposure from reversible ledger confirmation, establish a conditional non-reuse invariant, and give a counterexample to exact recovery from confirmed-chain history alone. A bounded state exploration and negative-input tests make these findings reproducible. The repaired variant remains a fixed-prefix research construction, not standardized WOTS+, and no cryptographic security level is assigned. The results support precise engineering claims about payload accounting, verification boundaries, and recovery obligations rather than a new post-quantum signature primitive.

**Keywords:** hash-based signatures; Winternitz; Merkle trees; implementation audit; reproducibility; stateful signatures.

## 1. Introduction

The engineering appeal of hash-based signatures is that their central operations are hashes and byte-string manipulations. Their practical cost nevertheless depends on much more than the hash output length: Winternitz parameters determine chain work, Merkle authentication adds communication and storage, and one-time signing requires reliable state management. A comparison is meaningful only when the transmitted objects, verification inputs, and security assumptions are explicit.

We investigate four research questions: RQ1, how much communication is saved by recovering rather than transmitting the one-time public key; RQ2, how complete verification and authentication-path construction vary with the Winternitz base and tree height; RQ3, which claims survive an implementation-level correctness audit; and RQ4, whether confirmed-chain replay is sufficient to recover one-time signing state. We address these questions using source inspection, exact arithmetic, an independently coded experimental variant, and a signer-state model.

The contributions are: **C1**, an executable source-to-claim audit with corrected payload and checksum-work accounting; **C2**, two fully specified experimental wire formats and a paired verification study covering w ∈ {4, 16, 256} and h ∈ {4, 8}, with raw samples and negative-input tests; and **C3**, a conditional non-reuse invariant and a recovery counterexample separating key exposure from ledger acceptance. These are reproducibility and integration contributions. Endpoint recovery and state reservation are established techniques [1,2]; this work claims neither a new signature primitive nor priority for those techniques.

## 2. Background and Scope

### 2.1 Established schemes

XMSS specifies WOTS+ within a stateful Merkle construction and defines public-key recovery from a signature [1]. LMS provides another standardized stateful hash-based design [3]. NIST SP 800-208 discusses approved stateful schemes and their operational requirements [4]. These are appropriate reference points for a future implementation comparison.

SLH-DSA is the stateless hash-based signature standard in FIPS 205; ML-DSA is the module-lattice signature standard in FIPS 204 [5,6]. Their published sizes provide communication baselines. They do not establish a security level or performance baseline for this repository's custom construction.

### 2.2 Terminology and evidence

The source files use the label “WOTS+.” In this paper, **Winternitz prototype** denotes their actual algorithm: repeated SHA-256 with a fixed prefix, a message digest, and a checksum field. It lacks the seed/address-dependent functions of the standardized constructions. Its checksum is also encoded incorrectly (Section 4). We therefore reserve “WOTS+” for the referenced schemes.

We distinguish **recorded results** from saved JSON, **derived values** calculated from code, and **proposed improvements** that require implementation and fresh measurement. All byte counts refer to bytes, and KiB denotes 1,024 bytes. No security certification or NIST security category is assigned to the prototype.

### 2.3 Lessons from a layered protocol specification

Shielded Bitcoin separates transfer semantics, state reconstruction, assumptions, and leakage [7]. We adopt that organizational discipline while studying a different object: signer-side key consumption. Its note tree does not substitute for this work's authentication tree, and a replayed spent-note set does not record an unconfirmed signature exposed outside the chain. Section 7.4 formalizes that distinction. The comparison is methodological, not a claim of compatible implementations or inherited privacy.

### 2.4 Position relative to implementation and state-management work

McGrew et al. analyze synchronization, cloning, and state reservation in hash-based signing [2]. Our reservation rule specializes that established discipline to an execution with ledger reorganizations; Proposition 1 is a conditional integration invariant, not a new state-management mechanism. Hülsing's W-OTS+ construction [8] supplies a cryptographic reference, whereas the fixed-prefix variant here supplies only an experimental accounting vehicle. The public XMSS/LMS benchmark collection of Romansky et al. [9] motivates comparisons over capacity and parameter choices, but its timings are not imported as same-platform measurements.

The resulting scope is deliberately narrow: a transparent audit and paired experiment on a small artifact, plus an explicit recovery failure case. The study does not demonstrate that the proposed implementation outperforms standardized XMSS, LMS, or SLH-DSA. A broader claim would require conforming implementations and matched security parameters on the same hardware.

## 3. Artifact and Evaluation Method

### 3.1 Source-to-claim mapping

| Artifact | Role in this study | Evidentiary boundary |
|---|---|---|
| `hbs_signature.py` | Lamport signing and Merkle aggregation | In-memory research implementation; no durable used-leaf registry |
| `wots.py` | Fixed-base Winternitz prototype, w = 16 | Fixed-prefix chain function; defective checksum |
| `experiment_v2.py` | Generic wrapper carrying signature, public key, path, and index | Supports explicit-public-key payload accounting |
| `experiment_jce.py` | Parameter sweep, h = 4, ten repetitions | Verification uses resident public keys and cached leaf hashes |
| `results_jce.json` | Historical timing means and sample standard deviations | Raw samples and machine metadata are absent |
| `wots_bench.c` | C chain microbenchmark, w = 16 | Different message hashing and timing boundaries |
| `bip360_demo.py` | Local root/signature checks and size estimate | No transaction serializer or consensus execution |
| `make_kat.py`, `kat_wots.json` | Deterministic local regression vector | Self-consistency, not independent standard conformance |
| `experiment_submission.py`, `results_submission.json` | Repaired variant, two encodings, 270 raw samples | Fixed-prefix construction; process-local state only |
| `state_model_jce.py`, `state_model_jce.json` | Bounded signer-state exploration | Abstract transitions, not persistent-storage validation |
| `audit_jce.py`, `audit_jce.json` | Reproducible checks added for this revision | Verifies arithmetic and observed behavior, not unforgeability |

Table 1. Source artifacts and the boundaries of the claims they support.

### 3.2 Measurement procedure recovered from code

For each w, the Python benchmark generates 16 one-time key pairs and a Merkle root ten times. The final set of keys is retained. Signing then repeats ten times on the same message and leaf zero; each repetition recomputes an authentication path. Verification repeats against the resident one-time public key and starts its tree walk from a cached leaf hash.

The signing and verification observations are therefore repeated timings of a fixed workload, not independent messages or ten independently selected leaves. The key-generation interval covers all 16 keys and tree construction. The signing interval includes digest processing, chain evaluation, and path generation. The verification interval includes digest processing, endpoint comparisons, and four internal-node hashes, but omits public-key-to-leaf hashing and serialized input parsing.

The previous manuscript identified Apple Silicon, Python 3.11, and Apple clang 17. Because the saved JSON does not record hardware, interpreter, compiler flags, or raw samples, those environment claims cannot be independently reconstructed from the result file. This revision preserves the historical timing aggregates without inventing missing provenance.

## 4. Construction and Correctness Findings

### 4.1 Parameters and operations

Let n = 32 be the hash output length **in bytes**, b = log₂(w), and h the Merkle height. The evaluated bases divide the 256-bit digest exactly. The chain counts are:

<div class="equation">L₁ = ⌈8n / b⌉ &nbsp;;&nbsp; L₂ = ⌊log<sub>w</sub>(L₁(w − 1))⌋ + 1 &nbsp;;&nbsp; L = L₁ + L₂.</div>

For message digits mᵢ, the intended checksum is C = Σᵢ(w − 1 − mᵢ). Its base-w representation contributes L₂ additional digits. Each signature element reveals a position on one chain; verification advances that value to the public endpoint. The supplied chain function is F(x) = SHA-256(`WOTS-CHAIN` ∥ x). The Python message digest is SHA-256(`HBS-PQ-MSG-v1` ∥ M).

Merkle leaves commit to concatenated one-time public endpoints with a fixed prefix. Internal nodes hash a prefix and the ordered left and right children. The index determines path orientation. Prefix conventions differ between the generic wrapper and the JCE benchmark, so these artifacts should not be assumed interoperable.

### 4.2 Checksum-encoding defect

Both Python implementations serialize C as a 32-byte big-endian integer and then extract the **first** L₂ base-w digits. The decoder consumes the most significant bits first, despite the LSB-first wording in one docstring. Since C is small, every extracted checksum digit is zero for all messages and all three evaluated bases. The C implementation also reads leading zeros and stores only the low checksum byte.

| w | Checksum for benchmark message | Encoded checksum in current Python code | Intended base-w digits |
|---:|---:|---|---|
| 4 | 178 | 0, 0, 0, 0, 0 | 0, 2, 3, 0, 2 |
| 16 | 451 | 0, 0, 0 | 1, 12, 3 |
| 256 | 3,706 | 0, 0 | 14, 122 |

Table 2. Deterministically reproduced by `audit_jce.py` using the exact message in `experiment_jce.py`.

A direct fixed-length digit extraction illustrates the required arithmetic:

```python
checksum_digits = [
    (checksum >> (log_w * i)) & (w - 1)
    for i in range(len2 - 1, -1, -1)
]
```

This is a proposed correction, not a claim that the legacy measurements used corrected code. Standard conformance also requires the appropriate hashing, addressing, encoding, and independent vectors.

The checksum is intended to stop an adversary from obtaining another valid digit vector solely by advancing revealed chain values. With a constant checksum, that safeguard is absent. A valid-signature round trip and rejection of a randomly modified signature do not establish the missing property. No unforgeability theorem or numerical forgery bound follows from these checks.

### 4.3 Authentication and key reconstruction

The generic wrapper explicitly carries the one-time public key. A compact alternative recovers each endpoint from the signature and message, hashes the recovered endpoints into a leaf, and verifies the authentication path against the root. This removes the endpoint array from the wire. The legacy benchmark does not time the full root-bound procedure; the repaired experiment in Section 6.4 implements and measures it from serialized inputs. It corrects the checksum while retaining the same fixed-prefix chain function, so this improvement does not confer standard conformance.

## 5. Communication, Computation, and Storage

### 5.1 Two payload models

For a Winternitz signature of Ln bytes and h authentication nodes, the models are:

<div class="equation">S<sub>explicit</sub> = n(2L + h) &nbsp;;&nbsp; S<sub>recovered</sub> = n(L + h).</div>

The first includes the one-time signature **and** public key. The second assumes endpoint recovery. Both exclude the leaf index, algorithm identifiers, and framing. Under a fixed-width index convention, add ⌈h/8⌉ bytes, which is one byte at h = 4. A 32-byte root is the public-key commitment; a complete public-key encoding must also establish the parameters.

| w | L₁ | L₂ | L | Explicit-key payload (B) | Recovery-model payload (B) | Raw secrets, 16 leaves (KiB) |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 128 | 5 | 133 | 8,640 | 4,384 | 66.5 |
| 16 | 64 | 3 | 67 | 4,416 | 2,272 | 33.5 |
| 256 | 32 | 2 | 34 | 2,304 | 1,216 | 17.0 |

Table 3. Derived values for n = 32 and h = 4; these are component counts, not measured network encodings.

The original `sig_bytes` field in `results_jce.json` reports the recovery model while the verifier receives a resident public key. Its label therefore cannot be interpreted as the complete payload of the measured interface. The explicit-key model yields 8,641, 4,417, and 2,305 bytes when the illustrative one-byte index is included.

For the supplied Lamport wrapper, the same accounting gives 8,192 signature bytes + 16,384 public-key bytes + 128 path bytes = **24,704 bytes**, before index and framing.

### 5.2 Exact chain work and expected work

For a digit vector d of length L, chain calls satisfy:

<div class="equation">T<sub>sign</sub> = Σᵢ dᵢ &nbsp;;&nbsp; T<sub>verify</sub> = L(w − 1) − T<sub>sign</sub>.</div>

For uniform message digest digits and a correctly encoded checksum:

<div class="equation">E[T<sub>sign</sub>] = L₁(w − 1)/2 + E[Σⱼ cⱼ].</div>

Checksum digits cⱼ are dependent functions of the message digits; they are not independent uniform samples. Thus L(w − 1)/2 is not the exact expected signing work. In the defective implementation, the checksum contribution is zero, making the uniform-digest expectation L₁(w − 1)/2. The benchmark uses a fixed digest, so its actual counts are deterministic:

| w | Actual sign chain calls | Actual verify chain calls | Calls per OTS key generation | Legacy reported “average” |
|---:|---:|---:|---:|---:|
| 4 | 206 | 193 | 399 | 199.5 |
| 16 | 509 | 496 | 1,005 | 502.5 |
| 256 | 4,454 | 4,216 | 8,670 | 4,335.0 |

Table 4. Exact counts exclude message hashes, leaf hashes, tree hashes, and allocation. The final column is the old model value, not instrumentation.

### 5.3 Exact checksum expectation

Let aₜ(c) count the length-t base-w vectors whose digits sum to c. Initialize a₀(0) = 1, take out-of-range counts as zero, and compute a<sub>t</sub>(c) = Σ<sub>u=0</sub><sup>w−1</sup> a<sub>t−1</sub>(c − u). Since w − 1 − mᵢ is uniform whenever mᵢ is uniform, a<sub>L₁</sub>(c)/w<sup>L₁</sup> is the checksum distribution. If s<sub>w</sub>(c) is the sum of the L₂ base-w digits of c, then:

<div class="equation">E[Σⱼ cⱼ] = w<sup>−L₁</sup> Σ<sub>c=0</sub><sup>L₁(w−1)</sup> a<sub>L₁</sub>(c) s<sub>w</sub>(c).</div>

The recurrence follows by partitioning vectors by their last digit; normalization is Σc aₜ(c) = wᵗ. The implementation uses exact integer counts and a sliding-window convolution, converting only the final ratio to floating point. Table 5 gives the resulting expectations. This is a distributional calculation under a uniform digest model, not a security assumption about the custom signature scheme.

| w | Expected checksum digit sum | Corrected expected sign calls | Approximation L(w − 1)/2 |
|---:|---:|---:|---:|
| 4 | 6.984003 | 198.984003 | 199.5 |
| 16 | 19.077380 | 499.077380 | 502.5 |
| 256 | 142.939453 | 4222.939453 | 4335.0 |

Table 5. Exact-distribution expectations, rounded to six decimal places; the saved JSON includes exact numerators and denominators.

### 5.4 Storage and tree scaling

Raw secret arrays occupy 2ʰLn bytes. The figures in Table 3 exclude Python object overhead, public endpoints, cached leaves, and durable state. They must not be described as process memory measurements. A production implementation may derive secrets from a protected seed and use an established traversal algorithm, but those designs need separate analysis.

The current `auth_path` routine rebuilds successive tree layers and performs 2ʰ − 1 internal-node hashes per call. Its signing-side path work therefore scales with the full tree size; the four-node verification walk scales with h. Measurements at h = 4 cannot establish performance for large signing capacities.

## 6. Experimental Results and Interpretation

### 6.1 Preserved Python measurements

| w | Full-tree key generation (ms) | Signing (ms) | Verification (ms) |
|---:|---:|---:|---:|
| 4 | 8.34 ± 1.41 | 0.293 ± 0.075 | 0.172 ± 0.092 |
| 16 | 14.01 ± 0.47 | 0.408 ± 0.042 | 0.414 ± 0.151 |
| 256 | 97.47 ± 2.08 | 2.488 ± 0.688 | 2.963 ± 0.280 |

Table 6. Historical means ± sample standard deviations from `results_jce.json`, ten repetitions each. These are legacy defective-prototype timings with the measurement boundaries in Section 3.2.

![Figure 1. Historical Python latency against explicit-public-key payload accounting. Error bars are recorded sample standard deviations, not confidence intervals. The code has a defective checksum; a complete serialized verification path was not timed.](fig_jce_wtradeoff.png)

![Figure 2. Exact chain calls for the fixed benchmark message, separating signing from verification. These counts describe the legacy implementation and exclude all non-chain operations.](fig_jce_costmodel.png)

Increasing w reduces the number of transmitted chain values while increasing chain work. The w = 256 configuration has the smallest payload and highest recorded signing and verification latency among the three points. The data do not establish a general Pareto optimum across implementations or secure schemes, nor do they isolate Python loop overhead as the cause of the observed timing differences.

### 6.2 C microbenchmark boundary

`wots_bench.c` evaluates only w = 16 and averages 100 repetitions. It generates deterministic secret bytes instead of using the Python randomness source. It hashes an unprefixed message, computes its digits outside the signing timer, omits Merkle work, and has no recorded sample variance. Thus it is a hash-chain microbenchmark rather than a drop-in reference implementation of the Python interface.

The artifact contains no machine-readable C run log with provenance and variance. Accordingly, we report no Python-to-C speed-up. The fresh study in Section 6.4 compares serialization modes within one implementation and runtime, avoiding this workload mismatch. It does not provide evidence about optimized C performance.

### 6.3 Standardized size baselines

| Scheme | Public key (B) | Signature (B) | State requirement / comparison status |
|---|---:|---:|---|
| ML-DSA-44 [6] | 1,312 | 2,420 | Stateless; published standard sizes |
| ML-DSA-65 [6] | 1,952 | 3,309 | Stateless; published standard sizes |
| SLH-DSA-SHA2-128s [5] | 32 | 7,856 | Stateless; published standard sizes |
| SLH-DSA-SHA2-128f [5] | 32 | 17,088 | Stateless; published standard sizes |
| Prototype, w = 16 | 32-byte root | 4,416 + index/framing | Stateful design; security not established |
| Prototype, w = 256 | 32-byte root | 2,304 + index/framing | Stateful design; security not established |
| Repaired recovery model, w = 256 | 32-byte root | 1,216 + index/framing | Payload excludes header; full path measured in Section 6.4 |

Table 7. Size context only. Standardized schemes were not run on the same machine, and these rows do not represent equivalent security guarantees, key lifetimes, or serialization conventions.

The 1,216-byte value is approximately 49.8% below 2,420 bytes arithmetically. It is not evidence that the implemented scheme delivers an equally secure signature at half the size. Even the 2,304-byte explicit-key payload excludes framing and pertains to a defective prototype with only 16 leaves in this experiment.

### 6.4 Repaired wire-to-root experiment

To test RQ1–RQ2 beyond the legacy artifact, `experiment_submission.py` separately implements integer-based checksum extraction, endpoint recovery, a canonical experimental byte format, strict length checks, and full verification from only (message, signature bytes, public-key bytes). It preserves the fixed-prefix SHA-256 chain, so the result is a repaired research variant, not standardized WOTS+. A process-local used-index set rejects repeated signing, but it provides no crash durability or rollback protection.

**Encoding.** The public key is `HBP1 || base_code || height || root`, with a total length of 38 bytes. The signature is `HBS1 || mode || base_code || height || index || elements || path`. Magic strings occupy four bytes; mode, base code, and height occupy one byte each. Base codes 0, 1, and 2 map to 4, 16, and 256. Mode 0 includes signature elements followed by public endpoints; mode 1 includes signature elements alone. The big-endian index uses ⌈h/8⌉ bytes, which is one for both tested heights. All elements and path nodes are 32 bytes. The verifier rejects unsupported fields, excess or missing bytes, out-of-range indices, and parameter mismatch with the public key. Thus each signature has exactly eight header bytes in this experiment.

**Sampling and timing.** Each (w,h) configuration uses three independently generated trees, with one unrecorded warm-up leaf and 15 measured leaves per tree. At h = 4, measured indices are 1–15; at h = 8, they are 1 + 17j for j = 0,…,14, sampling paths across the tree. Each measured message contains fresh random bytes. Both encodings use the same signature, message, and path; verification order alternates between modes by trial. The total is 270 measured signing events, with 45 paired observations per configuration. Tables report descriptive means and sample standard deviations; shared trees and a single host preclude interpreting the observations as independent deployment trials.

**Runtime.** The recorded process reports CPython 3.7.3, Darwin 24.6.0, and x86_64. These identify the execution environment, not the physical CPU model; native execution versus translation was not established. Timings use `perf_counter_ns`. Hardware power state, CPU frequency, and background load were uncontrolled. The old and new timing tables must not be combined into a speed-up claim.

| w | h | Explicit bytes | Compact bytes | Explicit verify (ms) | Compact verify (ms) |
|---:|---:|---:|---:|---:|---:|
| 4 | 4 | 8,648 | 4,392 | 0.932 ± 0.549 | 1.005 ± 0.605 |
| 4 | 8 | 8,776 | 4,520 | 1.046 ± 1.320 | 1.025 ± 1.133 |
| 16 | 4 | 4,424 | 2,280 | 0.942 ± 0.423 | 0.982 ± 0.507 |
| 16 | 8 | 4,552 | 2,408 | 1.283 ± 0.358 | 1.254 ± 0.348 |
| 256 | 4 | 2,312 | 1,224 | 7.657 ± 4.310 | 7.399 ± 2.475 |
| 256 | 8 | 2,440 | 1,352 | 7.609 ± 2.471 | 8.482 ± 2.041 |

Table 8. Fresh paired wire-to-root measurements; mean ± sample standard deviation, 45 observations per row. Both verification modes include parsing, message digest, endpoint computation, leaf hashing, and the complete root check. Encoded sizes include all experimental header bytes.

Endpoint recovery removes exactly Ln bytes, with no missing external public-key input. Both modes already evaluate the remaining chain segments; transmitting the endpoints does not avoid this work. Consequently, no uniform latency advantage is expected or claimed from these small timing differences. The smallest measured encoding is 1,224 bytes at w = 256, h = 4. It supports only 16 leaves and has no assigned cryptographic security level.

### 6.5 Traversal ablation and validation

The same sample compares rebuilding the authentication path from the leaf layer with looking up siblings in a cached full tree. Both paths are checked for byte equality. Table 9 isolates these operations, excluding signing and encoding.

| w | h | Rebuilt path median (ms) | Cached path median (ms) | Cached internal-node bytes |
|---:|---:|---:|---:|---:|
| 4 | 4 | 0.0405 | 0.0040 | 480 |
| 4 | 8 | 0.6723 | 0.0043 | 8,160 |
| 16 | 4 | 0.0266 | 0.0028 | 480 |
| 16 | 8 | 0.7590 | 0.0044 | 8,160 |
| 256 | 4 | 0.0395 | 0.0076 | 480 |
| 256 | 8 | 0.7501 | 0.0089 | 8,160 |

Table 9. Authentication-path ablation, medians over 45 observations per row. The final column counts retained internal hash values only, excluding leaves and Python container overhead.

Rebuilding requires 2ʰ − 1 internal hashes per path, while cached lookup reads h siblings and computes no new tree hashes. Retaining all internal nodes costs n(2ʰ − 1) bytes: 480 bytes at h = 4 and 8,160 bytes at h = 8, in addition to leaves and key material. This is a full-cache comparison, not a comparison with memory-efficient production traversal algorithms.

The run executes 5,130 counted positive/negative checks: for each signing event, two successful verifications, sixteen rejections across the two modes, and one repeated-index rejection. Rejection cases cover changed signature bytes, wrong messages, truncation, appended bytes, invalid mode, changed path, changed index, and wrong root. Additional assertions check path equality and distribution normalization. These establish functional behavior on the sampled inputs; they are not a security proof, exhaustive parser fuzzing, or independent standards-conformance testing.

![Figure 3. Repaired-variant verification and path-construction measurements. Panel (a) shows means with one sample standard deviation. Panel (b) averages the three per-base path-time medians at each height; it is descriptive and has no confidence interval.](fig_submission.png)

### 6.6 Threats to validity

**Internal validity.** Paired inputs control message and key effects between serialization modes, but configuration order is fixed and measurements can be affected by thermal drift, runtime scheduling, and test activity between samples. There are only three independently generated trees per configuration. Raw samples support reanalysis; no significance test or confidence interval is claimed.

**External validity.** The variant uses small trees, full caching, Python, fixed-prefix hashing, and process-local state. It cannot establish production latency, large-capacity behavior, physical fault resistance, or security-equivalent performance against XMSS/LMS. Repeating the study with conforming schemes, native optimized implementations, and independent machines is necessary for those claims.

**Construct validity.** Byte counts cover an explicitly specified experimental wire format, not a Bitcoin witness or standardized signature. Verification timing is complete within that format; durable allocation, network transport, transaction validation, and wallet recovery are outside the measured interval.

## 7. Security and Operational Boundaries

### 7.1 What the artifact does not establish

A 256-bit digest does not automatically confer 128-bit security on a complete signature scheme. Security depends on the required hash properties, adversarial model, message hashing, chain addressing, number of targets, and reduction losses. This revision provides no proof in either a classical or quantum random-oracle model. In particular, a second-preimage argument alone does not justify the original EUF-CMA claim.

The absence of address-dependent chain hashing and the checksum defect prevent direct inheritance of standardized WOTS+ security claims. The supplied self-tests check functional agreement between signer and verifier; two implementations sharing the same mistake may agree perfectly.

### 7.2 One-time state

One-time keys must not be used for different signing requests. In the Lamport wrapper, the assertion checks only that the leaf index is in range; it does not record consumption. The generic Winternitz wrapper also lacks an enforced used-leaf registry. Repeated signing of the identical message in a microbenchmark adds no distinct chain positions, but it does not test safe state management.

A production signer needs atomic leaf reservation before a signature can leave the device, coordination across concurrent signers, and rollback-resistant state across recovery and backup. A checksummed log alone detects accidental corruption; it does not prevent restoration of an older valid log. Exhaustion must trigger key rotation. These operational properties are especially important when a changed transaction requires a new signature.

### 7.3 Timing, faults, and malformed input

Chain lengths are derived from message digits, which need not be secret. Variable iteration counts therefore do not by themselves demonstrate secret-dependent timing leakage. A production audit must still examine secret handling, comparisons, memory exposure, state transitions, and fault effects. Checking an endpoint does not reveal how many iterations a signer actually executed.

The prototype also lacks comprehensive hostile-input validation. Robust verification should reject incorrect counts, element lengths, indices, and path lengths without exceptions or unbounded work. These concerns are unmeasured limitations, not claimed mitigations.

### 7.4 A state model for exposure-safe recovery

Let signer state be S = (kid, B, P, C), where kid identifies a signing root, B is the durable set of reserved or consumed leaf indices, P contains pending reservations, and C is the set currently confirmed on the selected chain. Let E be the external observer's history of released signatures. E is a specification-level history, not a state that the wallet can necessarily reconstruct. The invariant of interest is that each index occurs in E at most once per kid. Rebroadcasting the identical stored signature is not a fresh release event in this model.

| Assumption | Required property | Status in the artifact |
|---|---|---|
| S1: unique reservation | All writers for a root share a linearizable allocator | Absent from the legacy signer |
| S2: durable ordering | Reservation is committed before signature release | Assumed by the abstract model |
| S3: rollback resistance | Recovery cannot decrease B or recreate a consumed key under the same kid | Assumed, not implemented |
| S4: single release | Each reservation enables at most one fresh signing operation | Assumed by the abstract model |
| S5: key discipline | No uncoordinated cloned signer bypasses this state | Operational assumption |

Table 10. Assumptions required for the conditional state invariant. These properties are not supplied by the legacy signer.

The proposed lifecycle is as follows:

```text
Reserve(k): require k not in B; atomically persist B := B union {k}; add k to P.
Emit(k, M): require a live reservation; consume it once; release the signature.
Crash:     discard uncertain pending operations; keep B unchanged.
Confirm:   update C from the selected chain; keep B unchanged.
Reorg:     recompute C for the replacement chain; keep B unchanged.
Recover:   restore a trusted non-decreasing B; otherwise disable this signing root.
```

A crash may burn an unused leaf. This sacrifices capacity to preserve safety. If signing completion is uncertain, the reservation is not retried with a different message. A transaction replacement needs a fresh leaf and must also satisfy the spending script's authorization rules; the model does not assume that every script supports such a replacement.

**Proposition 1 (conditional non-reuse).** Under S1–S5, no leaf index under the same kid is used for two fresh signature-release events, regardless of the number of crashes or chain reorganizations.

**Proof.** Initially B is empty. A reservation adds an index not already in B; linearizability serializes competing reservations. Each release consumes a unique reservation once. All other transitions preserve or increase B, including recovery under S3. Hence a released index can neither be reserved again nor released through its old reservation. Induction on the transition sequence establishes the claim. This proves only the allocator invariant under the stated assumptions, not cryptographic unforgeability or a property of the legacy implementation.

**Proposition 2 (chain-only recovery ambiguity).** Given only the key seed and the current confirmed-chain history, a recovery procedure cannot, in general, reconstruct the exact set of previously exposed one-time keys.

**Proof.** Consider two executions with the same seed and final confirmed chain. In the first, leaf k has never signed. In the second, its signature is delivered to an observer but the transaction is never confirmed, or is later removed by a reorganization. The recovery inputs are identical, but k is reusable only in the first execution. Thus no procedure restricted to these inputs can recover the exact exposure set in both cases. Conservatively abandoning the root remains safe, at the cost of availability. The claim does not exclude recovery with additional trusted durable state.

This distinction is the main protocol-design lesson: **ledger acceptance is reversible; signature exposure is not**. Public replay can restore the former without restoring the latter. The seed-only restoration pattern of a replay-based application must therefore not be copied into an OTS wallet without a separate exposure-state mechanism.

### 7.5 Executable model and observability

`state_model_jce.py` explores reserve, emit, crash, confirm, and reorganization transitions with three leaves and traces up to eight events. It reaches 52 distinct states and checks 351 transition occurrences, verifying monotonic consumption, unique release, and inclusion of exposed leaves in the consumed set. It also constructs the indistinguishable-chain counterexample of Proposition 2. This bounded abstract check complements the inductive argument; it neither tests a storage engine nor emulates concurrent processes or Byzantine hardware.

For the proposed explicit-index wire format, define the public observation O = (root, parameters, leaf index, signature, authentication path, transaction metadata). The construction adds no mechanism to hide amounts, senders, transaction structure, or signing frequency. Under sequential allocation, index progression also reveals allocation progress, including potential skipped leaves. No transcript-privacy theorem or anonymity claim is made. Observability and authenticity are distinct evaluation dimensions.

## 8. Bitcoin-Oriented Integration Model

### 8.1 Protocol context

BIP 360 is a draft P2MR proposal that removes the key-path spend and commits to a script tree. The version consulted for this revision is 0.12.1, accessed 28 September 2026. It distinguishes long-exposure protection from the additional signature changes needed for short-exposure threats; it does not specify a native Winternitz verification opcode [10].

### 8.2 What the local demonstration actually does

`bip360_demo.py` checks a custom Merkle root and the legacy signature in Python. Its `bc1z` string is a prefix followed by truncated hexadecimal, not a Bech32m-encoded address. Its tree commits directly to endpoint arrays with `MSS-LEAF` and `MSS-NODE`, rather than implementing the proposal's script commitment. The assumed three-byte verification script is only a size placeholder. No transaction, signature hash, script interpreter, or node validation is supplied.

Accordingly, successful local checks in `bip360_demo.json` demonstrate internal consistency only. They do not demonstrate an end-to-end P2MR spend, mainnet compatibility, or an implemented upgrade opcode.

### 8.3 Witness accounting

The stored 4,325-byte estimate equals 1 + 2,144 signature bytes + 2,144 public-key bytes + 3 assumed script bytes + 33 control-block bytes. It omits witness-item length prefixes.

Under the illustrative assumption that each of the 67 signature values and 67 public-key values occupies a separate 32-byte stack item, plus the assumed script and control block, serialization would give:

<div class="equation">1 + 134 × (1 + 32) + (1 + 3) + (1 + 33) = 4,461 bytes.</div>

This corrects the accounting for that hypothetical layout; it does not validate the unspecified script or its commitment to a public key. A realizable script may require additional key commitments or parameters and change the size. Neither this count nor one quarter of it is a complete transaction fee estimate.

## 9. Reproducibility and Next Evaluation

### 9.1 Reproduce this revision

Run the following from the `pqc_research` directory. The audit preserves the original benchmark JSON and vector file. The renderer validates the current HTML by default to preserve direct edits; an explicit --from-markdown rebuild requires Python with `mistune`; chart generation requires `matplotlib`.

```bash
python3 audit_jce.py
python3 state_model_jce.py
python3 make_charts_jce.py
python3 render_jce.py
```

The audit reconstructs checksum digits and operation counts, verifies byte accounting, checks endpoint recovery, exercises signature tampering and wrong-message rejection, and reproduces the local deterministic vector. It writes `audit_jce.json`. No timing rerun is required to reproduce the revised tables; the historical timings remain explicitly labeled.

### 9.2 Availability, provenance, and assistance

The accompanying local artifact includes legacy inputs, the audit scripts, the repaired experiment, `results_submission.json` with all 270 raw records and environment metadata, and the bounded state model. The experimental JSON records SHA-256 hashes of its source and two legacy inputs. Regenerate fresh measurements with `python3 experiment_submission.py` and Figure 3 with `python3 make_submission_figure.py`; timings will vary. The exact checksum expectations and byte lengths are deterministic.

The artifact has not been assigned a public repository URL, release identifier, or archival DOI. Those identifiers must be supplied for external artifact access at submission. This work used AI assistance for manuscript restructuring, implementation auditing, generating the supplementary experimental code, and drafting analytical arguments. This disclosure describes assistance, not independent validation or authorship; final technical accountability rests with the human authors.

### 9.3 Requirements for a stronger evaluation

1. Replace the fixed-prefix experimental function with a specified standards-based chain and message-hashing design, and validate the complete implementation against independent vectors.
2. Extend the experimental wire-to-root evaluation to a standards-conforming implementation and security-matched parameter sets.
3. Enforce one-time state and test concurrency, crashes, rollback, malformed inputs, and all leaf positions.
4. Record hardware, OS, interpreter/compiler versions, flags, raw samples, warm-up policy, and independent message/key trials. Measure Python and C over equivalent operations.
5. Compare standardized implementations on the same platform, and separate key generation, chain work, leaf hashing, traversal, parsing, and state persistence.
6. For a protocol demonstration, implement the actual address encoding, script commitment, transaction digest, witness serialization, and applicable validation rules.

## 10. Conclusion

This study makes the signature interface and recovery assumptions explicit. The source audit identifies a checksum defect and a mismatch between size accounting and verifier inputs. A repaired experimental variant then demonstrates complete verification of explicit-key and recovered-key encodings, with 270 retained samples and 5,130 functional checks. At height four, recovered-key encodings span 4,392–1,224 bytes including their headers. Exact checksum-distribution calculations refine the chain-work model, while the traversal ablation exposes the cost of rebuilding authentication paths. The state analysis shows that confirmed-chain recovery cannot reconstruct unconfirmed signing exposure and that non-reuse requires an independently persistent consumption record. These results support a reproducible engineering case study. Standard conformance, security-matched baselines, and durable-state validation remain necessary before deployment or stronger cryptographic claims.

## References

[1] A. Hülsing et al. *XMSS: eXtended Merkle Signature Scheme.* RFC 8391, 2018. [Specification](https://www.rfc-editor.org/rfc/rfc8391.html).

[2] D. McGrew, P. Kampanakis, S. Fluhrer, S.-L. Gazdag, D. Butin, and J. Buchmann. *State Management for Hash-Based Signatures.* IACR Cryptology ePrint Archive, Report 2016/357. [Manuscript](https://eprint.iacr.org/2016/357.pdf).

[3] D. McGrew et al. *Leighton-Micali Hash-Based Signatures.* RFC 8554, 2019. [Specification](https://www.rfc-editor.org/rfc/rfc8554.html).

[4] NIST. *Recommendation for Stateful Hash-Based Signature Schemes.* SP 800-208, 2020. [Publication](https://csrc.nist.gov/pubs/sp/800/208/final).

[5] NIST. *Stateless Hash-Based Digital Signature Standard.* FIPS 205, 2024. [Standard](https://doi.org/10.6028/NIST.FIPS.205).

[6] NIST. *Module-Lattice-Based Digital Signature Standard.* FIPS 204, 2024. [Standard](https://doi.org/10.6028/NIST.FIPS.204).

[7] C. Shikhelman, M. Komarov, and A. Moskvin. *Shielded Bitcoin: Private Transfers on the Bitcoin L1.* 24 September 2026. Sections 17–20 and Appendix A. [Author-hosted manuscript](https://www.allocinit.xyz/uploads/shielded-bitcoin.pdf).

[8] A. Hülsing. *W-OTS+ — Shorter Signatures for Hash-Based Signature Schemes.* AFRICACRYPT 2013, pp. 173–188. [DOI](https://doi.org/10.1007/978-3-642-38553-7_10). [Author manuscript](https://eprint.iacr.org/2017/965.pdf).

[9] B. Romansky, T. Mazzuchi, and S. Sarkani. *Stateful Hash-Based Signature (SHBS) Benchmark Data for XMSS and LMS.* arXiv:2502.06033, 2025. [Preprint](https://doi.org/10.48550/arXiv.2502.06033).

[10] H. Beast, E. Heilman, and I. Foxen Duke. *Pay-to-Merkle-Root (P2MR).* BIP 360, draft, version 0.12.1; accessed 28 September 2026. [Proposal](https://github.com/bitcoin/bips/blob/master/bip-0360.mediawiki).

## Appendix A. Local Regression Vector

The deterministic seed is `HBS-PQ-WOTS-KAT-v1-2026`. The message is `Post-quantum signature KAT vector #0`. The public-key prefix below is **32 bytes**, not 64:

```text
d365850175988b1839d8a0850f36fa1fa26bd40849ca847f308acbf0f81f1a0a
```

The complete secret, public key, and signature in `kat_wots.json` reproduce under the existing implementation. The vector is public test material and must never be used as a signing key. It is a local regression vector for the defective algorithm, not a NIST conformance vector. The file `kat_128s.rsp` contains the text `404: Not Found` and supplies no independent test evidence.
