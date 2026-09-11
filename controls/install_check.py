#!/usr/bin/env python3
"""Ask whether a guardrail is active in the live process, rather than
whether it was declared somewhere.

A hook can appear in a configuration file and never be registered. Reading
the configuration answers "was it declared". This answers "is it running",
which is a different question with the same shape of output.

The failure modes it separates, the first four all observed:

  declared-not-registered   the config line is there, the runtime dropped it
                            (a missing allowlist, a prompt with no terminal)
  invisible-in-namespace    registered, and the command cannot be seen from
                            inside the service's namespace -- most hooks
                            FAIL OPEN, so the write proceeds with a warning
  process-predates-config   the file on disk is newer than the process, and
                            hooks register only at start: the edit is inert
  unreadable-timing         a timestamp this check cannot read, which is
                            never reported as active
  unproven-timing           the two timestamps are close and only one of them
                            carries a time zone: their order is not established
  active                    reachable from inside the live process

Exit codes
    0   every declared guardrail is active
    1   at least one is declared and not active
    2   nothing examined
    3   --fixture did not behave as declared
"""

import argparse
import datetime
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


# A gap smaller than this, between one time that carries a zone and one that
# does not, is a gap a zone offset could invent or erase. No offset on earth
# reaches a day. Two times that both lack a zone come off the same clock and
# are compared as they are: the fixture caught the first version of this rule
# calling that pair unproven, which would have made every ordinary collector
# unreadable.
ZONE_DOUBT_SECONDS = 24 * 60 * 60


def moment(value, where):
    """(seconds, zone_known) from an epoch number or an ISO 8601 string.

    Comparing an epoch to an ISO string raises TypeError, and comparing two
    ISO strings as text is only correct while every one of them is written
    the same way: an offset, or a month written 8 instead of 08, decides
    the verdict silently. Both sides are brought to the same yardstick.

    A string without a zone is read as UTC and flagged, because reading it
    as local time is a choice that moves the instant by hours and says so
    nowhere. What the flag buys is the "unproven" verdict below: a gap of
    minutes between a zoned and an unzoned time is not evidence.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise Unusable("%s must be a time, found %r" % (where, value))
    if isinstance(value, (int, float)):
        return float(value), True
    if not isinstance(value, str):
        raise Unusable("%s must be a time, found %s" % (where, type(value).__name__))
    try:
        parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise Unusable("%s is not a time this check can read: %r" % (where, value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=datetime.timezone.utc).timestamp(), False
    return parsed.timestamp(), True


def classify(guardrail):
    if not guardrail.get("registered_in_process"):
        return "declared-not-registered", as_text(
            guardrail.get("why"), "why", "runtime did not register it")
    if not guardrail.get("command_visible_in_namespace"):
        return "invisible-in-namespace", "fails open: the write proceeds with a warning"
    raw_config = guardrail.get("config_mtime")
    raw_start = guardrail.get("process_started_at")
    try:
        config_mtime = moment(raw_config, "config_mtime")
        process_start = moment(raw_start, "process_started_at")
    except Unusable as error:
        # Fail closed: a timing this check cannot read is never an "active".
        return "unreadable-timing", str(error)
    if config_mtime is not None and process_start is not None:
        gap = config_mtime[0] - process_start[0]
        if config_mtime[1] != process_start[1] and abs(gap) < ZONE_DOUBT_SECONDS:
            # Fail closed again: within a day, and with a zone missing on one
            # side, the order of the two events is a guess.
            return "unproven-timing", ("%s and %s are %.0f minutes apart and only one "
                                       "carries a time zone: an offset decides this"
                                       % (raw_config, raw_start, abs(gap) / 60))
        if gap > 0:
            return "process-predates-config", ("config changed at %s, process started at %s"
                                               % (raw_config, raw_start))
    return "active", "reachable inside the live process"


def inspect(observation):
    guardrails = as_mappings(
        as_mapping(observation, "observation").get("guardrails"), "guardrails")
    results = []
    for guardrail in guardrails:
        state, detail = classify(guardrail)
        results.append((as_text(guardrail.get("name"), "name", "<unnamed>"), state, detail))
    return len(guardrails), results


def report(examined, results, label):
    problems = [r for r in results if r[1] != "active"]
    print("%-22s examined=%d problems=%d" % (label, examined, len(problems)))
    for name, state, detail in results:
        if state != "active":
            print("   %-18s %-24s %s" % (name, state, detail))
    return problems


FIXTURE = {
    "guardrails": [
        {"name": "brake-alpha", "registered_in_process": False,
         "command_visible_in_namespace": True,
         "why": "no shell-hooks allowlist in the profile: prompt had no terminal"},
        {"name": "brake-beta", "registered_in_process": True,
         "command_visible_in_namespace": False},
        {"name": "brake-gamma", "registered_in_process": True,
         "command_visible_in_namespace": True,
         "config_mtime": "2026-08-18T09:00:00", "process_started_at": "2026-08-17T04:22:00"},
        # Must stay silent: declared, registered, visible, process newer.
        # Both times lack a zone, which is the ordinary collector: they come
        # off one clock and are compared as they are.
        {"name": "brake-delta", "registered_in_process": True,
         "command_visible_in_namespace": True,
         "config_mtime": "2026-08-16T09:00:00", "process_started_at": "2026-08-17T04:22:00"},
        # An epoch against a zoneless string, two hours apart -- which is
        # exactly one offset. The order of the two events is a guess, and a
        # guess is never reported as active.
        {"name": "brake-epsilon", "registered_in_process": True,
         "command_visible_in_namespace": True,
         "config_mtime": 1755500400, "process_started_at": "2025-08-18T09:00:00"},
        # A timestamp nothing can parse. Reading it as absent would have
        # left this guardrail reported as active on no evidence at all.
        {"name": "brake-zeta", "registered_in_process": True,
         "command_visible_in_namespace": True,
         "config_mtime": "last tuesday", "process_started_at": "2026-08-17T04:22:00"},
    ],
}

EXPECTED = {
    "brake-alpha": "declared-not-registered",
    "brake-beta": "invisible-in-namespace",
    "brake-gamma": "process-predates-config",
    "brake-delta": "active",
    "brake-epsilon": "unproven-timing",
    "brake-zeta": "unreadable-timing",
}


def run_fixture():
    examined, results = inspect(FIXTURE)
    report(examined, results, "fixture")
    got = dict((name, state) for name, state, _ in results)
    print("\n--- fixture verdict ---")
    conforms = True
    if examined != len(FIXTURE["guardrails"]):
        print("FAIL  examined %d guardrails, fixture holds %d"
              % (examined, len(FIXTURE["guardrails"])))
        conforms = False
    else:
        print("ok    every declared guardrail was examined (%d)" % examined)
    for name, expected in sorted(EXPECTED.items()):
        actual = got.get(name)
        if actual == expected:
            note = "  <- must stay silent" if expected == "active" else ""
            print("ok    %-14s %s%s" % (name, expected, note))
        else:
            print("FAIL  %-14s expected=%s got=%s" % (name, expected, actual))
            conforms = False

    # The shape block is code like any other. A validation nobody exercises
    # is the shape of the fault this check exists to report, so the fixture
    # hands it the shapes that used to end in a traceback and exit 1.
    for description, broken in (
        ("a list where the observation belongs",
         ["x"]),
        ("a guardrail that is a string",
         {"guardrails": ["brake-alpha"]}),
    ):
        try:
            inspect(broken)
            print("FAIL  accepted %s" % description)
            conforms = False
        except Unusable:
            print("ok    refused %s" % description)

    if not conforms:
        print("\nfixture did not behave as declared: the check cannot be trusted")
        return 3
    print("\nall six states told apart, including the one that fails open and the")
    print("two that refuse to call a timing they cannot read an active guardrail;")
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
    problems = report(examined, results, "install-check")
    if examined == 0:
        print("examined zero guardrails: that is a fault, not a protected system")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
