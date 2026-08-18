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


def inspect(observation):
    paths = observation.get("required_paths") or []
    inside = observation.get("visible_inside") or {}
    outside = observation.get("present_outside") or {}
    ephemeral = set(observation.get("ephemeral_filesystems") or [])
    problems = []

    for path in paths:
        seen_inside = bool(inside.get(path))
        seen_outside = bool(outside.get(path))
        backing = (inside.get(path) or {}).get("filesystem") if isinstance(inside.get(path), dict) else None

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
    ],
    "visible_inside": {
        "/data/output": {"filesystem": "overlay"},
        "/data/state": {"filesystem": "tmpfs"},
        "/data/config": {"filesystem": "ext4"},
    },
    "present_outside": {
        "/data/config": True,
        "/data/knowledge": True,
    },
}

EXPECTED = {
    "/data/output": "namespace-only",
    "/data/knowledge": "missing",
    "/data/state": "ephemeral",
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
    examined, problems = inspect(observation)
    report(examined, problems, "mount-guard")
    if examined == 0:
        print("examined zero paths: that is a fault, not a clean namespace")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
