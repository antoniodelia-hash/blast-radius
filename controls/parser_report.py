#!/usr/bin/env python3
"""Parse a log and declare what the parser could not attach.

A parser that reports only what it matched looks perfect while dropping a
category. The failure that produced this tool read 187 of 199 log lines
and lost exactly the twelve the measurement was about: the logger switches
quoting style when the text contains an apostrophe, and in Italian
apostrophes cluster in corrections.

An error of 6% spread at random is noise. An error of 6% that lands on one
category is a wrong answer wearing the clothes of a right one.

So two numbers, always: the lines that SHOULD have been of interest —
counted by keyword, before the pattern runs — and the lines the pattern
attached. Above a declared discard rate the parser refuses to answer.

Exit codes
    0   parsed within the declared discard rate
    1   discard rate exceeded, or nothing matched at all
    2   no candidate lines found: the source may not cover the period
    3   --fixture did not behave as declared
"""

import argparse
import re
import sys

# A fixture that behaved as designed exits with this, and nothing else
# does. Exit 1 is what a crashing program returns too, and the contract
# test used to read a traceback as proof that the check works.
FIXTURE_FOUND_ITS_FAULT = 86

DEFAULT_MAX_DISCARD = 0.01


def inspect(lines, keyword, pattern, max_discard=DEFAULT_MAX_DISCARD):
    """Return (candidates, matched, discarded_lines)."""
    compiled = re.compile(pattern)
    candidates = [line for line in lines if keyword in line]
    matched, discarded = [], []
    for line in candidates:
        if compiled.search(line):
            matched.append(line)
        else:
            discarded.append(line)
    return candidates, matched, discarded


def report(candidates, matched, discarded, max_discard, label):
    rate = (len(discarded) / float(len(candidates))) if candidates else 0.0
    print("%-22s examined=%d matched=%d discarded=%d rate=%.1f%% limit=%.1f%%"
          % (label, len(candidates), len(matched), len(discarded),
             rate * 100, max_discard * 100))
    # The rejects go on screen, not into a counter. A count says something
    # was dropped; the text says everything dropped was a correction.
    for line in discarded[:10]:
        print("   discarded: %s" % line.strip()[:90])
    if len(discarded) > 10:
        print("   ... and %d more" % (len(discarded) - 10))
    return rate


FIXTURE_KEYWORD = "msg="
FIXTURE_PATTERN = r"msg='([^']*)'"
# Ordinary lines use single quotes. The interesting ones — corrections,
# which in Italian carry apostrophes — switch to double quotes, and the
# pattern above cannot see them. That is the incident, reproduced.
FIXTURE_LINES = [
    "2026-08-11 09:01 level=info msg='job 1 registered'",
    "2026-08-11 09:02 level=info msg='job 2 registered'",
    "2026-08-11 09:03 level=info msg='report sent'",
    "2026-08-11 09:04 level=info msg=\"E' sbagliato, manca un allegato\"",
    "2026-08-11 09:05 level=info msg='window updated'",
    "2026-08-11 09:06 level=info msg=\"DEVI REGISTRARLO E BASTA\"",
    "2026-08-11 09:07 level=info msg='digest queued'",
    "2026-08-11 09:08 level=info msg=\"non e' quello che ho chiesto\"",
    "2026-08-11 09:09 level=warn something else entirely",
]


def run_fixture():
    candidates, matched, discarded = inspect(
        FIXTURE_LINES, FIXTURE_KEYWORD, FIXTURE_PATTERN)
    rate = report(candidates, matched, discarded, DEFAULT_MAX_DISCARD, "fixture")

    print("\n--- fixture verdict ---")
    conforms = True
    if len(candidates) != 8:
        print("FAIL  counted %d candidate lines, the fixture holds 8" % len(candidates))
        conforms = False
    else:
        print("ok    candidates counted by keyword before the pattern ran (8)")
    if len(discarded) != 3:
        print("FAIL  discarded %d lines, expected the 3 with the other quoting style"
              % len(discarded))
        conforms = False
    else:
        print("ok    the three differently quoted lines were declared, not hidden")
    # Every discarded line must share the other quoting style. Checking for
    # apostrophes would have been wrong: one of the three corrections is in
    # capitals and carries none. And this branch prints either way -- a
    # verdict that only speaks when it agrees is the mute check again.
    if all('msg="' in line for line in discarded):
        print("ok    every discarded line shares the other quoting style: a species")
    else:
        print("FAIL  the discarded lines have nothing in common: wrong trap")
        conforms = False
    if rate <= DEFAULT_MAX_DISCARD:
        print("FAIL  a 37%% discard rate passed the threshold")
        conforms = False
    else:
        print("ok    the discard rate crossed the declared limit")

    if not conforms:
        print("\nfixture did not behave as declared: the parser cannot be trusted")
        return 3
    print("\nthe parser refused to answer instead of reporting 5 of 8 as a result;")
    print("exiting 86: the code that means the fixture found the fault it planted")
    return FIXTURE_FOUND_ITS_FAULT


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("logfile", nargs="?")
    parser.add_argument("--keyword", default=FIXTURE_KEYWORD)
    parser.add_argument("--pattern", default=FIXTURE_PATTERN)
    parser.add_argument("--max-discard", type=float, default=DEFAULT_MAX_DISCARD)
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    if args.fixture:
        return run_fixture()
    if not args.logfile:
        parser.error("give a log file, or --fixture")
    # NaN compares false against everything, so a discard rate of 50% would
    # have passed a threshold of NaN without a word.
    limit = args.max_discard
    if not (limit == limit) or limit < 0 or limit > 1:
        print("--max-discard must be a fraction between 0 and 1, got %r" % limit)
        return 2
    try:
        with open(args.logfile, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError as error:
        print("unusable log file: %s" % error)
        return 2

    candidates, matched, discarded = inspect(lines, args.keyword, args.pattern, args.max_discard)
    rate = report(candidates, matched, discarded, args.max_discard, "parser-report")
    if not candidates:
        print("no candidate lines: zero rows from absent data and zero rows from")
        print("absent work are opposite findings, and this cannot tell them apart")
        return 2
    if not matched:
        print("nothing matched at all: the pattern and the source disagree")
        return 1
    return 1 if rate > args.max_discard else 0


if __name__ == "__main__":
    sys.exit(main())
