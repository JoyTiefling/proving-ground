#!/usr/bin/env python3
"""
CITATION CENSUS — every sha16 quoted in prose, resolved against what is on disk.

WHY (measured 30-08, on this repo).
`core_digest.py` (27-08) fixed one rotted pointer: prose cited the 02-08 run
sha for a core that had been re-run 14-08. The fix was real. But the fix was
found by walking ONE trajectory — the c=4 cover claim — and the list it
produced is the shape of that walk, not the shape of the defect. So I did the
census by construction instead of by memory: collect EVERY 16-hex token in the
prose, resolve each against every receipt on disk.

Two things the walk had missed:

1. `core_sha16` is quoted 6× in prose and stored NOWHERE. It is recomputable
   from the receipt — and on 30-08 it still reproduced — but nothing on disk
   holds it, and nothing recomputes it. The second carrier built to stop the
   pointer rotting had itself no carrier: if the core moved tomorrow, the six
   citations would keep reading true. This script IS that carrier, and it is
   deliberately a RECOMPUTATION, not a stored field: a stored digest rots the
   same way the sha did, a recomputed one cannot.

2. Citations of a superseded run are marked `[archived-on-purpose]` in
   log/weak-schur.md and were never marked in projects/frontier/STATE.md.
   The convention existed; nothing enforced it; the unmarked one had no red
   state. A convention with no gate is a habit, and habits are not carriers.

RED (exit 1) when a quoted sha16:
  - resolves to a SUPERSEDED receipt on a line not marked [archived-on-purpose]
  - resolves to nothing at all (dead pointer, or a core that has moved)

Green is not allowed to say "all clear": it prints what it did NOT check.

  python search/citation_census.py            # census + gate
  python search/citation_census.py --verbose  # also list every resolved token
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

SHA16 = re.compile(r"(?<![0-9a-f])[0-9a-f]{16}(?![0-9a-f])")
EXEMPT = "[archived-on-purpose]"

# Prose that makes a CURRENT claim: it says "the measurement is this run". A
# pointer here must still point. Gated. The joy coordinator lives outside the
# repo and is in the list on purpose — it carried the citation that rotted.
PROSE = [
    "log/weak-schur.md",
    "../../projects/frontier/STATE.md",
]

# Prose that records a MOMENT: on 02-08 I really did cite the 02-08 run, and
# that sentence stays true forever. Repointing it would be falsifying a diary.
# So these are counted and printed, never gated — and printed precisely so the
# count never quietly drops to zero because someone "tidied" the journals.
RECORDS = [
    "../../journal/2026-08-02.md",
    "../../journal/2026-08-14.md",
    "../../journal/2026-08-27.md",
]


def load_receipts():
    """(live, superseded, cores) — sha16 -> [filenames], plus core digests."""
    sys.path.insert(0, HERE)
    from core_digest import core_of, digest  # reuse: one definition of "core"

    live, sup, cores = {}, {}, {}
    for path, bucket in (("search/out/*.json", live),
                         ("search/out/superseded/*.json", sup)):
        for f in sorted(glob.glob(os.path.join(REPO, path))):
            try:
                d = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            sha = d.get("sha16")
            if sha:
                bucket.setdefault(sha, []).append(os.path.basename(f))
            if bucket is live and d.get("core_triples"):
                try:
                    _, core, claim = core_of(f)
                except SystemExit:
                    continue
                cores.setdefault(digest(core, claim), []).append(os.path.basename(f))
    return live, sup, cores


def cited_tokens(docs):
    """[(token, doc, lineno, exempt)] for every sha16 quoted in prose."""
    out, missing = [], []
    for rel in docs:
        path = os.path.normpath(os.path.join(REPO, rel))
        if not os.path.exists(path):
            missing.append(rel)
            continue
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                for tok in SHA16.findall(line):
                    out.append((tok, rel, n, EXEMPT in line))
    return out, missing


def census(docs=PROSE):
    live, sup, cores = load_receipts()
    cites, missing_docs = cited_tokens(docs)

    findings, resolved = [], []
    for tok, doc, n, exempt in cites:
        if tok in live:
            resolved.append((tok, doc, n, "run", live[tok][0]))
        elif tok in cores:
            resolved.append((tok, doc, n, "core", cores[tok][0]))
        elif tok in sup:
            resolved.append((tok, doc, n, "superseded", sup[tok][0]))
            if not exempt:
                findings.append((doc, n, tok,
                                 "cites SUPERSEDED %s without %s" % (sup[tok][0], EXEMPT)))
        else:
            findings.append((doc, n, tok, "resolves to NOTHING on disk"))
    return live, sup, cores, cites, resolved, findings, missing_docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--docs", nargs="*", default=None,
                    help="override the prose list (for tests / mutants)")
    args = ap.parse_args()

    live, sup, cores, cites, resolved, findings, missing_docs = census(
        args.docs if args.docs is not None else PROSE)

    print("receipts on disk : %d live, %d superseded, %d core digests recomputed"
          % (len(live), len(sup), len(cores)))
    print("prose scanned    : %d document(s), %d citations, %d distinct"
          % (len(args.docs if args.docs is not None else PROSE),
             len(cites), len({c[0] for c in cites})))
    if missing_docs:
        print("  !! prose document(s) not found: %s" % ", ".join(missing_docs))

    if args.verbose:
        for tok, doc, n, kind, fn in sorted(resolved, key=lambda r: (r[3], r[0])):
            print("  %-16s %-11s %s  (%s:%d)" % (tok, kind, fn, doc, n))

    if findings:
        print("\nRED — %d citation(s) with no live referent:" % len(findings))
        for doc, n, tok, why in findings:
            print("  %s:%d  %s  %s" % (doc, n, tok, why))
    else:
        print("\nGREEN for exactly this: every sha16 quoted in the listed prose "
              "resolves to a receipt on disk, superseded ones only where marked.")

    # Records: counted, never gated. A journal entry citing a run that has
    # since been superseded is not rot — it is what was true when written.
    live_r, sup_r, cores_r = load_receipts()
    rec_cites, rec_missing = cited_tokens(RECORDS)
    if rec_cites:
        historical = sum(1 for tok, *_ in rec_cites if tok in sup_r)
        print("\nrecords (NOT gated): %d citation(s) in %d diary document(s); "
              "%d name a since-superseded run — correct as written, do not repoint."
              % (len(rec_cites), len(RECORDS) - len(rec_missing), historical))
    if rec_missing:
        print("  !! record document(s) not found: %s" % ", ".join(rec_missing))

    # A green screen is not permitted to imply more than it measured (#3961).
    uncited = sorted(set(live) - {c[0] for c in cites})
    print("\nNOT checked by this run:")
    print("  - prose outside %s" % ", ".join(args.docs if args.docs is not None else PROSE))
    print("  - whether a resolved receipt's MATH is right (only its identity)")
    print("  - %d live receipt(s) no prose cites at all: %s"
          % (len(uncited), ", ".join(live[s][0] for s in uncited[:6]) or "none"))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
