#!/usr/bin/env python3
"""Decide which writes to an agent's own instruction files a brake refuses.

An agent allowed to edit its own instructions improves over time and, left
alone, only ever adds. Past a size the runtime stops returning the file's
body, and the agent works without the instructions it believes it follows.

Two ceilings, because one gives you a wall and no warning:

    hard        the write is refused
    operational the write passes and is marked in the log

Two exemptions that were learned the hard way, and both belong in the
decision rather than in a reviewer's head:

  * a write that REMOVES content always passes, whatever the size. A brake
    that blocks the fix teaches everyone to disable the brake.
  * vendor-owned files are exempt, decided by manifest membership and never
    by filename. They are required by the system prompt, and a diet applied
    to them is erased by the next update.

Exit codes
    0   every write examined, none refused
    1   at least one write refused
    2   nothing examined
    3   --fixture did not behave as declared
"""

import argparse
import json
import sys

# A fixture that behaved as designed exits with this, and nothing else
# does. Exit 1 is what a crashing program returns too, and the contract
# test used to read a traceback as proof that the check works.
FIXTURE_FOUND_ITS_FAULT = 86

LIMITS = {
    "instructions": {"hard": 40000, "operational": 30000},
    "reference": {"hard": 25000, "operational": 20000},  # scan:allow -- byte sizes
}


def decide(write, limits=None):
    """Return (verdict, reason). Verdict is refuse | mark | pass."""
    limits = limits or LIMITS
    kind = write.get("kind", "instructions")
    ceiling = limits.get(kind, limits["instructions"])
    before = write.get("size_before")
    after = write.get("size_after", 0)

    if write.get("vendor_owned"):
        return "pass", "vendor-owned: exempt by manifest membership"
    if before is not None and after <= before:
        return "pass", "write removes content (%d -> %d)" % (before, after)
    if after > ceiling["hard"]:
        return "refuse", "%d over hard ceiling %d for %s" % (after, ceiling["hard"], kind)
    if after > ceiling["operational"]:
        return "mark", "%d over operational line %d for %s" % (after, ceiling["operational"], kind)
    return "pass", "%d within limits" % after


def inspect(observation):
    writes = observation.get("writes") or []
    results = []
    for write in writes:
        verdict, reason = decide(write, observation.get("limits"))
        results.append((write.get("path", "<unnamed>"), verdict, reason))
    return len(writes), results


def report(examined, results, label):
    refused = [r for r in results if r[1] == "refuse"]
    marked = [r for r in results if r[1] == "mark"]
    print("%-22s examined=%d problems=%d marked=%d"
          % (label, examined, len(refused), len(marked)))
    for path, verdict, reason in results:
        if verdict != "pass":
            print("   %-10s %-28s %s" % (verdict.upper(), path, reason))
    return refused


FIXTURE = {
    "writes": [
        # The case that shaped the design: shrinking a file must always pass,
        # even while the file is still over every ceiling.
        {"path": "own/SKILL.md", "kind": "instructions",
         "size_before": 52000, "size_after": 47000},
        # Vendor file far above every ceiling. Refusing it would send the
        # agent to chop up a document that is not its own.
        {"path": "vendor/skill/SKILL.md", "kind": "instructions",
         "size_before": 50000, "size_after": 51000, "vendor_owned": True},
        # Between the lines: passes AND is marked. A single threshold would
        # either block this or say nothing about it.
        {"path": "own/growing.md", "kind": "instructions",
         "size_before": 29000, "size_after": 33000},
        # Over the hard ceiling.
        {"path": "own/runaway.md", "kind": "instructions",
         "size_before": 39000, "size_after": 41000},
        # Reference files have their own, lower ceilings.
        {"path": "own/references/detail.md", "kind": "reference",
         "size_before": 19000, "size_after": 26000},  # scan:allow -- byte sizes
        # Ordinary small write: silent pass.
        {"path": "own/small.md", "kind": "instructions",
         "size_before": 4000, "size_after": 4200},
    ],
}

EXPECTED = {
    "own/SKILL.md": "pass",
    "vendor/skill/SKILL.md": "pass",
    "own/growing.md": "mark",
    "own/runaway.md": "refuse",
    "own/references/detail.md": "refuse",
    "own/small.md": "pass",
}


def run_fixture():
    examined, results = inspect(FIXTURE)
    report(examined, results, "fixture")
    got = dict((path, verdict) for path, verdict, _ in results)

    print("\n--- fixture verdict ---")
    conforms = True
    if examined != len(FIXTURE["writes"]):
        print("FAIL  examined %d writes, fixture holds %d" % (examined, len(FIXTURE["writes"])))
        conforms = False
    else:
        print("ok    every seeded write was examined (%d)" % examined)
    for path, expected in sorted(EXPECTED.items()):
        actual = got.get(path)
        if actual == expected:
            print("ok    %-28s %s" % (path, expected))
        else:
            print("FAIL  %-28s expected=%s got=%s" % (path, expected, actual))
            conforms = False
    if not conforms:
        print("\nfixture did not behave as declared: the brake cannot be trusted")
        return 3
    print("\nshrinking writes and vendor files passed, the two ceilings held;")
    print("exiting 86: the code that means the fixture found the fault it planted")
    return FIXTURE_FOUND_ITS_FAULT


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("observation", nargs="?")
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()

    if args.fixture:
        return run_fixture()
    if not args.observation:
        parser.error("give an observation file, or --fixture")
    try:
        with open(args.observation, encoding="utf-8") as handle:
            observation = json.load(handle)
    except (OSError, ValueError) as error:
        print("unusable observation file: %s" % error)
        return 2

    examined, results = inspect(observation)
    refused = report(examined, results, "budget-brake")
    if examined == 0:
        print("examined zero writes: that is a fault, not a quiet day")
        return 2
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
