#!/usr/bin/env python3
"""Check that the counters at the top of MAPPING.md describe the table below.

A summary line and the set it summarises drift apart quietly. The first
version of MAPPING.md declared twelve principles above a table holding
thirteen rows, with the verdict tally off by one, and nothing about the
document looked wrong. That is the failure this check exists for, and the
fixture reproduces it exactly.

Exit codes
    0   the counters match the table
    1   at least one counter disagrees with the table
    2   nothing examined: no table found, or no counters declared
"""

import argparse
import os
import re
import sys
import tempfile

COUNTER_LINE = re.compile(
    r"principles examined\s*=\s*(\d+)\s+adversary present\s*=\s*(\d+)")
VERDICT_LINE = re.compile(
    r"full\s*=\s*(\d+)\s+partial\s*=\s*(\d+)[^\n]*?none\s*=\s*(\d+)")


def read_table(text, start_marker, stop_markers):
    """Rows of the first table after start_marker, as lists of cells."""
    if start_marker not in text:
        return []
    body = text.split(start_marker, 1)[1]
    for marker in stop_markers:
        if marker in body:
            body = body.split(marker, 1)[0]
    header = None
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            # Column positions are read from the header, never assumed. A
            # parser that counts positions breaks the first time a column
            # is inserted, and breaks quietly.
            header = [c.lower() for c in cells]
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def check(text, label):
    rows = read_table(text, "## Where our incidents land",
                      ["### Held back", "## Where the taxonomy"])
    counter = COUNTER_LINE.search(text)
    verdicts = VERDICT_LINE.search(text)

    if not rows or not counter or not verdicts:
        print("%-22s examined=0 problems=0" % label)
        print("no table or no counters found: nothing was checked")
        return 0, [("structure", "table rows=%d, counters=%s, verdicts=%s"
                    % (len(rows), bool(counter), bool(verdicts)))]

    declared_total = int(counter.group(1))
    declared_adversary = int(counter.group(2))
    declared = {
        "full": int(verdicts.group(1)),
        "partial": int(verdicts.group(2)),
        "none": int(verdicts.group(3)),
    }

    actual = {"full": 0, "partial": 0, "none": 0}
    adversary_yes = 0
    unknown = []
    for cells in rows:
        verdict = cells.get("verdict", "").lower()
        adversary = cells.get("adversary", "").lower()
        if verdict.startswith("full"):
            actual["full"] += 1
        elif verdict.startswith("partial"):
            actual["partial"] += 1
        elif verdict.startswith("none") or verdict.startswith("—"):
            actual["none"] += 1
        else:
            unknown.append(cells.get("principle", "?")[:40])
        if adversary not in ("no", "—", ""):
            adversary_yes += 1

    problems = []
    if len(rows) != declared_total:
        problems.append(("row count",
                         "table holds %d rows, header declares %d" % (len(rows), declared_total)))
    for name in ("full", "partial", "none"):
        if actual[name] != declared[name]:
            problems.append((name, "table has %d, header declares %d"
                             % (actual[name], declared[name])))
    if sum(actual.values()) != len(rows):
        problems.append(("verdict coverage",
                         "%d rows but %d classified verdicts" % (len(rows), sum(actual.values()))))
    if adversary_yes != declared_adversary:
        problems.append(("adversary count",
                         "table shows %d with an adversary, header declares %d"
                         % (adversary_yes, declared_adversary)))
    for name in unknown:
        problems.append(("unreadable verdict", name))

    print("%-22s examined=%d problems=%d" % (label, len(rows), len(problems)))
    for kind, detail in problems:
        print("   %-20s %s" % (kind, detail))
    return len(rows), problems


# The real defect: thirteen rows under a header claiming twelve, with the
# partial tally short by one, plus a row whose adversary column says yes.
FIXTURE = """# Mapping

    principles examined = 12    adversary present = 0
    full = 1    partial = 6 (one of them weak)    none = 5

## Where our incidents land

| # | Principle | ASI | Verdict | Adversary | Quotation |
|---|---|---|---|---|---|
| 01 | One | ASI02 | partial | no | "a" (p.1) |
| 02 | Two | ASI09 | partial | no | "b" (p.2) |
| 03 | Three | — | none | no | "c" (p.3) |
| 04 | Four | — | none | no | "d" (p.4) |
| 05 | Five | ASI03 | partial | no | "e" (p.5) |
| 06 | Six | ASI03 | partial | no | "f" (p.6) |
| 07 | Seven | — | none | no | "g" (p.7) |
| 08 | Eight | ASI03 | partial | yes | "h" (p.8) |
| 09 | Nine | — | none | no | "i" (p.9) |
| 10 | Ten | ASI09 | partial (weak) | no | "j" (p.10) |
| 11 | Eleven | — | none | no | "k" (p.11) |
| 12 | Twelve | ASI04 | full | no | "l" (p.12) |
| 13 | Thirteen | ASI08 | partial | no | "m" (p.13) |

## Where the taxonomy goes and we do not follow
"""

EXPECTED = {"row count", "partial", "adversary count"}


def run_fixture():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "MAPPING.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE)
        with open(path, encoding="utf-8") as handle:
            examined, problems = check(handle.read(), "fixture")

    kinds = set(kind for kind, _ in problems)
    print("\n--- fixture verdict ---")
    conforms = True
    if examined != 13:
        print("FAIL  examined %d rows, the fixture holds 13" % examined)
        conforms = False
    else:
        print("ok    all 13 seeded rows were read")
    for expected in sorted(EXPECTED):
        if expected in kinds:
            print("ok    caught: %s" % expected)
        else:
            print("FAIL  missed: %s" % expected)
            conforms = False
    extra = kinds - EXPECTED
    if extra:
        print("FAIL  reported problems that are not in the fixture: %s" % ", ".join(sorted(extra)))
        conforms = False

    if not conforms:
        print("\nfixture did not behave as declared: the check cannot be trusted")
        return 3
    print("\nthe drift between header and table was caught;")
    print("exiting 1 on purpose, because a check that cannot fail is not a check")
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", help="path to MAPPING.md")
    parser.add_argument("--fixture", action="store_true", help="prove the check can fail")
    args = parser.parse_args()

    if args.fixture:
        return run_fixture()

    path = args.path
    if not path:
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(repo, "MAPPING.md")
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        print("unusable mapping file: %s" % error)
        return 2

    examined, problems = check(text, "mapping-check")
    if examined == 0:
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
