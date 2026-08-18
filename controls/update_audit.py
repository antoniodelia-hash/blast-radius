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

READABLE_LIMIT = 100000


def inspect(observation):
    before = observation.get("before") or {}
    after = observation.get("after") or {}
    expected = set(observation.get("expected_new") or [])
    patches = observation.get("local_patches") or []
    limit = observation.get("readable_limit", READABLE_LIMIT)

    findings = []
    for name in sorted(set(after) - set(before)):
        if name not in expected:
            findings.append((name, "appeared", "installed by the update, not requested"))
    for name in sorted(set(before) - set(after)):
        findings.append((name, "vanished", "present before the update, gone after"))
    for name, size in sorted(after.items()):
        if isinstance(size, int) and size > limit:
            findings.append((name, "oversized",
                             "%d characters, past the readable limit %d" % (size, limit)))
    for patch in patches:
        marker = patch.get("marker")
        target = patch.get("target_file")
        occurrences = patch.get("marker_occurrences_after")
        if occurrences == 0:
            findings.append((target or patch.get("name", "<patch>"), "orphaned",
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
    ],
}

EXPECTED = {
    ("skills/vendor-home-automation", "appeared"),
    ("skills/vendor-paper-writing", "appeared"),
    ("skills/vendor-paper-writing", "oversized"),
    ("plugins/adapter.py", "orphaned"),
}


def run_fixture():
    examined, findings = inspect(FIXTURE)
    report(examined, findings, "fixture")
    got = set((name, kind) for name, kind, _ in findings)
    print("\n--- fixture verdict ---")
    conforms = True
    if examined != 7:
        print("FAIL  examined %d items, the fixture holds 7" % examined)
        conforms = False
    else:
        print("ok    every component and patch was examined (7)")
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
    if not conforms:
        print("\nfixture did not behave as declared: the audit cannot be trusted")
        return 3
    print("\nthe oversized arrival and the orphaned patch were both caught;")
    print("exiting 1 on purpose, because a check that cannot fail is not a check")
    return 1


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
    examined, findings = inspect(observation)
    report(examined, findings, "update-audit")
    if examined == 0:
        print("examined zero components: that is a fault, not a quiet update")
        return 2
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
