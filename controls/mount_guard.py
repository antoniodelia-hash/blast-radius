#!/usr/bin/env python3
"""Check that the paths an agent depends on are real storage inside its own
namespace.

Service hardening can replace a home directory with an empty temporary
filesystem, and every path the service needs then has to be re-mounted
into its namespace explicitly. A forgotten mount raises nothing: the agent
writes, reads back what it wrote, and finds it, because inside its
namespace the file genuinely exists. Outside, nothing was ever written.

The observation therefore needs BOTH views. A check that asks only from
inside answers a different question, confidently.

Exit codes
    0   every required path is real storage
    1   at least one path is missing or namespace-only
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


def side_entry(value, side, path):
    """One side of a path: true/false, or an object describing the mount.

    Both shapes are legitimate and the fixture ships both, so neither is
    refused. Anything else is refused rather than coerced: a bare true was
    reaching .get("device") and raising AttributeError, which exits 1 -- the
    code this control documents as "a path is missing or namespace-only".
    """
    if value is None or isinstance(value, (bool, dict)):
        return value
    raise Unusable("%s[%s] must be true, false or an object, found %s"
                   % (side, path, type(value).__name__))


def inspect(observation):
    observation = as_mapping(observation, "observation")
    paths = as_strings(observation.get("required_paths"), "required_paths")
    inside = as_mapping(observation.get("visible_inside"), "visible_inside")
    outside = as_mapping(observation.get("present_outside"), "present_outside")
    # set() over a bare string turns "tmpfs" into five single letters, and a
    # path would then never match: a filter that cannot match is a filter
    # that approves everything.
    ephemeral = set(as_strings(observation.get("ephemeral_filesystems"),
                               "ephemeral_filesystems"))
    problems = []

    for path in paths:
        inside_entry = side_entry(inside.get(path), "visible_inside", path)
        outside_entry = side_entry(outside.get(path), "present_outside", path)
        seen_inside = bool(inside_entry)
        seen_outside = bool(outside_entry)
        backing = inside_entry.get("filesystem") if isinstance(inside_entry, dict) else None

        if not seen_inside:
            problems.append((path, "missing", "not visible inside the namespace"))
            continue
        if backing in ephemeral:
            problems.append((path, "ephemeral",
                             "backed by %s: writes vanish on restart" % backing))
            continue
        if not seen_outside:
            # The exact shape of the incident: readable from inside, absent
            # on disk. Presents as a deletion, with no delete anywhere.
            problems.append((path, "namespace-only",
                             "reads back from inside, absent outside"))
            continue
        # Present on both sides is not the same as being the same storage.
        # Without an identifier to compare, the check would approve a path
        # that exists in two unrelated places.
        inside_id = inside_entry.get("device") if isinstance(inside_entry, dict) else None
        outside_id = outside_entry.get("device") if isinstance(outside_entry, dict) else None
        if inside_id is None or outside_id is None:
            problems.append((path, "unproven",
                             "no device identifier on one side: sameness not established"))
        elif inside_id != outside_id:
            problems.append((path, "different-storage",
                             "inside device %s, outside device %s" % (inside_id, outside_id)))
    return len(paths), problems


def report(examined, problems, label):
    print("%-22s examined=%d problems=%d" % (label, examined, len(problems)))
    for path, kind, detail in problems:
        print("   %-28s %-14s %s" % (path, kind, detail))
    return problems


FIXTURE = {
    "ephemeral_filesystems": ["tmpfs"],
    "required_paths": [
        "/data/output",          # the incident: inside only
        "/data/knowledge",       # forgotten entirely
        "/data/state",           # on a temporary filesystem
        "/data/config",          # healthy: must stay silent
        "/data/shared",          # on both sides, sameness never established
        "/data/twin",            # two different devices behind one path
    ],
    "visible_inside": {
        "/data/output": {"filesystem": "overlay"},
        "/data/state": {"filesystem": "tmpfs"},
        "/data/config": {"filesystem": "ext4", "device": "8:1"},
        "/data/shared": {"filesystem": "ext4", "device": "8:1"},
        "/data/twin": {"filesystem": "ext4", "device": "8:1"},
    },
    "present_outside": {
        "/data/config": {"device": "8:1"},
        "/data/knowledge": True,
        "/data/shared": True,
        "/data/twin": {"device": "252:3"},
    },
}

EXPECTED = {
    "/data/output": "namespace-only",
    "/data/knowledge": "missing",
    "/data/state": "ephemeral",
    "/data/shared": "unproven",
    "/data/twin": "different-storage",
}


def run_fixture():
    examined, problems = inspect(FIXTURE)
    report(examined, problems, "fixture")
    got = dict((path, kind) for path, kind, _ in problems)
    print("\n--- fixture verdict ---")
    conforms = True
    if examined != len(FIXTURE["required_paths"]):
        print("FAIL  examined %d paths, fixture holds %d"
              % (examined, len(FIXTURE["required_paths"])))
        conforms = False
    else:
        print("ok    every required path was examined (%d)" % examined)
    for path in FIXTURE["required_paths"]:
        expected = EXPECTED.get(path)
        actual = got.get(path)
        if expected == actual:
            note = "  <- must stay silent" if expected is None else ""
            print("ok    %-20s %s%s" % (path, expected or "(nothing)", note))
        else:
            print("FAIL  %-20s expected=%s got=%s" % (path, expected, actual))
            conforms = False

    # The shape block is code like any other. A validation nobody exercises
    # is the shape of the fault this check exists to report, so the fixture
    # hands it the shapes that used to end in a traceback and exit 1.
    for description, broken in (
        ("a list where the observation belongs",
         ["x"]),
        ("an ephemeral filesystem list written as one string",
         {"required_paths": ["/data"], "ephemeral_filesystems": "tmpfs"}),
        ("a mount side that is neither a flag nor an object",
         {"required_paths": ["/data"], "visible_inside": {"/data": 7}}),
    ):
        try:
            inspect(broken)
            print("FAIL  accepted %s" % description)
            conforms = False
        except Unusable:
            print("ok    refused %s" % description)

    if not conforms:
        print("\nfixture did not behave as declared: the guard cannot be trusted")
        return 3
    print("\nthe path that reads back from inside and is absent outside was caught;")
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

    try:
        examined, problems = inspect(observation)
    except Unusable as error:
        # Exit 2, never 1: a shape this check cannot read is not a finding.
        print("unusable observation: %s" % error)
        return 2
    report(examined, problems, "mount-guard")
    if examined == 0:
        print("examined zero paths: that is a fault, not a clean namespace")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
