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


# ---- the shape of an observation ---------------------------------------
# Copied verbatim into every control that reads one. These files are made
# to be taken one at a time, so each carries its own validation instead of
# importing it, and tools/copy_check.py fails when the copies drift apart.
#
# json.load promises valid JSON and says nothing about shape. A list where
# an object belongs used to raise AttributeError, and an uncaught exception
# exits 1 -- the code these controls document as "I found a problem". That
# made a crash indistinguishable from a verdict, which is the failure this
# repository exists to describe. An outside review found it in six controls
# at once on 2026-09-11, with one of them crashing on the shape its own
# fixture ships.
#
# Some helpers are unused in some controls. The copies are kept identical
# on purpose: an identical copy is one whose drift can be checked.


class Unusable(ValueError):
    """The observation cannot be read, so no verdict can be given."""


def as_mapping(value, where):
    """The value as an object. Absent reads as empty, a wrong type refuses."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Unusable("%s must be an object, found %s"
                       % (where, type(value).__name__))
    return value


def as_mappings(value, where):
    """A list of objects: the shape of every "one entry per thing" field."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise Unusable("%s must be a list, found %s"
                       % (where, type(value).__name__))
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise Unusable("%s[%d] must be an object, found %s"
                           % (where, index, type(item).__name__))
    return value


def as_number(value, where, default=None):
    """A number. A stringified or null count is refused, never guessed."""
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Unusable("%s must be a number, found %r" % (where, value))
    return value


def as_text(value, where, default=""):
    """A string. A number here used to reach re.search and raise TypeError."""
    if value is None:
        return default
    if not isinstance(value, str):
        raise Unusable("%s must be a string, found %s"
                       % (where, type(value).__name__))
    return value


def as_strings(value, where):
    """A list of strings. set() over a bare string silently becomes letters."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise Unusable("%s must be a list of strings, found %s"
                       % (where, type(value).__name__))
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise Unusable("%s[%d] must be a string, found %s"
                           % (where, index, type(item).__name__))
    return value
# ---- end of the shape block --------------------------------------------

LIMITS = {
    "instructions": {"hard": 40000, "operational": 30000},
    "reference": {"hard": 25000, "operational": 20000},  # scan:allow -- byte sizes
}


def strict_bool(value, field):
    """Accept only a real boolean.

    A JSON file carrying "false" as a string is truthy in Python, so an
    exemption meant to be off would have been read as on. An observation
    that says something unreadable gets refused instead of guessed.
    """
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (field, value))
    return value


def decide(write, limits=None):
    """Return (verdict, reason). Verdict is refuse | mark | pass."""
    limits = as_mapping(limits, "limits") or LIMITS
    kind = as_text(write.get("kind"), "kind", "instructions")
    # dict.get(key, default) evaluates the default whether or not it is
    # needed: limits.get(kind, limits["instructions"]) raised KeyError on
    # every write as soon as an observation brought its own limits without
    # an "instructions" entry -- including the writes that were in it.
    ceiling = (as_mapping(limits.get(kind), "limits[%s]" % kind)
               or LIMITS.get(kind) or LIMITS["instructions"])
    hard = as_number(ceiling.get("hard"), "limits[%s].hard" % kind)
    operational = as_number(ceiling.get("operational"), "limits[%s].operational" % kind)
    if hard is None or operational is None:
        raise Unusable("limits[%s] needs both operational and hard" % kind)
    before = as_number(write.get("size_before"), "size_before")
    after = as_number(write.get("size_after"), "size_after", 0)

    if strict_bool(write.get("vendor_owned"), "vendor_owned"):
        return "pass", "vendor-owned: exempt by manifest membership"
    if before is not None and after <= before:
        # Equal sizes land here too, so the reason says what was measured.
        return "pass", "write does not grow the file (%d -> %d)" % (before, after)
    if after > hard:
        return "refuse", "%d over hard ceiling %d for %s" % (after, hard, kind)
    if after > operational:
        return "mark", "%d over operational line %d for %s" % (after, operational, kind)
    return "pass", "%d within limits" % after


def inspect(observation):
    observation = as_mapping(observation, "observation")
    writes = as_mappings(observation.get("writes"), "writes")
    results = []
    for write in writes:
        verdict, reason = decide(write, observation.get("limits"))
        results.append((as_text(write.get("path"), "path", "<unnamed>"), verdict, reason))
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

    # The shape block is code like any other. A validation nobody exercises
    # is the shape of the fault this check exists to report, so the fixture
    # hands it the shapes that used to end in a traceback and exit 1.
    for description, broken in (
        ("a list where the observation belongs",
         ["x"]),
        ("a ceiling written as a string",
         {"limits": {"instructions": {"operational": "big", "hard": 2}},
          "writes": [{"path": "p", "size_after": 10}]}),
        ("a size written as a string",
         {"writes": [{"path": "p", "size_before": 1, "size_after": "41000"}]}),
    ):
        try:
            inspect(broken)
            print("FAIL  accepted %s" % description)
            conforms = False
        except Unusable:
            print("ok    refused %s" % description)

    # The KeyError that started this: an observation carrying its own limits
    # without an "instructions" entry killed every write, including the ones
    # the mapping did cover, because dict.get evaluated its default anyway.
    partial = {"limits": {"reference": {"operational": 100, "hard": 200}},
               "writes": [{"path": "own/ref.md", "kind": "reference", "size_after": 10},
                          {"path": "own/skill.md", "kind": "instructions", "size_after": 10}]}
    try:
        seen, verdicts = inspect(partial)
        if seen == 2 and all(v == "pass" for _, v, _ in verdicts):
            print("ok    limits missing a kind fall back to the built-in ceiling")
        else:
            print("FAIL  partial limits gave examined=%d verdicts=%s"
                  % (seen, [v for _, v, _ in verdicts]))
            conforms = False
    except Exception as error:
        print("FAIL  partial limits raised %s: %s" % (type(error).__name__, error))
        conforms = False

    if not conforms:
        print("\nfixture did not behave as declared: the brake cannot be trusted")
        return 3
    print("\nshrinking writes and vendor files passed, the two ceilings held;")
    print("exiting 86: the code that means the fixture found the fault it planted")
    return FIXTURE_FOUND_ITS_FAULT


def main():
    parser = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
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

    try:
        examined, results = inspect(observation)
    except Unusable as error:
        # Exit 2, never 1: a shape this check cannot read is not a finding.
        print("unusable observation: %s" % error)
        return 2
    except ValueError as error:
        print("observation refused: %s" % error)
        return 2
    refused = report(examined, results, "budget-brake")
    if examined == 0:
        print("examined zero writes: that is a fault, not a quiet day")
        return 2
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
