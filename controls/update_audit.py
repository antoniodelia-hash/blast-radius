#!/usr/bin/env python3
"""Compare a system before and after an update: what arrived, what vanished,
and what is now too large to be read.

An update is an actor. It installs components nobody asked for, and it drops
local changes while reporting that it restored them. Both were observed, four
weeks apart, from the same mechanism.

Three questions, and the third is the one everybody skips:

    appeared    components present after and not before
    vanished    components present before and not after
    oversized   components past the size at which the runtime stops
                returning the body, so the agent works without the
                instructions it believes it follows
    orphaned    a local patch whose target file moved, so reapplying it
                silently hit nothing -- the updater still says it restored

Exit codes
    0   nothing appeared unexpectedly, nothing vanished, nothing oversized
    1   at least one finding
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

READABLE_LIMIT = 100000


def inspect(observation):
    observation = as_mapping(observation, "observation")
    before = as_mapping(observation.get("before"), "before")
    after = as_mapping(observation.get("after"), "after")
    expected = set(as_strings(observation.get("expected_new"), "expected_new"))
    patches = as_mappings(observation.get("local_patches"), "local_patches")
    # .get(key, default) falls back only when the key is absent. A collector
    # writing "readable_limit": null handed None to a > comparison, and the
    # whole oversized check died on a typo in a config file.
    limit = as_number(observation.get("readable_limit"), "readable_limit", READABLE_LIMIT)

    findings = []
    for name in sorted(set(after) - set(before)):
        if name not in expected:
            findings.append((name, "appeared", "installed by the update, not requested"))
    for name in sorted(set(before) - set(after)):
        findings.append((name, "vanished", "present before the update, gone after"))
    for name, size in sorted(after.items()):
        # A size the collector wrote as "102716" or 102716.0 used to skip the
        # check entirely, so the one component past the limit was the one
        # reported clean. A size this cannot read is a finding of its own.
        if isinstance(size, bool) or not isinstance(size, (int, float)):
            findings.append((name, "unreadable-size",
                             "size is %r, so nothing was compared against the limit" % (size,)))
        elif size > limit:
            findings.append((name, "oversized",
                             "%d characters, past the readable limit %d" % (size, limit)))
    for patch in patches:
        marker = patch.get("marker")
        # target_file: null yields None, and None[:32] raises TypeError while
        # printing -- after the findings have been computed, so the run dies
        # with the answer already in hand.
        label = (as_text(patch.get("target_file"), "local_patches[].target_file", "")
                 or as_text(patch.get("name"), "local_patches[].name", "")
                 or "<patch>")
        occurrences = patch.get("marker_occurrences_after")
        # False == 0 in Python, and a count written "0" or -1 is not a count.
        # Anything that is not a whole number at or above zero was not
        # collected, whatever it looks like.
        if (isinstance(occurrences, bool) or not isinstance(occurrences, int)
                or occurrences < 0):
            # Not collected and zero are opposite findings, and treating the
            # first as clean is how an unchecked patch passes as restored.
            findings.append((label, "not-collected",
                             "no usable marker count for %r (%r): nothing was verified"
                             % (marker, occurrences)))
        elif occurrences == 0:
            findings.append((label, "orphaned",
                             "marker %r not found after update: reapply hit nothing"
                             % marker))
    examined = len(set(before) | set(after)) + len(patches)
    return examined, findings


def report(examined, findings, label):
    print("%-22s examined=%d problems=%d" % (label, examined, len(findings)))
    for name, kind, detail in findings:
        print("   %-32s %-11s %s" % (name[:32], kind, detail))
    return findings


FIXTURE = {
    "readable_limit": 100000,
    "before": {"skills/domain-a": 12000, "skills/domain-b": 8000},
    "after": {
        "skills/domain-a": 12000,
        "skills/domain-b": 8000,
        "skills/vendor-home-automation": 9000,
        "skills/vendor-paper-writing": 102716,   # the real one, to the character
        "skills/vendor-requested": 4000,
    },
    "expected_new": ["skills/vendor-requested"],
    "local_patches": [
        # The eighteen-day orphan: upstream moved the file, the reapply had no
        # target, and the updater reported that local changes were restored.
        {"name": "input-conversion", "target_file": "plugins/adapter.py",
         "marker": "Converted legacy", "marker_occurrences_after": 0},
        # A patch that really did survive: must stay silent.
        {"name": "mime-type", "target_file": "core/base.py",
         "marker": "application/vnd.ms-excel", "marker_occurrences_after": 2},
        # The collector never ran for this one. Silence here used to read
        # as health.
        {"name": "encoding-fix", "target_file": "core/text.py",
         "marker": "normalise_encoding"},
    ],
}

EXPECTED = {
    ("skills/vendor-home-automation", "appeared"),
    ("skills/vendor-paper-writing", "appeared"),
    ("skills/vendor-paper-writing", "oversized"),
    ("plugins/adapter.py", "orphaned"),
    ("core/text.py", "not-collected"),
}


def run_fixture():
    examined, findings = inspect(FIXTURE)
    report(examined, findings, "fixture")
    got = set((name, kind) for name, kind, _ in findings)
    print("\n--- fixture verdict ---")
    conforms = True
    if examined != 8:
        print("FAIL  examined %d items, the fixture holds 8" % examined)
        conforms = False
    else:
        print("ok    every component and patch was examined (8)")
    for pair in sorted(EXPECTED):
        if pair in got:
            print("ok    caught %s: %s" % pair)
        else:
            print("FAIL  missed %s: %s" % pair)
            conforms = False
    extra = got - EXPECTED
    if extra:
        print("FAIL  reported findings the fixture did not plant: %s" % sorted(extra))
        conforms = False
    else:
        print("ok    the requested skill and the surviving patch stayed silent")

    # The shape block is code like any other. A validation nobody exercises
    # is the shape of the fault this check exists to report, so the fixture
    # hands it the shapes that used to end in a traceback and exit 1.
    for description, broken in (
        ("a list where the observation belongs",
         ["x"]),
        ("a readable limit written as a string",
         {"readable_limit": "100000"}),
        ("an inventory that is a list",
         {"before": ["a"], "after": {}}),
    ):
        try:
            inspect(broken)
            print("FAIL  accepted %s" % description)
            conforms = False
        except Unusable:
            print("ok    refused %s" % description)

    if not conforms:
        print("\nfixture did not behave as declared: the audit cannot be trusted")
        return 3
    print("\nthe oversized arrival and the orphaned patch were both caught;")
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
        examined, findings = inspect(observation)
    except Unusable as error:
        # Exit 2, never 1: a shape this check cannot read is not a finding.
        print("unusable observation: %s" % error)
        return 2
    report(examined, findings, "update-audit")
    if examined == 0:
        print("examined zero components: that is a fault, not a quiet update")
        return 2
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
