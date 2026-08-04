#!/usr/bin/env python3
"""Receipt verifier — re-checks published sha16 across the whole corpus.

WHY THIS EXISTS
---------------
`receipts.py` carries a VERIFIER NOTE documenting exactly ONE re-hash
procedure (indent=2, ensure_ascii=False, sort_keys=True, sha16 popped).
That note is the only instruction a reader has. Measured 05-08, it
reproduces the stored sha16 of *some* receipts and not others, because
scripts written before `receipts.py` existed embedded their own inline
hashing and each picked different `json.dumps` kwargs:

    search/out/w76.json                        indent=2, no sort_keys
    search/out/case_tree_cover_*.json          sort_keys, no indent
    receipts.write_receipt (current default)   indent=2, ensure_ascii=False, sort_keys

A reader following the documented procedure concludes that two thirds of
my receipts are corrupt. They are not — the note is narrower than the
corpus. The shared element (`receipts.py`'s note) is read by consumers
whose files it never produced.

TWO CLAIMS, DELIBERATELY SEPARATED
----------------------------------
A receipt citation "sha16=X" has been doing double duty. It carries two
different claims with different lifetimes, and only one of them is true:

  (a) INTEGRITY — the file on disk still hashes to the sha16 it carries.
      Checkable forever, offline, by anyone, from the file alone.

  (b) REPRODUCIBILITY — rerunning the script reproduces that sha16.
      FALSE for every receipt here: `elapsed_s` (wall-clock seconds) sits
      inside the hashed object, so the next run hashes differently no
      matter how deterministic the mathematics is.

This tool asserts (a) and *reports* (b) rather than quietly implying it.
Volatile-field detection is a claim about the receipt, not a failure:
integrity can hold while reproducibility cannot.

WHAT IT DOES NOT DO
-------------------
It does not rewrite any receipt and does not change any hashing scheme.
Every sha16 already cited in STATE.md and in the prose stays exactly as
published; the fix is to make the corpus *checkable*, not to make it
prettier. Renaming the scheme would silently orphan published numbers —
the same trade already made once in `receipts.py` (compatibility beats
elegance) and made again here for the same reason.
"""

import argparse
import glob
import hashlib
import json
import os
import sys

# Registry, not a chain of ifs: new scripts may arrive with new kwargs, and
# a reader needs to see the full set of accepted procedures in one place.
SCHEMES = {
    # name                      json.dumps kwargs
    "i2_ea0_sk": dict(indent=2, ensure_ascii=False, sort_keys=True),
    "i2_sk":     dict(indent=2, sort_keys=True),
    "i2":        dict(indent=2),
    "sk":        dict(sort_keys=True),
    # sat_verify_partition.py / analyze_forced_same_orbits.py hash a COMPACT
    # payload and then write the file pretty-printed. The file therefore never
    # looks like what was hashed — found 05-08 only because the verifier
    # refused rather than shrugged.
    "compact_sk": dict(sort_keys=True, separators=(",", ":")),
    "i1_sk":     dict(indent=1, sort_keys=True),
    "i1":        dict(indent=1),
    "plain":     dict(),
}

# The procedure documented in receipts.py. Named so the gap between
# "documented" and "accepted" is visible rather than folded away.
DOCUMENTED_SCHEME = "i2_ea0_sk"

# Fields whose value changes between two runs of the same deterministic
# computation. Presence inside the hashed object kills claim (b).
VOLATILE_FIELDS = ("elapsed_s", "elapsed_s_total", "total_elapsed_s", "started")


def as_loaded(obj):
    """Identity — the key domain you get by reading the file back."""
    return obj


def int_keys_restored(obj):
    """Digit-string keys back to ints, recursively.

    JSON has no integer keys: `json.dumps` coerces them to strings. When the
    producer hashed a dict keyed by ints under `sort_keys=True`, the ordering
    was NUMERIC (1, 3, 11, 45); after the round-trip the same keys are strings
    and sort LEXICOGRAPHICALLY (1, 11, 3, 45). The file is therefore a lossy
    image of the object that was hashed, and no choice of dumps-kwargs can
    reproduce the sha16 from the file alone.

    Found 05-08 on sat_verify_partition_run1.json (3669e88c7ec427c6) — the
    rigid provenance the whole cover argument cites. It is intact; it was
    simply unverifiable by every procedure I had written down.
    """
    if isinstance(obj, dict):
        return {(int(k) if isinstance(k, str) and k.lstrip("-").isdigit() else k):
                int_keys_restored(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [int_keys_restored(v) for v in obj]
    return obj


# Second axis, orthogonal to SCHEMES. "Scheme" was one word holding two
# different things — serialization kwargs and key domain — and the second
# was invisible until a receipt failed for a reason the first could not
# express. Kept as its own registry so the next hidden axis has somewhere
# to land instead of being folded into a special case.
KEY_DOMAINS = {
    "as_loaded": as_loaded,
    "int_keys": int_keys_restored,
}


def rehash(payload, scheme, key_domain="as_loaded"):
    """sha16 of the payload under a named scheme and key domain."""
    if scheme not in SCHEMES:
        raise KeyError(f"unknown scheme: {scheme}")
    if key_domain not in KEY_DOMAINS:
        raise KeyError(f"unknown key domain: {key_domain}")
    obj = KEY_DOMAINS[key_domain](payload)
    blob = json.dumps(obj, **SCHEMES[scheme]).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def volatile_in(obj, _depth=0):
    """Volatile field names present anywhere in the hashed object."""
    found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in VOLATILE_FIELDS:
                found.add(k)
            found |= volatile_in(v, _depth + 1)
    elif isinstance(obj, list) and _depth < 3:
        for v in obj:
            found |= volatile_in(v, _depth + 1)
    return found


def verify(path):
    """Verify one receipt.

    Returns a dict with:
      stored     — sha16 the file carries (None if absent)
      scheme     — name of the scheme reproducing it, or None
      integrity  — bool: some known scheme reproduces the stored sha16
      volatile   — sorted volatile field names inside the hashed object
      reproducible — bool: integrity AND no volatile field is hashed
    """
    res = {"path": path, "stored": None, "scheme": None, "key_domain": None,
           "integrity": False, "volatile": [], "reproducible": False, "note": ""}
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as exc:                       # noqa: BLE001
        res["note"] = f"unreadable: {exc}"
        return res
    if not isinstance(doc, dict):
        res["note"] = "not a JSON object"
        return res
    if doc.get("status") == "in_progress":
        res["note"] = "in_progress stub — run was killed, not a receipt"
        return res
    if "sha16" not in doc:
        res["note"] = "no sha16 field"
        return res

    res["stored"] = doc["sha16"]
    payload = {k: v for k, v in doc.items() if k != "sha16"}
    for dom in KEY_DOMAINS:
        for name in SCHEMES:
            if rehash(payload, name, dom) == doc["sha16"]:
                res["scheme"] = name
                res["key_domain"] = dom
                res["integrity"] = True
                break
        if res["integrity"]:
            break
    res["volatile"] = sorted(volatile_in(payload))
    res["reproducible"] = res["integrity"] and not res["volatile"]
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", default=None,
                    help="receipt files or globs; default = search/out/*.json")
    ap.add_argument("--self-test", action="store_true",
                    help="run the gate's own mutants and exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    pats = args.paths or [os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "out", "*.json")]
    files = []
    for p in pats:
        files.extend(sorted(glob.glob(p)) if any(c in p for c in "*?[") else [p])
    if not files:
        print("no receipts matched", file=sys.stderr)
        return 2

    rows = [verify(p) for p in files]
    broken = [r for r in rows if r["stored"] and not r["integrity"]]
    skipped = [r for r in rows if not r["stored"]]
    by_scheme = {}
    for r in rows:
        if r["scheme"]:
            by_scheme[r["scheme"]] = by_scheme.get(r["scheme"], 0) + 1

    for r in rows:
        if not r["stored"]:
            mark, tail = "  --", r["note"]
        elif not r["integrity"]:
            mark, tail = "FAIL", "no known scheme reproduces stored sha16"
        else:
            mark = "  ok"
            tail = f"scheme={r['scheme']}"
            if r["volatile"]:
                tail += f"  [not reproducible: hashes {','.join(r['volatile'])}]"
        print(f"{mark}  {os.path.basename(r['path']):<58} {tail}")

    total = len(rows) - len(skipped)
    repro = sum(1 for r in rows if r["reproducible"])
    doc_ok = by_scheme.get(DOCUMENTED_SCHEME, 0)
    print(f"\n  receipts: {total} verifiable, {len(skipped)} skipped, "
          f"{len(broken)} broken")
    print(f"  schemes in use: {by_scheme}")
    print(f"  documented procedure ({DOCUMENTED_SCHEME}) covers "
          f"{doc_ok}/{total} — the rest need this tool to be checkable")
    print(f"  reproducible by rerun: {repro}/{total} "
          f"(the gap is wall-clock fields inside the hashed object)")
    return 1 if broken else 0


def self_test():
    """Mutants. Each must be red for its own reason, control green."""
    import tempfile

    def write(doc, scheme):
        payload = {k: v for k, v in doc.items() if k != "sha16"}
        doc = dict(doc)
        doc["sha16"] = rehash(payload, scheme)
        fd, p = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(doc, f, **SCHEMES[scheme])
        return p, doc

    fails = []

    def check(name, cond, why):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}: {why}")
        if not cond:
            fails.append(name)

    # Positive control: a clean receipt with no volatile field verifies
    # under every scheme it was written with, and counts as reproducible.
    for scheme in SCHEMES:
        p, _ = write({"script": "x", "leaves": 76, "b": {"z": 1, "a": 2}}, scheme)
        r = verify(p)
        os.unlink(p)
        check(f"C1[{scheme}]", r["integrity"] and r["reproducible"],
              f"clean receipt written as {scheme} verifies (got {r['scheme']})")

    # M1 — one byte of the payload changed after hashing. Integrity must die.
    p, doc = write({"script": "x", "leaves": 76}, "i2_ea0_sk")
    doc["leaves"] = 77
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, **SCHEMES["i2_ea0_sk"])
    r = verify(p)
    os.unlink(p)
    check("M1", not r["integrity"], "tampered payload no longer verifies")

    # M2 — sha16 itself edited. Integrity must die.
    p, doc = write({"script": "x", "leaves": 76}, "i2_ea0_sk")
    doc["sha16"] = "0" * 16
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, **SCHEMES["i2_ea0_sk"])
    r = verify(p)
    os.unlink(p)
    check("M2", not r["integrity"], "edited sha16 no longer verifies")

    # M3 — a receipt hashing elapsed_s: integrity holds, reproducibility must not.
    # This is the whole point of splitting the two claims; a tool that only
    # asserted integrity would call this receipt fine.
    p, _ = write({"script": "x", "leaves": 76, "elapsed_s": 7.845}, "i2_ea0_sk")
    r = verify(p)
    os.unlink(p)
    check("M3", r["integrity"] and not r["reproducible"] and r["volatile"] == ["elapsed_s"],
          "volatile field: integrity ok, reproducibility refused")

    # M4 — volatile field nested one level down must still be caught.
    p, _ = write({"script": "x", "runs": {"a": {"elapsed_s": 1.0}}}, "i2_ea0_sk")
    r = verify(p)
    os.unlink(p)
    check("M4", r["integrity"] and not r["reproducible"],
          "nested volatile field caught")

    # M5 — an in_progress stub is not a receipt and must not be counted ok.
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"status": "in_progress", "started": "2026-08-05T06:00:00Z"}, f)
    r = verify(p)
    os.unlink(p)
    check("M5", not r["integrity"] and "in_progress" in r["note"],
          "killed-run stub reported as stub, not as broken receipt")

    # M6 — the registry must not be a wildcard. An unknown scheme is an
    # error, not a silent miss: a verifier that accepts anything passes
    # everything, which is a check unable to fail.
    try:
        rehash({"a": 1}, "no_such_scheme")
        ok = False
    except KeyError:
        ok = True
    check("M6", ok, "unknown scheme raises instead of silently returning")

    # M8 — the int-key axis must be load-bearing, not decoration. Build the
    # receipt the way sat_verify_partition.py did: hash a dict with INTEGER
    # keys spanning one and two digits (so numeric and lexicographic order
    # genuinely differ), then write it — JSON turns the keys into strings.
    # Required: as_loaded cannot reproduce it, int_keys can. Delete
    # int_keys_restored and this goes red; that is the point.
    doc = {"roots": {1: "a", 3: "b", 11: "c", 45: "d"}, "script": "x"}
    sha = rehash(doc, "compact_sk", "int_keys")
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    doc_out = dict(doc)
    doc_out["sha16"] = sha
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc_out, f, indent=2, sort_keys=True)
    reloaded = json.load(open(p, encoding="utf-8"))
    pay = {k: v for k, v in reloaded.items() if k != "sha16"}
    as_is = rehash(pay, "compact_sk", "as_loaded")
    r = verify(p)
    os.unlink(p)
    check("M8", as_is != sha and r["integrity"] and r["key_domain"] == "int_keys",
          "int-key receipt: unverifiable as loaded, verifiable with keys restored")

    # M9 — restoring keys must not be a universal solvent. A receipt whose
    # keys were strings all along must still verify as as_loaded, otherwise
    # the axis would be quietly relabelling every receipt it touches.
    p, _ = write({"roots": {"1": "a", "11": "b", "3": "c"}}, "compact_sk")
    r = verify(p)
    os.unlink(p)
    check("M9", r["integrity"] and r["key_domain"] == "as_loaded",
          "string-keyed receipt still resolves as as_loaded, not relabelled")

    # M7 — a receipt written under a scheme NOT in the registry must fail,
    # otherwise "some scheme matched" degenerates into "any file passes".
    doc = {"script": "x", "leaves": 76}
    blob = json.dumps(doc, indent=7, separators=(" , ", " : ")).encode()
    doc["sha16"] = hashlib.sha256(blob).hexdigest()[:16]
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    r = verify(p)
    os.unlink(p)
    check("M7", not r["integrity"], "off-registry scheme is not accepted")

    print(f"\n  self-test: {'PASS' if not fails else 'FAIL ' + ','.join(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
