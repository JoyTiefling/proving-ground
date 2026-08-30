#!/usr/bin/env python3
"""
Positive controls for citation_census.

The census came up GREEN on its first real run. A green that has never been
red is one light, not evidence — so each mutant below is a state the real
repo could actually enter, and every one of them must turn the census RED.
Mutant 3 is the sharpest: it takes a REAL line from the REAL log and removes
only the exemption marker, so it proves the marker is what holds the green up
and not some accident of parsing.

  python search/test_citation_census.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from citation_census import census, PROSE, EXEMPT  # noqa: E402

SUPERSEDED_SHA = "36dfed9cbac60b3e"   # really in out/superseded/
LIVE_SHA = "24c378c7df3e11a8"         # really in out/
CORE_SHA = "7af12ac3b6ca061f"         # recomputed, stored nowhere
FABRICATED = "deadbeefcafe0123"

failures = []


def check(name, text, want_red, want_reason=None):
    """Write `text` as the only prose document and assert the census verdict."""
    fd, path = tempfile.mkstemp(suffix=".md", dir=REPO, text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        rel = os.path.basename(path)
        *_, findings, missing = census([rel])
        got_red = bool(findings)
        ok = got_red == want_red
        if ok and want_reason:
            ok = any(want_reason in why for _, _, _, why in findings)
        if missing:
            ok = False
        print("%-4s %s%s" % ("ok" if ok else "FAIL", name,
                             "" if ok else "  -> findings=%r missing=%r" % (findings, missing)))
        if not ok:
            failures.append(name)
    finally:
        os.unlink(path)


# --- negative controls: these must stay GREEN -------------------------------
check("live run sha resolves", "run `%s` says X" % LIVE_SHA, want_red=False)
check("core digest resolves (recomputed, not stored)",
      "core_sha16 `%s`" % CORE_SHA, want_red=False)
check("superseded WITH marker is allowed",
      "control `%s` restored <!-- %s -->" % (SUPERSEDED_SHA, EXEMPT), want_red=False)
check("prose with no sha at all", "no identities quoted here.", want_red=False)

# --- positive controls: each must go RED ------------------------------------
check("superseded WITHOUT marker",
      "control `%s` restored" % SUPERSEDED_SHA,
      want_red=True, want_reason="SUPERSEDED")
check("fabricated sha resolves to nothing",
      "measured in run `%s`" % FABRICATED,
      want_red=True, want_reason="NOTHING")
check("marker on a NEIGHBOURING line does not cover this one",
      "ok `%s` <!-- %s -->\nbare `%s` here\n" % (SUPERSEDED_SHA, EXEMPT, SUPERSEDED_SHA),
      want_red=True, want_reason="SUPERSEDED")

# --- mutant 3: the real log, with only the marker removed -------------------
real = open(os.path.join(REPO, "log", "weak-schur.md"), encoding="utf-8").read()
assert EXEMPT in real, "log no longer uses the exemption marker — update this test"
check("REAL log with exemption markers stripped", real.replace(EXEMPT, ""),
      want_red=True, want_reason="SUPERSEDED")
check("REAL log untouched stays green", real, want_red=False)

# --- guard: the census must notice a prose document that vanished -----------
*_, missing = census(["log/does-not-exist.md"])
print("%-4s missing prose document is reported" % ("ok" if missing else "FAIL"))
if not missing:
    failures.append("missing prose document is reported")

print("\n%d failure(s)" % len(failures))
sys.exit(1 if failures else 0)
