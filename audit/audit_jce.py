"""
audit_jce.py -- Reproducible audit for the JCE revision.

Implements the checks described in paper Sections 4 and 5:

  1. Checksum-encoding defect reproduction (paper Table 2).
  2. Exact chain-work counts for the fixed benchmark message (paper Table 4).
  3. Exact checksum expectation via the digit-sum distribution (paper Table 5).
  4. Byte-accounting checks for the explicit-key and recovery payload models.
  5. Endpoint recovery with a corrected integer checksum encoding, plus
     tamper / wrong-message / truncation rejection.
  6. Deterministic local regression vector round-trip (kat_wots.json).

The script writes audit_jce.json. It verifies arithmetic and observed
behavior; it does not establish unforgeability.
"""
from __future__ import annotations

import json
import math
import hashlib
from pathlib import Path

import sys as _sys
_ROOT = Path(__file__).resolve().parents[1]
_sys.path.insert(0, str(_ROOT / "src"))
_sys.path.insert(0, str(_ROOT / "experiments"))

from hbs_signature import H, H_message
from experiment_jce import base_w, chain, N

OUT = _ROOT
BENCH_MSG = b"JCE extended benchmark message"   # exact message in experiment_jce.py


# ---------------------------------------------------------------------------
# Parameter helpers (mirror experiment_jce.py)
# ---------------------------------------------------------------------------
def params_for_w(w: int) -> dict:
    log_w = int(math.log2(w))
    len1 = (8 * N + (log_w - 1)) // log_w
    len2 = math.floor(math.log2(len1 * (w - 1)) / log_w) + 1
    return {"w": w, "log_w": log_w, "len1": len1, "len2": len2,
            "len": len1 + len2}


def msg_digits(msg: bytes, p: dict) -> list[int]:
    digest = H_message(msg)
    return base_w(digest, p["len1"], p["log_w"])


# ---------------------------------------------------------------------------
# 1. Checksum-encoding defect (Table 2)
# ---------------------------------------------------------------------------
def checksum_digits_legacy(csum: int, p: dict) -> list[int]:
    """The defective encoding: serialize csum as a 32-byte big-endian integer
    and extract the first len2 base-w digits (most-significant first). Because
    csum is small, all extracted digits are zero."""
    return base_w(csum.to_bytes(N, "big"), p["len2"], p["log_w"])


def checksum_digits_int(csum: int, p: dict) -> list[int]:
    """Corrected encoding: little-endian digit extraction, reported in the
    same most-significant-first order as the legacy decoder for comparison."""
    log_w = p["log_w"]
    return [(csum >> (log_w * i)) & (p["w"] - 1)
            for i in range(p["len2"] - 1, -1, -1)]


def table2() -> dict:
    rows = []
    for w in (4, 16, 256):
        p = params_for_w(w)
        md = msg_digits(BENCH_MSG, p)
        csum = sum(w - 1 - d for d in md)
        legacy = checksum_digits_legacy(csum, p)
        intended = checksum_digits_int(csum, p)
        rows.append({
            "w": w,
            "checksum": csum,
            "legacy_encoded_digits": legacy,
            "intended_digits": intended,
            "defect_confirmed": all(d == 0 for d in legacy),
        })
    return {"benchmark_message": BENCH_MSG.decode(), "rows": rows}


# ---------------------------------------------------------------------------
# 2. Exact chain work for the fixed message (Table 4)
# ---------------------------------------------------------------------------
def table4() -> dict:
    rows = []
    for w in (4, 16, 256):
        p = params_for_w(w)
        md = msg_digits(BENCH_MSG, p)
        sign_calls = sum(md)                       # checksum digits all zero
        verify_calls = (p["len1"] * (w - 1) - sign_calls
                        + p["len2"] * (w - 1))     # verify advances every digit
        keygen_calls = p["len"] * (w - 1)
        legacy_avg = p["len"] * (w - 1) / 2
        rows.append({
            "w": w,
            "len1": p["len1"], "len2": p["len2"], "len": p["len"],
            "sign_chain_calls": sign_calls,
            "verify_chain_calls": verify_calls,
            "keygen_chain_calls": keygen_calls,
            "legacy_average": legacy_avg,
            "excludes": "message/leaf/tree hashes and allocation",
        })
    return {"message": BENCH_MSG.decode(), "rows": rows}


# ---------------------------------------------------------------------------
# 3. Exact checksum expectation (Table 5)
# ---------------------------------------------------------------------------
def digit_sum_distribution(w: int, t: int) -> list[int]:
    """a_t(c): number of length-t base-w vectors whose digits sum to c."""
    max_c = t * (w - 1)
    a = [0] * (max_c + 1)
    a[0] = 1
    for _ in range(t):
        new = [0] * (max_c + 1)
        for c in range(max_c + 1):
            if a[c] == 0:
                continue
            for u in range(w):
                new[c + u] += a[c]
        a = new
    return a


def expected_checksum_sum(w: int, len1: int, len2: int) -> float:
    a = digit_sum_distribution(w, len1)
    total = 0
    for c, cnt in enumerate(a):
        if cnt == 0:
            continue
        # sum of the len2 base-w digits of c (little-endian extraction)
        d = c
        s = 0
        for _ in range(len2):
            s += d % w
            d //= w
        total += cnt * s
    return total / (w ** len1)


def table5() -> dict:
    rows = []
    for w in (4, 16, 256):
        p = params_for_w(w)
        e_checksum = expected_checksum_sum(w, p["len1"], p["len2"])
        corrected = p["len1"] * (w - 1) / 2 + e_checksum
        approx = p["len"] * (w - 1) / 2
        rows.append({
            "w": w,
            "expected_checksum_digit_sum": round(e_checksum, 6),
            "corrected_expected_sign_calls": round(corrected, 6),
            "approximation_L(w-1)/2": approx,
            "exact_numerator_denominator": None,  # computed below
        })
    # Exact rational values for the saved JSON (numerator/denominator).
    for r in rows:
        w = r["w"]
        p = params_for_w(w)
        a = digit_sum_distribution(w, p["len1"])
        num = 0
        for c, cnt in enumerate(a):
            if cnt == 0:
                continue
            d, s = c, 0
            for _ in range(p["len2"]):
                s += d % w
                d //= w
            num += cnt * s
        den = w ** p["len1"]
        r["exact_numerator_denominator"] = [num, den]
    return {"model": "uniform message digest; correct checksum encoding",
            "rows": rows}


# ---------------------------------------------------------------------------
# 4. Byte accounting (Section 5.1)
# ---------------------------------------------------------------------------
def byte_accounting(height: int = 4) -> dict:
    rows = []
    for w in (4, 16, 256):
        p = params_for_w(w)
        explicit = N * (2 * p["len"] + height)
        recovered = N * (p["len"] + height)
        raw_secrets = 2 ** height * p["len"] * N / 1024
        rows.append({
            "w": w, "len1": p["len1"], "len2": p["len2"], "len": p["len"],
            "explicit_key_payload_bytes": explicit,
            "recovery_model_payload_bytes": recovered,
            "explicit_plus_index_bytes": explicit + 1,
            "raw_secrets_16_leaves_kib": raw_secrets,
        })
    # Lamport wrapper (hbs_signature.py): 8192 sig + 16384 pk + 128 path
    lamport = {"sig_bytes": 8192, "pk_bytes": 16384, "path_bytes": 128,
               "total_bytes": 8192 + 16384 + 128,
               "note": "before index and framing"}
    return {"height": height, "rows": rows, "lamport_wrapper": lamport}


# ---------------------------------------------------------------------------
# 5. Repaired variant: corrected checksum + endpoint recovery
# ---------------------------------------------------------------------------
def repaired_sign(sk: list[bytes], msg: bytes, p: dict) -> list[bytes]:
    md = msg_digits(msg, p)
    csum = sum(p["w"] - 1 - d for d in md)
    cd = checksum_digits_int(csum, p)
    digits = md + cd
    assert len(digits) == p["len"]
    return [chain(sk[i], 0, digits[i]) for i in range(p["len"])]


def repaired_verify(msg: bytes, sig: list[bytes], pk: list[bytes], p: dict) -> bool:
    if len(sig) != p["len"] or len(pk) != p["len"]:
        return False
    md = msg_digits(msg, p)
    csum = sum(p["w"] - 1 - d for d in md)
    cd = checksum_digits_int(csum, p)
    digits = md + cd
    for i in range(p["len"]):
        if chain(sig[i], digits[i], p["w"] - 1 - digits[i]) != pk[i]:
            return False
    return True


def endpoint_recovery(msg: bytes, sig: list[bytes], p: dict) -> list[bytes]:
    """Recover the one-time public endpoints from the signature and message."""
    md = msg_digits(msg, p)
    csum = sum(p["w"] - 1 - d for d in md)
    cd = checksum_digits_int(csum, p)
    digits = md + cd
    return [chain(sig[i], digits[i], p["w"] - 1 - digits[i])
            for i in range(p["len"])]


def repaired_checks() -> dict:
    results = {}
    for w in (4, 16, 256):
        p = params_for_w(w)
        sk = [hashlib.sha256(b"AUDIT-SEED-" + str(w).encode()
                             + i.to_bytes(2, "big")).digest() for i in range(p["len"])]
        pk = [chain(sk[i], 0, p["w"] - 1) for i in range(p["len"])]
        msg = BENCH_MSG + b" (repaired)"
        sig = repaired_sign(sk, msg, p)
        ok = repaired_verify(msg, sig, pk, p)
        # endpoint recovery equals the explicit public key
        recovered = endpoint_recovery(msg, sig, p)
        rec_ok = recovered == pk
        # tamper: flip one bit in one element
        bad = list(sig)
        bad[0] = bytes([bad[0][0] ^ 0x01]) + bad[0][1:]
        tamper_ok = not repaired_verify(msg, bad, pk, p)
        # wrong message
        wrong_ok = not repaired_verify(b"wrong message", sig, pk, p)
        # truncation: drop last element
        trunc_ok = not repaired_verify(msg, sig[:-1], pk, p)
        results[f"w={w}"] = {
            "roundtrip_ok": ok,
            "endpoint_recovery_ok": rec_ok,
            "tamper_rejected": tamper_ok,
            "wrong_message_rejected": wrong_ok,
            "truncation_rejected": trunc_ok,
        }
    return results


# ---------------------------------------------------------------------------
# 6. Deterministic local regression vector (kat_wots.json)
# ---------------------------------------------------------------------------
def kat_check() -> dict:
    kat = json.loads((OUT / "experiments" / "kat_wots.json").read_text())
    # Rebuild the key pair from the saved secret (legacy defective algorithm).
    from wots import WOTSKeyPair
    sk = [bytes.fromhex(kat["sk_hex"][i:i + 64]) for i in range(0, len(kat["sk_hex"]), 64)]
    pk = [bytes.fromhex(kat["pk_hex"][i:i + 64]) for i in range(0, len(kat["pk_hex"]), 64)]
    kp = WOTSKeyPair(sk=sk, pk=pk)
    msg = bytes.fromhex(kat["msg_hex"])
    sig = [bytes.fromhex(kat["sig_hex"][i:i + 64]) for i in range(0, len(kat["sig_hex"]), 64)]
    ok = WOTSKeyPair.verify(msg, sig, kp.pk)
    tamper = not WOTSKeyPair.verify(msg, [sig[0][:-1] + bytes([sig[0][-1] ^ 1])] + sig[1:], kp.pk)
    return {
        "algorithm": kat["algorithm"],
        "seed": kat["seed"],
        "roundtrip_ok": ok,
        "tamper_rejected": tamper,
        "pk_prefix_hex": pk[0][:32].hex(),
        "note": "local regression vector for the defective algorithm, not a NIST conformance vector",
    }


def main():
    results = {
        "table2_checksum_defect": table2(),
        "table4_exact_chain_work": table4(),
        "table5_exact_checksum_expectation": table5(),
        "byte_accounting": byte_accounting(),
        "repaired_checks": repaired_checks(),
        "kat_check": kat_check(),
    }
    out = OUT / "audit" / "audit_jce.json"
    out.write_text(json.dumps(results, indent=2))
    print("[written]", out)
    # Console summary
    for row in results["table2_checksum_defect"]["rows"]:
        print(f"w={row['w']:>3} checksum={row['checksum']:>5} "
              f"legacy={row['legacy_encoded_digits']} "
              f"intended={row['intended_digits']} defect={row['defect_confirmed']}")
    for row in results["table4_exact_chain_work"]["rows"]:
        print(f"w={row['w']:>3} sign={row['sign_chain_calls']:>5} "
              f"verify={row['verify_chain_calls']:>5} "
              f"keygen={row['keygen_chain_calls']:>5} "
              f"legacy_avg={row['legacy_average']}")
    for row in results["table5_exact_checksum_expectation"]["rows"]:
        print(f"w={row['w']:>3} E[checksum]={row['expected_checksum_digit_sum']:<12.6f} "
              f"corrected={row['corrected_expected_sign_calls']:<12.6f} "
              f"approx={row['approximation_L(w-1)/2']}")
    print("[repaired]", json.dumps(results["repaired_checks"]))
    print("[kat]", json.dumps(results["kat_check"]))


if __name__ == "__main__":
    main()
