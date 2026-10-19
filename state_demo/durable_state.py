"""
durable_state.py — minimal durable, crash-safe one-time-key allocator.

This is a *demo* of the operational requirements discussed in the paper's
state-management section, not a production wallet. It implements:

  * reserve-before-release: a leaf is committed to durable storage before the
    signature is produced, so a crash can burn a leaf but can never reuse one;
  * an append-only hash-chained log: each entry commits to the previous hash,
    so truncation or modification is detected on load;
  * atomic head updates (write temp + fsync + rename);
  * a separate high-water mark: detects restoring an older state directory
    (partial rollback);
  * an exclusive file lock: concurrent signers draw distinct leaves.

Residual limitation (stated in the paper): rolling back *all* local state,
including the high-water mark, is not detectable without a trusted monotonic
anchor (secure element, remote transparency log, or hardware counter). The
demo deliberately does not pretend otherwise.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

try:
    import fcntl  # POSIX only
except ImportError:  # pragma: no cover
    fcntl = None


class StateError(RuntimeError):
    pass


class TamperDetected(StateError):
    pass


class RollbackDetected(StateError):
    pass


class ReuseDenied(StateError):
    pass


class CapacityExhausted(StateError):
    pass


ZERO = "00" * 32


def _hash(prev_hex: str, leaf: int) -> str:
    return hashlib.sha256(bytes.fromhex(prev_hex) + leaf.to_bytes(4, "big")).hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class DurableState:
    def __init__(self, state_dir, capacity: int, hwm_path=None):
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.capacity = capacity
        self.log = self.dir / "consumed.log"
        self.head = self.dir / "head.json"
        self.lockfile = self.dir / "lock"
        self.hwm = (Path(hwm_path) if hwm_path is not None
                    else self.dir.parent / (self.dir.name + ".hwm"))
        self.entries: list[dict] = []
        self._lock_fd = None
        # Loading happens under the exclusive lock in __enter__ so that a
        # concurrent appender cannot expose a partially written log line.

    # -- locking --------------------------------------------------------
    def __enter__(self):
        if fcntl is not None:
            self._lock_fd = open(self.lockfile, "a+")
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX)
        self._reload(heal=True)
        return self

    def __exit__(self, *exc):
        if self._lock_fd is not None:
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
            self._lock_fd.close()
            self._lock_fd = None

    # -- load / verify --------------------------------------------------
    def _reload(self, heal: bool) -> None:
        entries: list[dict] = []
        prev = ZERO
        if self.log.exists():
            for line in self.log.read_text().splitlines():
                if not line.strip():
                    continue
                e = json.loads(line)
                if e.get("prev") != prev:
                    raise TamperDetected("hash-chain prev mismatch")
                h = _hash(prev, int(e["leaf"]))
                if e.get("hash") != h:
                    raise TamperDetected("hash-chain entry mismatch")
                entries.append(e)
                prev = h

        last_seq = len(entries)
        last_hash = entries[-1]["hash"] if entries else ZERO

        if self.head.exists():
            head = json.loads(self.head.read_text())
            if head["seq"] > last_seq:
                raise TamperDetected("log truncated below the committed head")
            if head["seq"] < last_seq:
                # crash after appending the log but before updating the head:
                # the fsynced log is authoritative, so heal the head forward.
                if heal:
                    self._write_head(last_seq, last_hash)
            elif head["hash"] != last_hash:
                raise TamperDetected("head hash mismatch")
        elif heal:
            self._write_head(last_seq, last_hash)

        if self.hwm.exists():
            hwm = int(self.hwm.read_text().strip() or "0")
            if last_seq < hwm:
                raise RollbackDetected(
                    f"state at seq {last_seq} is older than high-water mark {hwm}")
            if last_seq > hwm and heal:
                self._write_hwm(last_seq)
        elif heal:
            self._write_hwm(last_seq)

        self.entries = entries

    # -- writes ---------------------------------------------------------
    def _write_head(self, seq: int, h: str) -> None:
        _atomic_write(self.head, json.dumps({"seq": seq, "hash": h}))

    def _write_hwm(self, seq: int) -> None:
        _atomic_write(self.hwm, str(seq))

    # -- public API -----------------------------------------------------
    def used_leaves(self) -> set[int]:
        return {int(e["leaf"]) for e in self.entries}

    def _append(self, leaf: int) -> int:
        used = self.used_leaves()
        if leaf in used:
            raise ReuseDenied(f"leaf {leaf} already consumed")
        if not (0 <= leaf < self.capacity):
            raise ReuseDenied(f"leaf {leaf} out of range 0..{self.capacity - 1}")
        if len(used) >= self.capacity:
            raise CapacityExhausted("all leaves consumed")

        seq = len(self.entries) + 1
        prev = self.entries[-1]["hash"] if self.entries else ZERO
        e = {"seq": seq, "leaf": leaf, "prev": prev, "hash": _hash(prev, leaf)}
        # commit point: append + fsync the log, then the high-water mark, then
        # the head. A crash at any point leaves the leaf consumed (safe).
        with open(self.log, "a") as f:
            f.write(json.dumps(e) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self._write_hwm(seq)
        self._write_head(seq, e["hash"])
        self.entries.append(e)
        return leaf

    def reserve(self) -> int:
        """Reserve the smallest unused leaf and commit it durably *before*
        returning. The caller may sign only after this returns."""
        used = self.used_leaves()
        if len(used) >= self.capacity:
            raise CapacityExhausted("all leaves consumed")
        leaf = next(i for i in range(self.capacity) if i not in used)
        return self._append(leaf)

    def reserve_specific(self, leaf: int) -> int:
        """Request a specific leaf; used to demonstrate reuse rejection."""
        return self._append(leaf)
