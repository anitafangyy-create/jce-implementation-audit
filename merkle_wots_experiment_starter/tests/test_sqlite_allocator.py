import tempfile
import threading
import unittest
from pathlib import Path

from src.sqlite_allocator import SQLiteAllocator


class AllocatorTests(unittest.TestCase):
    def test_sequential_unique(self):
        with tempfile.TemporaryDirectory() as d:
            a = SQLiteAllocator(Path(d) / "state.sqlite")
            got = [a.reserve() for _ in range(100)]
            self.assertEqual(got, list(range(100)))
            self.assertEqual(a.next_index(), 100)

    def test_concurrent_unique(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.sqlite"
            workers, each = 8, 100
            barrier = threading.Barrier(workers)
            out, errors = [], []
            lock = threading.Lock()

            def worker():
                try:
                    allocator = SQLiteAllocator(path)
                    barrier.wait()
                    local = [allocator.reserve() for _ in range(each)]
                    with lock:
                        out.extend(local)
                except Exception as exc:
                    with lock:
                        errors.append(repr(exc))

            threads = [threading.Thread(target=worker) for _ in range(workers)]
            for t in threads: t.start()
            for t in threads: t.join()

            self.assertEqual(errors, [])
            self.assertEqual(len(out), workers * each)
            self.assertEqual(len(set(out)), workers * each)
            self.assertEqual(sorted(out), list(range(workers * each)))


if __name__ == "__main__":
    unittest.main()
