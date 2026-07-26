"""Tests for receipts.py — the persist-by-default invariant.

Test 3 is the load-bearing one: it checks that the re-verification procedure
written in write_receipt's docstring actually reproduces the sha16. Receipts
in the canon are only meaningful if that procedure is correct; a wrong
docstring would make every published checksum unverifiable.
"""
import os, json, hashlib, tempfile, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import receipts


def test_probe_reserves_and_makes_dirs():
    tmp = os.path.join(tempfile.mkdtemp(), "sub", "r.json")
    receipts.probe_writable(tmp)
    assert json.load(open(tmp))["status"] == "in_progress"


def test_write_receipt_embeds_sha():
    tmp = os.path.join(tempfile.mkdtemp(), "r.json")
    sha = receipts.write_receipt(tmp, {"claim": "MUS", "triples": 699})
    d = json.load(open(tmp))
    assert d["sha16"] == sha and d["triples"] == 699


def test_docstring_verifier_reproduces_sha():
    tmp = os.path.join(tempfile.mkdtemp(), "r.json")
    sha = receipts.write_receipt(tmp, {"claim": "MUS", "roots": 44})
    d = json.load(open(tmp)); d.pop("sha16")
    recomputed = hashlib.sha256(json.dumps(
        d, indent=2, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    assert recomputed == sha


def test_no_out_discards():
    class A: out = ""; no_out = True
    assert receipts.resolve_out(A(), __file__, N=90) == ""


def test_default_persists():
    """The actual bug: absent flags must KEEP the result, not drop it."""
    class B: out = ""; no_out = False
    p = receipts.resolve_out(B(), "/x/search/mus_forced_pair.py", pair="35-55", N=90)
    assert p.endswith("mus_forced_pair_N90_pair35-55.json")
    assert os.path.basename(os.path.dirname(p)) == "out"


def test_explicit_out_wins():
    class C: out = "/tmp/explicit.json"; no_out = False
    assert receipts.resolve_out(C(), __file__, N=90) == "/tmp/explicit.json"
