#!/usr/bin/env python3
"""
CONTENT digest of a core-bearing receipt — the thing a citation actually means.

WHY (measured 27-08, on my own published citation).
`receipts._write_receipt` hashes the whole payload, `sha16` included by
exclusion only. That payload carries `wake`, `elapsed_s`, `deletion_order`
and whatever fields the script grew since. So **sha16 identifies a RUN, not
a CORE**: re-run the same minimisation and the sha moves even though not one
triple changed.

Concretely, what made me write this: the c=4 cover-claim core was measured
02-08 (sha `36dfed9cbac60b3e`) and re-run 14-08 (sha `24c378c7df3e11a8`).  # [archived-on-purpose]
Core triples: **identical, symmetric difference 0.** But log/weak-schur.md and
projects/frontier/STATE.md both went on citing the 02-08 sha, and on 27-08 I
copied that stale sha into a fresh entry — describing a measurement whose real
input was the 14-08 file. Nothing mathematical was wrong; the pointer had
rotted while the object stood still.

That failure has no red state under the current scheme. A reader re-verifying
the citation gets a sha mismatch and cannot tell "the core changed" from "the
run was repeated" — the two produce the same screen. This gives the second
carrier: a digest over the mathematical content ALONE.

Stable by construction: sorted, de-duplicated root-tuples, plus the claim
being refuted. Nothing about when, how long, or in what deletion order.

  python search/core_digest.py <receipt.json> [<receipt.json> ...]
  python search/core_digest.py --compare A.json B.json

Exit 1 on --compare when the CONTENT differs (so it can gate a script).
"""
import argparse
import hashlib
import json
import sys


def core_of(path):
    """The mathematical content of a core receipt, in canonical form."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    triples = d.get("core_triples")
    if triples is None:
        raise SystemExit("%s carries no core_triples — not a core receipt" % path)
    core = sorted({tuple(sorted(set(t["distinct_roots"]))) for t in triples})
    # The claim matters: the same triples refuting a different colour or a
    # different pair-set are a different object, and must digest differently.
    claim = {
        "N": d.get("N"),
        "k": d.get("k"),
        "colour": d.get("colour"),
        "pairs": sorted(sorted(p) for p in (d.get("pairs") or [])),
        "arm": d.get("arm") or d.get("rigid_mode"),
    }
    return d, core, claim


def digest(core, claim):
    payload = json.dumps({"claim": claim, "core": [list(t) for t in core]},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("receipts", nargs="+")
    ap.add_argument("--compare", action="store_true",
                    help="exit 1 if the two receipts differ in CONTENT")
    args = ap.parse_args()

    rows = []
    for p in args.receipts:
        d, core, claim = core_of(p)
        rows.append((p, d, digest(core, claim), core))
        print("%s\n  core_sha16 = %s   (run sha16 = %s)\n"
              "  triples=%d  roots=%d  claim=c%s pairs=%s  wake=%s"
              % (p, rows[-1][2], d.get("sha16"), len(core),
                 len({r for t in core for r in t}), claim["colour"],
                 claim["pairs"], d.get("wake")))

    if args.compare:
        if len(rows) != 2:
            raise SystemExit("--compare needs exactly two receipts")
        (_, da, ca, ta), (_, db, cb, tb) = rows
        same_content = ca == cb
        same_run = da.get("sha16") == db.get("sha16")
        print("\ncontent identical : %s" % same_content)
        print("run sha identical : %s" % same_run)
        if same_content and not same_run:
            print("VERDICT: same core, different run. Any citation by run-sha "
                  "is stale but not wrong — repoint it, do not re-measure.")
        elif not same_content:
            print("VERDICT: the cores DIFFER (symmetric difference %d). A "
                  "citation swap here would change the mathematics."
                  % len(set(ta) ^ set(tb)))
        else:
            print("VERDICT: identical receipts.")
        return 0 if same_content else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
