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

# A fixture that behaved as designed exits with this, and nothing else
# does. Exit 1 is what a crashing program returns too, and the contract
# test used to read a traceback as proof that the check works.
FIXTURE_FOUND_ITS_FAULT = 86

# Matched against whitespace-flattened text, so a counter block that gets
# reflowed across lines is still found. [^\n] would stop at the line break
# and report the block as absent, which exits 2 -- and a CI that only fails
# on 1 walks past that. [^=] keeps the match from reaching across into a
# different counter further down the document.
COUNTER_LINE = re.compile(
    r"principles examined\s*=\s*(\d+)[^=]*?adversary present\s*=\s*(\d+)")
VERDICT_LINE = re.compile(
    r"full\s*=\s*(\d+)[^=]*?partial\s*=\s*(\d+)[^=]*?none\s*=\s*(\d+)")
# The third line of the block, which nothing read until 2026-09-11: editing
# it from 4 to 9 left this check exiting 0, in a tool whose whole job is to
# notice the header disagreeing with the table.
MAPPED_LINE = re.compile(
    r"distinct ASI codes mapped\s*=\s*(\d+)[^=]*?ASI codes with no card\s*=\s*(\d+)")
ASI_CODE = re.compile(r"ASI\d+", re.IGNORECASE)
# What counts as "no adversary here". Anything outside both sets is
# reported: the first version counted every unrecognised word as an
# adversary, so a cell reading "none" or "n/a" invented one.
ADVERSARY_ABSENT = ("no", "n", "—", "-", "")
ADVERSARY_PRESENT = ("yes", "y", "true")


def read_table(text, start_marker, stop_markers):
    """Rows of the first table after start_marker, as lists of cells."""
    if start_marker not in text:
        return []
    body = text.split(start_marker, 1)[1]
    for marker in stop_markers:
        if marker in body:
            body = body.split(marker, 1)[0]
    header = None
    separator_seen = False
    rows = []
    misshapen = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            # Column positions are read from the header, never assumed. A
            # parser that counts positions breaks the first time a column
            # is inserted, and breaks quietly.
            header = [c.lower() for c in cells]
            continue
        # The separator is the row right after the header, and it is
        # recognised by position rather than by its characters. Testing for
        # "only dashes, pipes and spaces" rejected GitHub's own alignment
        # row (|:---|---:|) as data -- five invented problems on a valid
        # document -- and silently swallowed a row of empty cells, which
        # undercounts instead.
        if not separator_seen and all(re.fullmatch(r"[-:]*", cell) for cell in cells):
            separator_seen = True
            continue
        if len(cells) != len(header):
            # zip() would drop the extra cells or the missing ones without
            # a word, and the tallies would come out wrong rather than
            # unreadable.
            misshapen.append((len(cells), len(header), " ".join(cells)[:40]))
        rows.append(dict(zip(header, cells)))
    return rows, misshapen


def check(text, label):
    rows, misshapen = read_table(text, "## Where our incidents land",
                                 ["### Held back", "## Where the taxonomy"])
    # The second table names the codes that carry no card. Counting its rows
    # is where the size of the taxonomy comes from: hardcoding 10 made every
    # "X of the ten" claim wrong the day the list changed, and could hand a
    # negative number to the prose check.
    no_card_rows, _ = read_table(text, "## Where the taxonomy goes",
                                 ["## On the empty column", "## About the name"])
    flat = re.sub(r"\s+", " ", text)
    counter = COUNTER_LINE.search(flat)
    verdicts = VERDICT_LINE.search(flat)
    declared_codes = MAPPED_LINE.search(flat)

    if not rows or not counter or not verdicts:
        structure = [("structure", "table rows=%d, counters=%s, verdicts=%s"
                      % (len(rows), bool(counter), bool(verdicts)))]
        print("%-22s examined=0 problems=%d" % (label, len(structure)))
        print("no table or no counters found: nothing was checked")
        return 0, structure

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
    unreadable_adversary = []
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
        if adversary in ADVERSARY_PRESENT:
            adversary_yes += 1
        elif adversary not in ADVERSARY_ABSENT:
            unreadable_adversary.append("%s: %r"
                                        % (cells.get("principle", "?")[:30], adversary))

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
    for detail in unreadable_adversary:
        problems.append(("unreadable adversary", detail))
    for width, columns, preview in misshapen:
        problems.append(("misshapen row",
                         "%d cells against a header of %d: %s" % (width, columns, preview)))

    # The prose that summarises the counters is checked against them. It was
    # the one surface nobody read: "seven of the ten" sat above a list of six
    # through two external judgements.
    # Every code in the cell, not the first five characters of it: a row
    # reading "ASI02, ASI09" counted as one code, and the prose checks below
    # were then computed from an undercount with nothing said about it.
    mapped_codes = set()
    for row in rows:
        for code in ASI_CODE.findall(row.get("asi", "")):
            mapped_codes.add(code.upper())
    no_card_codes = set()
    for row in no_card_rows:
        for code in ASI_CODE.findall(row.get("asi", "")):
            no_card_codes.add(code.upper())
    if declared_codes:
        if int(declared_codes.group(1)) != len(mapped_codes):
            problems.append(("mapped count",
                             "table maps %d distinct codes, header declares %s"
                             % (len(mapped_codes), declared_codes.group(1))))
        if int(declared_codes.group(2)) != len(no_card_codes):
            problems.append(("no-card count",
                             "the second table lists %d codes with no card, header declares %s"
                             % (len(no_card_codes), declared_codes.group(2))))
    overlap = mapped_codes & no_card_codes
    if overlap:
        problems.append(("code in both tables",
                         "%s carries a card and is listed as having none"
                         % ", ".join(sorted(overlap))))
    counters = {
        "principles": len(rows),
        "mapped": len(mapped_codes),
        "no_card": len(no_card_codes),
    }
    # Table cells and quoted PDF text are not prose: a quotation holding
    # "seven of the ten" was compared against the counters and reported as a
    # defect of a sentence nobody wrote.
    prose_only = "\n".join(line for line in text.splitlines()
                           if not line.strip().startswith("|"))
    prose_examined, prose_problems = check_prose(prose_only, counters)
    for detail in prose_problems:
        problems.append(("prose", detail))

    print("%-22s examined=%d problems=%d prose_claims=%d"
          % (label, len(rows), len(problems), prose_examined))
    for kind, detail in problems:
        print("   %-20s %s" % (kind, detail))
    return len(rows), problems


# The real defect: thirteen rows under a header claiming twelve, with the
# partial tally short by one, a row whose adversary column says yes, and a
# sentence claiming a different count from the table beneath it -- the last
# one survived two external judgements because no check read the prose.
FIXTURE = """# Mapping

    principles examined = 12    adversary present = 0
    full = 1    partial = 6 (one of them weak)    none = 5
    distinct ASI codes mapped = 9    ASI codes with no card = 6

## Where our incidents land

| # | Principle | ASI | Verdict | Adversary | Quotation |
|:---|---|---|---|---|---:|
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
| 13 | Thirteen | ASI08 | partial | maybe | "m" (p.13) |
| 14 | Fourteen | ASI02, ASI09 | partial | no | "n" (p.14) | stray |

## Where the taxonomy goes and we do not follow

| ASI | Title | Why no card |
|---|---|---|
| ASI01 | One | requires an attacker |
| ASI05 | Five | executes code by design |
"""

# Six faults in one document, and the alignment row above must not become a
# seventh: |:---|---:| is valid Markdown, and reading it as data invented
# five problems on a document that was right.
EXPECTED = {"row count", "partial", "adversary count", "unreadable adversary",
            "mapped count", "no-card count", "misshapen row"}


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
    if examined != 14:
        print("FAIL  examined %d rows, the fixture holds 14" % examined)
        conforms = False
    else:
        print("ok    all 14 seeded rows were read, and the alignment row was not one of them")
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
    print("exiting 86: the code that means the fixture found the fault it planted")
    return FIXTURE_FOUND_ITS_FAULT


# A number word missing from here was skipped in silence, so a sentence
# claiming "twenty principles" went unread by the check written to read
# exactly that kind of sentence.
WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
         "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
         "fifty": 50}


def check_prose(text, counters):
    """Compare the sentences that summarise the counters with the counters.

    The machine-readable block and the table agreed while the prose above
    them said "seven of the ten" over a list of six. Two judgements walked
    past it, because every check read the numbers and none read the words.
    """
    problems = []
    examined = 0

    # Flatten first. The sentence this check exists for was wrapped between
    # "the" and "ten", and the pattern below looks for a space -- so the
    # check written to catch the error walked past it on the first run.
    # Third time today that a line break defeated a check; the fix belongs
    # wherever text is matched, not only where citations are.
    text = re.sub(r"\s+", " ", text)

    patterns = [
        # "Six of the ten have no counterpart here"
        (r"\b([A-Za-z]+) of the ten\b", "no_card",
         "codes with no card"),
        # "Four distinct codes carry cards"
        (r"\b([A-Za-z]+) distinct codes carry cards\b", "mapped",
         "distinct codes mapped"),
        # "Twelve principles"
        (r"\b([A-Za-z]+) principles\b", "principles", "principles"),
    ]
    for pattern, key, label in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            word = match.group(1).lower()
            if word not in WORDS:
                continue
            examined += 1
            claimed = WORDS[word]
            actual = counters.get(key)
            if actual is not None and claimed != actual:
                problems.append("prose says %s %s, the counters say %d"
                                % (word, label, actual))
    return examined, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
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
