#!/usr/bin/env python3
"""
Audit every run-sha16 CITED in prose against the receipts actually on disk.

WHY (27-08). `receipts._write_receipt` hashes the whole payload — `wake`,
`elapsed_s` and all — so **sha16 names a RUN, not a CORE** (see
`core_digest.py`). A re-run moves the sha while the mathematics stands still,
and every prose citation of the old sha silently rots. On 27-08 I found one
such rotted pointer by following the one branch I happened to be reading
(`mus_cover_claim`, c=4). That list was the trace of MY path, not the class of
the defect (L3 #3936) — so this walks the WHOLE list instead:

  every 16-hex token in the prose  ×  every sha16 in the receipts on disk.

Four verdicts per citation:
  LIVE       — the cited sha is the sha of a current receipt. Fine.
  SUPERSEDED — the cited sha only exists under out/superseded/. ROTTED:
               the object was re-run, the pointer was not repointed.
  UNKNOWN    — no receipt on disk carries that sha at all. Either the file
               was deleted, or the sha was never a receipt sha.
  (tokens that are plainly not receipt shas are reported separately, not
   silently dropped — a filter that hides its remainder cannot go red, #3899.)

Prints the remainder BY NAME in every class. Exit 1 if anything ROTTED.

  python search/citation_audit.py [--roots DIR ...]
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core_digest  # noqa: E402

# A run-sha is hex; a 16-digit all-decimal token is the tail of a float in a
# JSON dump, not a citation. Requiring one hex letter drops that whole class.
HEX16 = re.compile(r"\b(?=[0-9a-f]{16}\b)[0-9a-f]*[a-f][0-9a-f]*\b")
# Receipts are DATA, not prose: a sha inside a receipt is provenance, not a
# citation. Scan the things a reader reads.
PROSE_EXT = {".md", ".txt", ".py"}


def core_shas(repo):
    """core_sha16 -> [paths] recomputed from CONTENT of every core receipt.

    `core_sha16` is never written to disk (checked 27-08: neither receipts.py
    nor any receipt carries the field). It exists only in prose, where I type
    it by hand — which is the very act that rotted the run-sha in the first
    place. It IS derivable from the receipt, so unlike a run-sha it can be
    re-established rather than looked up; this recomputes the whole set so a
    cited core_sha16 can be confirmed or denied WITHOUT trusting the prose.
    """
    out = {}
    for p in glob.glob(os.path.join(repo, "**", "*.json"), recursive=True):
        try:
            _, core, claim = core_digest.core_of(p)
        except (Exception, SystemExit):
            # core_of raises SystemExit on a non-core receipt, and SystemExit
            # is not an Exception — a bare `except Exception` here looked
            # total and killed the whole audit on the first plain json.
            continue
        out.setdefault(core_digest.digest(core, claim), []).append(
            p.replace("\\", "/"))
    return out


def receipt_shas(repo):
    """sha16 -> (path, superseded?) for every receipt json under the repo."""
    live, sup = {}, {}
    pats = [os.path.join(repo, "**", "*.json")]
    for pat in pats:
        for p in glob.glob(pat, recursive=True):
            try:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            s = d.get("sha16")
            if not isinstance(s, str) or not HEX16.fullmatch(s):
                continue
            norm = p.replace("\\", "/")
            (sup if "/superseded/" in norm else live)[s] = norm
    return live, sup


def prose_citations(roots):
    """sha16 -> [(file, line_no, line)] over every prose file in roots."""
    cites = {}
    for root in roots:
        if os.path.isfile(root):
            walk = [(os.path.dirname(root), [], [os.path.basename(root)])]
        else:
            walk = os.walk(root)
        for dirpath, dirnames, filenames in walk:
            dirnames[:] = [d for d in dirnames
                           if d not in (".git", "__pycache__", "node_modules")]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in PROSE_EXT:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, encoding="utf-8") as f:
                        lines = f.readlines()
                except Exception:
                    continue
                for i, line in enumerate(lines, 1):
                    for m in HEX16.findall(line):
                        cites.setdefault(m, []).append(
                            (p.replace("\\", "/"), i, line.strip()[:140]))
    return cites


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=here,
                    help="repo whose receipts define what a sha means")
    ap.add_argument("--roots", nargs="*", default=None,
                    help="dirs/files to scan for citations (default: repo)")
    args = ap.parse_args()
    roots = args.roots or [args.repo]

    live, sup = receipt_shas(args.repo)
    cores = core_shas(args.repo)
    cites = prose_citations(roots)

    # A receipt file citing its OWN sha is not a prose citation.
    def self_cite(sha, path):
        return live.get(sha) == path or sup.get(sha) == path

    rotted, ok, core_ok, unknown = [], [], [], []
    for sha, where in sorted(cites.items()):
        where = [w for w in where if not self_cite(sha, w[0])]
        if not where:
            continue
        if sha in live:
            ok.append((sha, where))
        elif sha in cores:
            core_ok.append((sha, where))
        elif sha in sup:
            rotted.append((sha, where))
        else:
            unknown.append((sha, where))

    print("receipts on disk : %d live, %d superseded, %d distinct cores"
          % (len(live), len(sup), len(cores)))
    print("distinct 16-hex tokens cited in prose: %d" % len(cites))
    print("  LIVE       %d   (names a current receipt RUN)" % len(ok))
    print("  CORE       %d   (recomputed from receipt CONTENT — confirmed)"
          % len(core_ok))
    print("  SUPERSEDED %d   <-- rotted pointers" % len(rotted))
    print("  UNKNOWN    %d   (nothing on disk carries or yields this sha)"
          % len(unknown))

    for title, group in (("ROTTED (cited sha exists only in superseded/)", rotted),
                         ("UNKNOWN (nothing on disk carries or yields this sha)", unknown),
                         ("CORE (cited sha == recomputed content digest)", core_ok),
                         ("LIVE (cited sha == a current receipt)", ok)):
        print("\n=== %s ===" % title)
        if not group:
            print("  (none)")
        for sha, where in group:
            tgt = (sup.get(sha) or live.get(sha)
                   or (" + ".join(cores[sha]) if sha in cores else "-"))
            print("  %s  -> %s" % (sha, tgt))
            for p, i, line in where:
                print("       %s:%d  %s" % (p, i, line))

    return 1 if rotted else 0


if __name__ == "__main__":
    sys.exit(main())
