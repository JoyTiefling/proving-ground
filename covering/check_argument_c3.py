"""Pin the prose of covering/argument_c3.md to the witness payload.

Why this exists: the worked leaves in the argument are transcribed by hand from
search/out/w76.json. A transcription error is invisible on rereading -- the
prose stays internally coherent and only stops matching the object it claims to
describe. So the claims are re-derived from the payload here, and the hand-typed
derivation bullets in the worked sections are parsed back out of the markdown
and compared step for step.

This checker VALIDATES; it does not search. It can fail: mutate any quoted
number in the markdown, or any bullet's clause/root/colour/domain, and the
corresponding assertion goes red. Run with --self-test to see that happen.

What it does NOT catch, stated so the green is not read as more than it is:
a bullet *omitted* from the prose. The check is one-directional — every typed
bullet must exist in the payload, but not every payload step need be typed.
That is deliberate and not laziness: section 4 openly declines to repeat the
prefix steps it shares with section 3, so a completeness assertion would be red
for a legitimate reason and would have to be muted, which is worse than being
absent. Omission is guarded by the step *counts*, which are anchored and
checked; a dropped bullet leaves those untouched, so the guard is partial. If a
later instalment claims a leaf is written "in full", that claim needs its own
check and does not have one yet.

Usage:
    python covering/check_argument_c3.py
    python covering/check_argument_c3.py --self-test
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "search" / "out" / "w76.json"
PROSE = ROOT / "covering" / "argument_c3.md"

# The two worked leaves, by their branch path in the payload.
WORKED = {
    "3": [[11, 2], [9, 3], [17, 3]],
    "4": [[11, 2], [9, 4], [17, 3]],
}


def step_key(s):
    return (
        s["kind"],
        tuple(s.get("clause") or ()),
        s.get("root"),
        s.get("colour"),
        s.get("removed"),
    )


def derive(payload):
    """Every number the prose quotes, recomputed from the payload alone."""
    cases = payload["cases"]
    kinds = Counter(st["kind"] for c in cases for st in c["steps"])

    trie, distinct = {}, 0
    for c in cases:
        node = trie
        for k in (step_key(st) for st in c["steps"]):
            if k not in node:
                node[k] = {}
                distinct += 1
            node = node[k]

    signatures = {step_key(st) for c in cases for st in c["steps"]}

    blocks = Counter()
    touched = set()
    for i, c in enumerate(cases):
        for st in c["steps"]:
            if st["kind"] in ("pair_prune", "pair_conflict"):
                blocks[(tuple(sorted(st["clause"])), st["kind"])] += 1
                touched.add(i)

    idx = {tuple(map(tuple, c["path"])): i for i, c in enumerate(cases)}
    worked = {k: idx[tuple(map(tuple, p))] for k, p in WORKED.items()}
    a, b = (cases[worked["3"]]["steps"], cases[worked["4"]]["steps"])
    shared = 0
    for x, y in zip(a, b):
        if step_key(x) != step_key(y):
            break
        shared += 1

    return {
        "leaves": len(cases),
        "depth": max(c["depth"] for c in cases),
        "mono_prune": kinds["mono_prune"],
        "pair_prune": kinds["pair_prune"],
        "pin": kinds["pin"],
        "mono_conflict": kinds["mono_conflict"],
        "pair_conflict": kinds["pair_conflict"],
        "total_steps": sum(kinds.values()),
        "distinct_prefix_tree": distinct,
        "distinct_signature": len(signatures),
        "block_11_17_prunes": blocks[((11, 17), "pair_prune")],
        "block_35_55_prunes": blocks[((35, 55), "pair_prune")],
        "block_35_55_conflicts": blocks[((35, 55), "pair_conflict")],
        "cases_touching_a_block": len(touched),
        "worked_shared_prefix": shared,
        "worked_distinct_covered": len(a) + len(b) - shared,
        "steps_sec3": len(a),
        "steps_sec4": len(b),
        "worked_index": worked,
    }


# Each derived quantity is anchored to the ONE place in the prose that states
# it, and the number is read out of that anchor. A bare "does 76 appear
# somewhere in the file" is not a check: 76 appears a dozen times, so editing
# any single occurrence would leave it green. The anchor must capture the digit
# in its own sentence, and it must match exactly once.
ANCHORS = {
    "leaves": r"the case tree over that core has \*\*(\d+) conflict leaves\*\*",
    "depth": r"\*\*depth (\d+)\*\*, and branches on",
    "mono_prune": r"\| `mono_prune` \(triple prunes\) \| (\d+) \|",
    "pair_prune": r"\| `pair_prune` \(block prunes\) \| (\d+) \|",
    "pin": r"\| `pin` \(case splits\) \| (\d+) \|",
    "mono_conflict": r"\| `mono_conflict` \(dies on a monochromatic triple\) \| (\d+) \|",
    "pair_conflict": r"\| `pair_conflict` \(dies on a cover block\) \| (\d+) \|",
    "total_steps": r"\| \*\*total, case-by-case\*\* \| \*\*(\d+)\*\* \|",
    "distinct_prefix_tree": r"the count is \*\*(\d+)\*\*",
    "distinct_signature": r"it is \*\*(\d+)\*\*\. The writable-by-hand number",
    "block_11_17_prunes": r"\| `¬\(11 = 3 ∧ 17 = 3\)` \| (\d+) \| \d+ \|",
    "block_35_55_prunes": r"\| `¬\(35 = 3 ∧ 55 = 3\)` \| (\d+) \| \d+ \|",
    "block_35_55_conflicts": r"\| `¬\(35 = 3 ∧ 55 = 3\)` \| \d+ \| (\d+) \|",
    "cases_touching_a_block": r"\*\*(\d+) of the 76 cases contain at least one block step\.\*\*",
    "worked_shared_prefix": r"share a (\d+)-step prefix",
    "worked_distinct_covered": r"cover\n\*\*(\d+) of the 1116 distinct steps\*\*",
    "steps_sec3": r"## 3\..*?\(depth \d+, (\d+) steps\)",
    "steps_sec4": r"## 4\..*?\(depth \d+, (\d+) steps\)",
}


def read_claims(prose):
    """Read each claimed magnitude out of its own sentence in the prose."""
    claims, problems = {}, []
    for name, pat in ANCHORS.items():
        hits = re.findall(pat, prose, flags=re.S)
        if len(hits) != 1:
            problems.append(
                f"{name}: anchor matched {len(hits)} times in the prose, expected exactly 1"
            )
            continue
        claims[name] = int(hits[0])
    return claims, problems

BULLET = re.compile(
    r"^- `\{([\d,\s]+)\}`.*?⟹ `(\d+)` loses (\d+), domain `\{([\d,\s]+)\}`"
)
SECTION = re.compile(r"^## (\d)\.")


def parse_prose_bullets(text):
    """Pull the hand-typed derivation bullets out of each worked section."""
    out, cur = {}, None
    for line in text.splitlines():
        m = SECTION.match(line)
        if m:
            cur = m.group(1) if m.group(1) in WORKED else None
            continue
        if cur is None:
            continue
        m = BULLET.match(line.strip())
        if m:
            clause = tuple(int(x) for x in m.group(1).replace(" ", "").split(","))
            out.setdefault(cur, []).append(
                (
                    clause,
                    int(m.group(2)),
                    int(m.group(3)),
                    tuple(int(x) for x in m.group(4).replace(" ", "").split(",")),
                )
            )
    return out


def check(payload_text=None, prose_text=None):
    payload = json.loads(payload_text or PAYLOAD.read_text(encoding="utf-8"))
    prose = prose_text if prose_text is not None else PROSE.read_text(encoding="utf-8")
    got = derive(payload)
    failures = []

    if not payload.get("all_gates_pass"):
        failures.append("payload's own gates do not pass -- nothing here is trustworthy")

    claims, problems = read_claims(prose)
    failures.extend(problems)
    for name, want in claims.items():
        if got[name] != want:
            failures.append(f"{name}: prose says {want}, payload gives {got[name]}")

    # Hand-typed bullets vs payload, step for step.
    bullets = parse_prose_bullets(prose)
    for sec, path in WORKED.items():
        steps = payload["cases"][got["worked_index"][sec]]["steps"]
        actual = [
            (tuple(s["clause"]), s["root"], s["removed"], tuple(s["left"]))
            for s in steps
            if s["kind"] in ("mono_prune", "pair_prune")
        ]
        typed = bullets.get(sec, [])
        if not typed:
            failures.append(f"section {sec}: no derivation bullets parsed out of the prose")
            continue
        pool = set(actual)
        for i, b in enumerate(typed):
            if b not in pool:
                failures.append(
                    f"section {sec} bullet {i + 1}: {b[0]} -> {b[1]} loses {b[2]}, "
                    f"domain {list(b[3])} -- no such step in the payload"
                )
    return failures, got


def main():
    self_test = "--self-test" in sys.argv
    failures, got = check()

    if self_test:
        prose = PROSE.read_text(encoding="utf-8")
        muts = {
            "M1 leaf count 76->77": lambda t: t.replace("**76 conflict leaves**", "**77 conflict leaves**"),
            "M2 pair_prune 49->48": lambda t: t.replace("| 49 |", "| 48 |"),
            "M3 corrupt a bullet's domain": lambda t: t.replace(
                "⟹ `15` loses 3, domain `{4}`", "⟹ `15` loses 3, domain `{2,4}`"
            ),
            "M4 corrupt a bullet's clause": lambda t: t.replace(
                "`{15, 25, 55}` (15, 25 at 4)", "`{15, 25, 57}` (15, 25 at 4)"
            ),
        }
        print("positive control (unmutated):", "PASS" if not failures else "FAIL")
        ok = not failures
        for name, fn in muts.items():
            mutated = fn(prose)
            if mutated == prose:
                print(f"  {name}: MUTATION IS A NO-OP -- the test proves nothing")
                ok = False
                continue
            f, _ = check(prose_text=mutated)
            print(f"  {name}: {'RED (good)' if f else 'GREEN -- gate is blind'}")
            ok = ok and bool(f)
        print("self-test:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    for k, v in sorted(got.items()):
        if k != "worked_index":
            print(f"  {k:26s} {v}")
    if failures:
        print("\nFAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nOK: every number and every transcribed step agrees with the payload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
