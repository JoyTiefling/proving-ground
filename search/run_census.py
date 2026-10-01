#!/usr/bin/env python3
"""Run census — does the receipt a log SENTENCE points at carry the best verdict?

WHY THIS EXISTS (measured 02-10-2026, cost: one wake re-running a finished run)
-------------------------------------------------------------------------------
On 24-09 the k=7 climb finished with a verdict:

    search/out/chain_lift_N245_k7_b10M.json   last_sat=212, stalled_at=213,
                                              nine controls green

On 28-09 I asked "was the b10M run ever launched?", looked for
`out/c016_lift_k7_b10M.log`, found nothing, concluded "not launched", and
re-ran the same climb from N=1. It was killed by the end of the wake at
N=205 — forty-one steps BELOW an answer that had been on disk for four days.

The defect does not live in either file. Both are honest:
  * `receipts.resolve_out()` defaults the receipt to `search/out/<auto>.json`;
  * the 28-09 launch passed `--out out/...` explicitly, from the repo root;
  * the prose of `log/weak-schur.md` carries the path as written at the time.
A relative path in prose is not an address. It is an address PLUS the working
directory of whoever launched the run, and that second half was never written
down. So two trees now hold the same basename, one with a verdict and one with
an `in_progress` stub, and no existing check has a state in which it reddens:
the stub exists, parses, and is the file the prose names (#4565 — the defect
lives in the RELATION between carriers; #3961 — a reserved stub and a run that
never happened print the same screen).

WHAT THIS CHECKS
----------------
Input is the relation, not a file: every `*.json` token appearing in prose
(`log/*.md`, `README.md`) is resolved against the repo root AND `search/`,
then compared with every receipt sharing its basename anywhere in the tree.

RED (exit 1):
  STUB_OVER_VERDICT  the cited path is an in_progress stub while a same-named
                     receipt elsewhere carries a verdict  <- the 02-10 case
  CITED_MISSING      nothing at the cited path, but the basename exists
                     elsewhere (prose points into the wrong tree)
  VERDICT_CONFLICT   two same-named receipts carry DIFFERENT verdicts

YELLOW (printed, exit 0): a cited path that resolves nowhere and whose
basename exists nowhere (deleted output, or a path that was never produced) —
that is a different disease, handled by citation_census.py.

Self-test (`--self-test`) seeds both a dirty pair and a clean pair in a temp
tree and requires the detector to redden on the first and stay green on the
second: a positive control ON the border, not just a green run (P-58).
"""

import argparse
import json
import os
import re
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROSE_GLOBS = ("log", ".")  # log/*.md plus top-level *.md
JSON_TOKEN = re.compile(r"[A-Za-z0-9_./\\-]*\.json")
VERDICT_KEYS = ("verdict", "last_sat", "stalled_at", "first_unsat", "finished")


def load_receipt(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def classify(d):
    """stub | verdict | other — what does this receipt actually claim?"""
    if d.get("status") == "in_progress":
        return "stub"
    if any(k in d for k in VERDICT_KEYS):
        return "verdict"
    return "other"


def verdict_key(d):
    """The claim itself, for conflict comparison. None = no comparable claim."""
    if "verdict" in d:
        return ("verdict", str(d["verdict"]))
    if "last_sat" in d:
        return ("last_sat", d.get("last_sat"), d.get("stalled_at"))
    return None


def scan_receipts(root):
    """basename -> [(relpath, receipt, kind)]"""
    index = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [x for x in dirnames if x not in (".git", "__pycache__")]
        for fn in filenames:
            if not fn.endswith(".json"):
                continue
            full = os.path.join(dirpath, fn)
            d = load_receipt(full)
            if d is None:
                continue
            rel = os.path.relpath(full, root).replace("\\", "/")
            index.setdefault(fn, []).append((rel, d, classify(d)))
    return index


def prose_citations(root):
    """{basename: set(cited tokens)} over prose files."""
    cites = {}
    for sub in PROSE_GLOBS:
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            with open(os.path.join(d, fn), "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for tok in JSON_TOKEN.findall(text):
                tok = tok.replace("\\", "/").lstrip("./")
                if not tok or "/" not in tok and not tok.endswith(".json"):
                    continue
                base = os.path.basename(tok)
                if base:
                    cites.setdefault(base, set()).add(tok)
    return cites


def resolve(root, tok):
    """Where a cited relative path could land: repo root, or search/ cwd."""
    hits = []
    for prefix in ("", "search"):
        cand = os.path.join(root, prefix, tok)
        if os.path.isfile(cand):
            hits.append(os.path.relpath(cand, root).replace("\\", "/"))
    return hits


def census(root, quiet=False):
    index = scan_receipts(root)
    cites = prose_citations(root)
    reds, yellows = [], []

    for base, toks in sorted(cites.items()):
        present = index.get(base, [])
        verdicts = [(p, d) for p, d, kind in present if kind == "verdict"]
        stubs = [p for p, d, kind in present if kind == "stub"]

        # VERDICT_CONFLICT — same name, different claim
        keys = {}
        for p, d in verdicts:
            k = verdict_key(d)
            if k is not None:
                keys.setdefault(k, []).append(p)
        if len(keys) > 1:
            reds.append(("VERDICT_CONFLICT", base,
                         "; ".join("%s <- %s" % (k, ", ".join(v)) for k, v in keys.items())))

        for tok in sorted(toks):
            hits = resolve(root, tok)
            if not hits:
                where = ", ".join(p for p, _, _ in present)
                if present and "/" in tok:
                    # prose gives a TREE and it is the wrong one — actively misleading
                    reds.append(("WRONG_TREE", tok, "basename lives at: " + where))
                elif present:
                    # bare basename: an incomplete address, not a false one
                    yellows.append(("NO_TREE", tok, "lives at: " + where))
                else:
                    yellows.append(("UNRESOLVED", tok, "no file, no same-named receipt anywhere"))
                continue
            for hit in hits:
                kind = next((k for p, _, k in present if p == hit), "other")
                if kind == "stub" and verdicts:
                    reds.append(("STUB_OVER_VERDICT", tok,
                                 "cited path %s is an in_progress stub; verdict lives at %s"
                                 % (hit, ", ".join(p for p, _ in verdicts))))

    if not quiet:
        print("receipts parsed: %d files, %d distinct basenames" %
              (sum(len(v) for v in index.values()), len(index)))
        print("prose citations: %d distinct basenames" % len(cites))
        print("")
        for tag, who, why in reds:
            print("RED    %-18s %s\n         %s" % (tag, who, why))
        for tag, who, why in yellows:
            print("yellow %-18s %s  (%s)" % (tag, who, why))
        if not reds:
            print("RED: none — every cited receipt path is the best carrier of its own claim.")
        print("")
        print("summary: %d red, %d yellow" % (len(reds), len(yellows)))
    return reds, yellows


def self_test():
    """Positive control ON the border + a clean pair that must stay green."""
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "log"))
        os.makedirs(os.path.join(tmp, "out"))
        os.makedirs(os.path.join(tmp, "search", "out"))

        # dirty pair: prose cites out/run.json (a stub); verdict sits in search/out/
        with open(os.path.join(tmp, "out", "run.json"), "w") as fh:
            json.dump({"status": "in_progress", "started": "x"}, fh)
        with open(os.path.join(tmp, "search", "out", "run.json"), "w") as fh:
            json.dump({"last_sat": 212, "stalled_at": 213, "verdict": "M >= 212"}, fh)
        # clean pair: prose cites a receipt that IS the verdict, no twin
        with open(os.path.join(tmp, "out", "clean.json"), "w") as fh:
            json.dump({"last_sat": 145, "stalled_at": 146, "verdict": "M >= 145"}, fh)
        with open(os.path.join(tmp, "log", "t.md"), "w", encoding="utf-8") as fh:
            fh.write("read out/run.json for the climb; out/clean.json is the k=6 run\n")

        reds, _ = census(tmp, quiet=True)
        tags = sorted({t for t, _, _ in reds})
        want = ["STUB_OVER_VERDICT"]
        if tags != want:
            print("SELF-TEST FAIL: expected exactly %s, got %s" % (want, tags or "no reds"))
            ok = False
        else:
            print("SELF-TEST ok: dirty pair reddens (STUB_OVER_VERDICT)")
        if any(who.endswith("clean.json") for _, who, _ in reds):
            print("SELF-TEST FAIL: clean pair reddened — detector fires without a defect")
            ok = False
        else:
            print("SELF-TEST ok: clean pair stays green")

        # mutant: make the stub a verdict too, with the SAME claim -> must go green
        with open(os.path.join(tmp, "out", "run.json"), "w") as fh:
            json.dump({"last_sat": 212, "stalled_at": 213, "verdict": "M >= 212"}, fh)
        reds2, _ = census(tmp, quiet=True)
        if reds2:
            print("SELF-TEST FAIL: mutant (stub replaced by identical verdict) still red: %s"
                  % sorted({t for t, _, _ in reds2}))
            ok = False
        else:
            print("SELF-TEST ok: mutant with identical verdicts is green (no false alarm)")

        # mutant 2: differing claims under one name -> VERDICT_CONFLICT
        with open(os.path.join(tmp, "out", "run.json"), "w") as fh:
            json.dump({"last_sat": 205, "stalled_at": 206, "verdict": "M >= 205"}, fh)
        reds3, _ = census(tmp, quiet=True)
        if "VERDICT_CONFLICT" not in {t for t, _, _ in reds3}:
            print("SELF-TEST FAIL: two different verdicts under one basename did not redden")
            ok = False
        else:
            print("SELF-TEST ok: VERDICT_CONFLICT fires on disagreeing twins")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true",
                    help="seed a dirty pair, a clean pair and two mutants; check the detector")
    ap.add_argument("--root", default=REPO, help="repo root to census")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(0 if self_test() else 1)

    reds, _ = census(args.root)
    sys.exit(1 if reds else 0)


if __name__ == "__main__":
    main()
