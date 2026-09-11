#!/usr/bin/env python3
"""Check that a block copied into several files is still the same block.

The controls in this repository are meant to be taken one at a time, so
the validation that reads an observation is copied into each of them
rather than imported. That choice buys a single-file control and owes a
debt: two copies of one rule drift, and the drift is silent -- the
principle this repository holds back from the twelve, because its sharpest
numbers come from a synthetic dataset.

This is the interest payment. Every file carrying the block declares it
between two markers, and the copies are compared byte for byte.

Exit codes
    0   every copy is identical
    1   at least two copies differ
    2   fewer than two copies found: nothing was compared
    3   --fixture did not behave as declared
"""

import argparse
import hashlib
import os
import sys
import tempfile

# A fixture that behaved as designed exits with this, and nothing else
# does. Exit 1 is what a crashing program returns too, and the contract
# test used to read a traceback as proof that the check works.
FIXTURE_FOUND_ITS_FAULT = 86

OPEN_MARKER = "# ---- the shape of an observation "
CLOSE_MARKER = "# ---- end of the shape block "
SEARCH_DIRS = ("controls", "tools")


def extract(text):
    """The block between the markers, or None if the file carries none.

    An unclosed block is not "no block": it is returned as the empty
    string, which never matches a real copy and is reported as a
    difference rather than skipped.
    """
    if OPEN_MARKER not in text:
        return None
    body = text.split(OPEN_MARKER, 1)[1]
    if CLOSE_MARKER not in body:
        return ""
    return body.split(CLOSE_MARKER, 1)[0]


def collect(root):
    """(path, block) for every file under the search dirs carrying a block.

    This file is skipped, and not by name: it holds the markers in order to
    look for them, so the first run counted the tool itself as a seventh
    copy and reported it as the one that had drifted. A measuring tool that
    lands inside its own measurement is the shape of failure this
    repository collects, and it happened here first.
    """
    here = os.path.abspath(__file__)
    found = []
    for directory in SEARCH_DIRS:
        full = os.path.join(root, directory)
        if not os.path.isdir(full):
            continue
        for base, dirs, names in os.walk(full):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(names):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(base, name)
                if os.path.abspath(path) == here:
                    continue
                try:
                    with open(path, encoding="utf-8") as handle:
                        text = handle.read()
                except (OSError, UnicodeDecodeError) as error:
                    # Fail closed: a file this cannot read is a file whose
                    # copy was not compared, and that has to be said out
                    # loud rather than counted as absent.
                    found.append((os.path.relpath(path, root), "<unreadable: %s>" % error))
                    continue
                block = extract(text)
                if block is not None:
                    found.append((os.path.relpath(path, root), block))
    return found


def inspect(copies):
    """Return (examined, problems). A problem is (path, digest, detail)."""
    digests = {}
    for path, block in copies:
        digests.setdefault(hashlib.sha256(block.encode("utf-8")).hexdigest(), []).append(path)
    if len(digests) <= 1:
        return len(copies), []
    # The majority reading is the reference: one edited copy is the common
    # case, and naming it beats naming the other five.
    winner = max(digests.items(), key=lambda item: (len(item[1]), item[0]))
    problems = []
    for digest, paths in sorted(digests.items()):
        if digest == winner[0]:
            continue
        for path in paths:
            problems.append((path, digest[:12],
                             "differs from the %d copies agreeing on %s"
                             % (len(winner[1]), winner[0][:12])))
    return len(copies), problems


def report(examined, problems, label):
    print("%-22s examined=%d problems=%d" % (label, examined, len(problems)))
    for path, digest, detail in problems:
        print("   %-28s %-14s %s" % (path, digest, detail))
    return problems


def run_fixture():
    """Plant a drifted copy and check that this tool names it."""
    conforms = True
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "controls"))
        canonical = OPEN_MARKER + "---\ndef as_mapping(value):\n    return value\n" + CLOSE_MARKER + "---\n"
        drifted = canonical.replace("return value", "return value or {}")
        unclosed = OPEN_MARKER + "---\ndef as_mapping(value):\n    return value\n"
        seeded = [("agree_one.py", canonical), ("agree_two.py", canonical),
                  ("drifted.py", drifted), ("unclosed.py", unclosed),
                  ("no_block.py", "print('nothing to compare here')\n")]
        for name, body in seeded:
            with open(os.path.join(tmp, "controls", name), "w", encoding="utf-8") as handle:
                handle.write(body)

        copies = collect(tmp)
        examined, problems = inspect(copies)
        report(examined, problems, "fixture")
        named = sorted(os.path.basename(p) for p, _, _ in problems)

        print("\n--- fixture verdict ---")
        if examined == 4:
            print("ok    four files carry a block, the fifth was left alone")
        else:
            print("FAIL  expected 4 files carrying a block, examined %d" % examined)
            conforms = False
        if named == ["drifted.py", "unclosed.py"]:
            print("ok    named the edited copy and the unclosed one, and nothing else")
        else:
            print("FAIL  expected ['drifted.py', 'unclosed.py'], got %s" % named)
            conforms = False

        # A check that cannot see agreement is as broken as one that cannot
        # see drift, so the clean case is planted too.
        for name in ("drifted.py", "unclosed.py"):
            os.remove(os.path.join(tmp, "controls", name))
        clean_examined, clean_problems = inspect(collect(tmp))
        if clean_examined == 2 and not clean_problems:
            print("ok    two identical copies are reported as identical")
        else:
            print("FAIL  identical copies reported examined=%d problems=%d"
                  % (clean_examined, len(clean_problems)))
            conforms = False

    if not conforms:
        print("\nfixture did not behave as declared: the check cannot be trusted")
        return 3
    print("\nexiting 86: the code that means the fixture found the fault it planted")
    return FIXTURE_FOUND_ITS_FAULT


def main():
    parser = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", help="repository root")
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    if args.fixture:
        return run_fixture()

    root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    copies = collect(root)
    examined, problems = inspect(copies)
    report(examined, problems, "copy-check")
    if examined < 2:
        print("found %d copies of the block: with fewer than two there is nothing"
              " to compare, and a check that compares nothing passes" % examined)
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
