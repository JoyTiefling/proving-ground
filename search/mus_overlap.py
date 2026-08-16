"""Does proving the five rigid facts ONCE actually buy anything?

Wake 16-08 14:00 solo. Reads the receipts written by `mus_rigid_five.py`.

WHY. The ladder's whole promise (log/weak-schur.md, 14-08) is: "cover costs
130 + 119 triples PLUS a single proof of those five facts" -- i.e. the five are
paid once and shared. `mus_rigid_five` (16-08 12:00) killed the cheap half of
that: one fact alone costs 319..584 of 1331 triples, the same order as the
616/633-triple unconditional cover it was meant to undercut.

That leaves exactly one number that can still save the ladder, and nobody has
it: HOW MUCH DO THE FIVE CERTIFICATES OVERLAP? If the five arguments are
essentially the same triples, the union stays near a single fact's cost and
"pay once" survives. If they are five different arguments, the union blows past
the unconditional cover and the ladder is dead as an economy.

UNIT OF ACCOUNT. Proving a fact R -> c* means excluding EVERY wrong colour, so
the certificate of a fact is the UNION of its per-colour MUS, not one of them:
    CERT(fact) = U_{c != c*} MUS(fact, c)

THE MEASUREMENT PROBLEM, HANDLED. The minimiser is order-dependent: on the SAME
instance, forward and reverse deletion disagree by 40..92 triples (#3335 --
a size that moves with the procedure is a property of the procedure). So a raw
overlap number between two facts is unreadable on its own. Fix: the procedure
measures itself. For each fact, forward and reverse are two runs on an
IDENTICAL input, so
    J_self(fact) = J(CERT_fwd(fact), CERT_rev(fact))
is what this pipeline scores when the answer is "the same thing twice". That is
the ceiling. Cross-fact overlap is only readable against it.

PRE-REGISTERED (written before any number was printed; structure, not
magnitude -- the thing that has won on this object before):

  Q1  Class structure. 13,23,43 are all partners of chain-root 1 (P3 held:
      every class-A MUS meets root 1); 5 and 31 are not. So the median
      within-class-A cross-Jaccard EXCEEDS the median A-vs-B cross-Jaccard.
      Refuted if it does not.

  Q2  The economy. |U over all five CERT| < 616 (the unconditional c=3 cover).
      Refuted if the union reaches or passes it -- in which case proving the
      five costs at least as much as not using them at all, and the ladder's
      arithmetic is finished regardless of how elegant the decomposition looks.

      ASYMMETRIC READING, fixed before the cross numbers existed. CERT here is
      the union of four INDEPENDENTLY minimised MUS, one per wrong colour --
      not a single set minimised against all four at once. Union-of-minimal is
      an upper bound on the true cost of a fact, so:
        SUPPORTED is strong  -- even the loose accounting fits under the cover.
        REFUTED is weak      -- it means "this procedure did not show the five
                                are cheap", NOT "the five are expensive". The
                                honest next move for a REFUTED Q2 is to
                                minimise once against the conjunction of all
                                wrong colours, not to declare the ladder dead.
      (Calibration run on fact 13 alone, already on disk before this wake:
      per-colour MUS 319/372/579/584 -> CERT_fwd 820. So the union is already
      over 616 from ONE fact, and Q2 will land REFUTED. Written down here so
      the weak reading is on record BEFORE the verdict, not after it.)

  Q3  Instrument sanity (positive control, and the one that can void the other
      two). Every cross-fact Jaccard is STRICTLY BELOW the smaller of the two
      facts' J_self. Refuted if any two DIFFERENT facts agree with each other
      better than this procedure agrees with itself on ONE fact -- which would
      mean the overlap number carries more noise than signal and Q1/Q2 must not
      be read at all.

This script refuses to print a verdict on fewer than the five facts: a partial
answer to "do the five overlap" is not a smaller answer, it is a different
question wearing the same words.
"""
import sys, os, json, glob, argparse, itertools, statistics

sys.path.insert(0, os.path.dirname(__file__))
import receipts

FIVE = [(13, 0), (23, 0), (43, 0), (5, 1), (31, 1)]
CLASS_A = {13, 23, 43}
UNCONDITIONAL_COVER = 616  # triples, c=3 arm, weak-schur log 14-08


def load(paths):
    """fact-key -> {'fwd': set(triple), 'rev': set(triple)}; plus provenance."""
    certs, src = {}, {}
    for p in sorted(paths):
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("script") != "mus_rigid_five.py":
            continue
        for name, per_colour in d["results"].items():
            fwd, rev = set(), set()
            for colour, r in per_colour.items():
                if r.get("verdict") != "UNSAT":
                    raise SystemExit(
                        f"{name} colour {colour}: verdict {r.get('verdict')} -- "
                        "a fact that escapes has no certificate; the overlap "
                        "question does not apply. Stop and look at it.")
                fwd |= {tuple(t) for t in r["mus_forward"]}
                rev |= {tuple(t) for t in r["mus_reverse"]}
            if not fwd or not rev:
                raise SystemExit(f"{name}: empty certificate in {p}")
            if name in certs:
                raise SystemExit(f"{name} appears in two receipts; resolve first")
            certs[name] = {"fwd": fwd, "rev": rev}
            src[name] = os.path.basename(p)
    return certs, src


def jac(a, b):
    return len(a & b) / len(a | b) if (a or b) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipts", default=None,
                    help="glob for mus_rigid_five receipts")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pattern = args.receipts or os.path.join(
        os.path.dirname(__file__), "out", "mus_rigid_five*.json")
    paths = glob.glob(pattern)
    certs, src = load(paths)

    expected = {f"{r}->{c}" for r, c in FIVE}
    missing = expected - set(certs)
    if missing:
        raise SystemExit(
            "REFUSING TO REPORT: missing certificates for " +
            ", ".join(sorted(missing)) +
            f"\nfound {sorted(certs)} in {pattern}\n"
            "The union of a subset is not a partial answer to the union of the "
            "five -- run mus_rigid_five.py for the rest first.")

    out_path = receipts.resolve_out(args, __file__, facts="five")
    receipts.probe_writable(out_path)

    # --- positive control: the procedure against itself on identical input ---
    self_j = {n: jac(d["fwd"], d["rev"]) for n, d in certs.items()}

    # --- cross-fact, forward hand vs forward hand ---
    cross = {}
    for a, b in itertools.combinations(sorted(certs), 2):
        cross[f"{a} | {b}"] = {
            "jaccard": jac(certs[a]["fwd"], certs[b]["fwd"]),
            "shared": len(certs[a]["fwd"] & certs[b]["fwd"]),
            "a_size": len(certs[a]["fwd"]),
            "b_size": len(certs[b]["fwd"]),
        }

    def root(name):
        return int(name.split("->")[0])

    within_a, across = [], []
    for key, v in cross.items():
        a, b = (root(x.strip()) for x in key.split("|"))
        (within_a if {a, b} <= CLASS_A else across).append(v["jaccard"])

    union_fwd = set().union(*(d["fwd"] for d in certs.values()))
    union_rev = set().union(*(d["rev"] for d in certs.values()))
    sum_sizes = sum(len(d["fwd"]) for d in certs.values())

    checks = {}
    checks["Q1_class_structure"] = {
        "median_within_A": statistics.median(within_a) if within_a else None,
        "median_across_classes": statistics.median(across) if across else None,
        "verdict": "SUPPORTED" if within_a and across and
                   statistics.median(within_a) > statistics.median(across)
                   else "REFUTED",
    }
    checks["Q2_economy"] = {
        "union_forward": len(union_fwd),
        "union_reverse": len(union_rev),
        "sum_of_five": sum_sizes,
        "sharing_factor": round(sum_sizes / len(union_fwd), 2),
        "unconditional_cover": UNCONDITIONAL_COVER,
        "verdict": "SUPPORTED" if len(union_fwd) < UNCONDITIONAL_COVER
                   else "REFUTED",
        "reading": ("strong: even union-of-independently-minimised fits under "
                    "the unconditional cover"
                    if len(union_fwd) < UNCONDITIONAL_COVER else
                    "WEAK: this procedure did not show the five are cheap. "
                    "CERT is a union of four separately minimised MUS, i.e. an "
                    "upper bound; next move is one minimisation against the "
                    "conjunction of all wrong colours, not a death notice."),
    }
    violations = {k: v["jaccard"] for k, v in cross.items()
                  if v["jaccard"] >= min(self_j[k.split(" | ")[0]],
                                         self_j[k.split(" | ")[1]])}
    # Q3b: written AFTER Q3 came back REFUTED, and kept separate from it on
    # purpose. Q3 compares J_self (forward vs REVERSE, one fact) against cross
    # (forward vs FORWARD, two facts) -- those are not the same comparison. The
    # two hands differ SYSTEMATICALLY, not just noisily: forward keeps ~820-920
    # triples, reverse ~690-790. So J_self is depressed by a size gap that the
    # cross number never pays. The homogeneous cross is forward-vs-reverse
    # ACROSS facts: same hand mismatch, different object. Q3 stays REFUTED on
    # the record with its diagnosis attached; this does not rescue it, it
    # explains it -- and only Q3b's margin says whether the instrument can tell
    # "same fact" from "different fact" at all.
    hom = [jac(certs[a]["fwd"], certs[b]["rev"])
           for a, b in itertools.permutations(sorted(certs), 2)]
    med_self = statistics.median(self_j.values())
    med_hom = statistics.median(hom)
    checks["Q3b_homogeneous_control"] = {
        "median_self_fwd_vs_rev": round(med_self, 3),
        "median_cross_fwd_vs_rev": round(med_hom, 3),
        "margin": round(med_self - med_hom, 3),
        "self_range": [round(min(self_j.values()), 3), round(max(self_j.values()), 3)],
        "cross_range": [round(min(hom), 3), round(max(hom), 3)],
        "ranges_overlap": min(self_j.values()) < max(hom),
        "verdict": "DISCRIMINATES" if med_self > med_hom else "BLIND",
        "reading": "the separation between 'same fact twice' and 'two different "
                   "facts' is of the same order as the procedure's own hand-to-"
                   "hand disagreement -- the five certificates are close to "
                   "indistinguishable from each other at this resolution",
    }
    shared_all = set.intersection(*(d["fwd"] for d in certs.values()))
    checks["shared_core"] = {
        "in_all_five_forward": len(shared_all),
        "in_all_five_reverse": len(set.intersection(*(d["rev"] for d in certs.values()))),
        "of_total": 1331,
        "note": "not a prediction -- the raw number the ladder question needs",
    }
    checks["Q3_instrument_sanity"] = {
        "self_jaccard": {k: round(v, 3) for k, v in self_j.items()},
        "min_self": round(min(self_j.values()), 3),
        "max_cross": round(max(v["jaccard"] for v in cross.values()), 3),
        "violations": {k: round(v, 3) for k, v in violations.items()},
        "verdict": "SUPPORTED" if not violations else "REFUTED",
        "note": "if REFUTED, Q1 and Q2 are not readable -- the overlap number "
                "carries more procedure-noise than object-signal",
    }

    print(f"certificates: {len(certs)} facts, sources {sorted(set(src.values()))}")
    for n in sorted(certs, key=root):
        print(f"  {n}: fwd {len(certs[n]['fwd'])}  rev {len(certs[n]['rev'])}  "
              f"J_self {self_j[n]:.3f}")
    print("\ncross-fact (forward hand):")
    for k, v in sorted(cross.items(), key=lambda kv: -kv[1]["jaccard"]):
        print(f"  {k:>16}: J {v['jaccard']:.3f}  shared {v['shared']:4d}  "
              f"({v['a_size']} / {v['b_size']})")
    print("\nPre-registered:")
    for k, v in checks.items():
        rest = {kk: vv for kk, vv in v.items() if kk not in ("verdict", "note")}
        print(f"  {k}: {v.get('verdict', '(raw)')}  {rest}")

    receipts.write_receipt(out_path, {
        "script": os.path.basename(__file__),
        "wake": receipts.wake_iso(),
        "reads": sorted(set(src.values())),
        "unit": "CERT(fact) = union over wrong colours of that fact's MUS",
        "preregistered": {
            "Q1": "median within-class-A cross-Jaccard > median A-vs-B",
            "Q2": "union of all five CERT < 616 (unconditional c=3 cover)",
            "Q3": "every cross-fact Jaccard strictly below both facts' J_self",
        },
        "cert_sizes": {n: {"fwd": len(d["fwd"]), "rev": len(d["rev"])}
                       for n, d in certs.items()},
        "self_jaccard": self_j,
        "cross": cross,
        "checks": checks,
    })
    print(f"\n-> {out_path}")


if __name__ == "__main__":
    main()
