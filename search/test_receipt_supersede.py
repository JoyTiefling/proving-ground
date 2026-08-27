"""Gate for receipts.supersede() — a rerun must never cost a published anchor.

Origin (14-08 14:00). Receipts are the anchors of every claim in this repo:
prose cites sha16, and that sha16 is verifiable only if the byte-image still
exists. Two facts lived here separately and never met:

  - the auto path is derived from run parameters, so a rerun overwrites its
    predecessor (documented as a feature: "rather than littering");
  - receipt reproducibility is 1/18 (measured 05-08) — elapsed_s and the wake
    stamp are inside the hash, so an overwritten receipt is NOT regenerable.

Together: any rerun silently and permanently destroys a published anchor.
Confirmed live — a *control* rerun killed 36dfed9cbac60b3e two minutes into  # [archived-on-purpose]
the wake. It was recoverable only because the original scalars happened to be
on screen; an accident, not a device.

Every test below fails on the pre-14-08 receipts.py (no supersede()) — that is
the point of writing them. M0 is the positive control on the gate itself.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import receipts  # noqa: E402


class _Args:
    def __init__(self, out):
        self.out = out
        self.no_out = False


def _superseded_dir(out_path):
    return os.path.join(os.path.dirname(out_path), "superseded")


def _archived(out_path):
    d = _superseded_dir(out_path)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


class SupersedeGate(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "run.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, elapsed):
        """One completed run landing on the shared auto path."""
        receipts.probe_writable(self.path)
        sha = receipts.write_receipt(
            self.path, {"claim": "X is UNSAT", "mus_size": 85,
                        "elapsed_s": elapsed})
        return sha

    # ---- M0: positive control on the gate itself -----------------------
    def test_M0_the_two_runs_really_do_differ(self):
        """If reruns produced identical images there would be nothing to lose,
        and every test below would pass vacuously. Establish the premise."""
        first = self._write(2.296)
        second = self._write(1.290)
        self.assertNotEqual(first, second,
                            "reruns must differ, else the whole gate is vacuous")

    # ---- the anchor survives -------------------------------------------
    def test_prior_receipt_is_archived_under_its_own_sha16(self):
        first = self._write(2.296)
        with open(self.path, "rb") as f:
            original_bytes = f.read()
        self._write(1.290)

        dest = os.path.join(_superseded_dir(self.path), f"run.{first}.json")
        self.assertTrue(os.path.exists(dest),
                        f"anchor {first} destroyed by the rerun; archived={_archived(self.path)}")
        with open(dest, "rb") as f:
            self.assertEqual(f.read(), original_bytes,
                             "archive must be the byte-image — the image IS the anchor")
        # and it still hashes to the sha16 it is filed under
        d = json.loads(original_bytes.decode("utf-8"))
        self.assertEqual(d["sha16"], first)

    def test_reservation_alone_does_not_cost_the_anchor(self):
        """A rerun that CRASHES before finishing must not cost anything either:
        probe_writable() clobbers the path first in time, so it is the first
        place the predecessor can die."""
        first = self._write(2.296)
        receipts.probe_writable(self.path)          # crash right here
        dest = os.path.join(_superseded_dir(self.path), f"run.{first}.json")
        self.assertTrue(os.path.exists(dest),
                        "a crashed rerun destroyed the anchor at reservation time")

    def test_stub_is_not_archived(self):
        """An in_progress stub is a reservation, not a result. Archiving it
        would fill the archive with non-anchors and hide the real ones."""
        receipts.probe_writable(self.path)
        receipts.probe_writable(self.path)
        self.assertEqual(_archived(self.path), [],
                         "reservations must not be archived as results")

    def test_supersede_is_idempotent(self):
        first = self._write(2.296)
        receipts.supersede(self.path)
        receipts.supersede(self.path)
        self.assertEqual(_archived(self.path), [f"run.{first}.json"])

    def test_rerun_is_never_refused(self):
        """Correction through interest, not pain: re-verification is the
        behaviour I want more of. A tool that refuses or errors on a rerun
        teaches me not to check. Nothing is refused; nothing is lost."""
        self._write(2.296)
        sha = self._write(1.290)                    # must simply work
        self.assertTrue(sha)
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["sha16"], sha,
                             "the rerun's own receipt must land normally")

    def test_write_receipt_alone_still_archives(self):
        """The precondition the other tests get for free.

        Every test above goes through _write(), which calls probe_writable()
        first — and probe_writable() archives. So they all prove "the anchor
        survives IF the path was reserved", and none of them can see whether
        write_receipt() protects anything on its own. Mutant M1 (14-08) —
        deleting supersede() from write_receipt() — survived all seven of
        them for exactly that reason, while receipts.py claims in prose that
        scripts skipping probe_writable() are covered. Five of the repo's
        scripts predate that helper. This test asks the question the fixture
        makes unaskable: it never reserves."""
        receipts.probe_writable(self.path)
        first = receipts.write_receipt(self.path, {"claim": "X", "elapsed_s": 2.296})
        receipts.write_receipt(self.path, {"claim": "X", "elapsed_s": 1.290})
        dest = os.path.join(_superseded_dir(self.path), f"run.{first}.json")
        self.assertTrue(os.path.exists(dest),
                        "write_receipt() alone destroyed the anchor; "
                        f"archived={_archived(self.path)}")

    def test_unreadable_predecessor_does_not_abort_the_run(self):
        """Expensive work must never be lost to a damaged predecessor."""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{ this is not json")
        self.assertIsNone(receipts.supersede(self.path))
        self.assertTrue(self._write(1.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
