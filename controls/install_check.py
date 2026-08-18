#!/usr/bin/env python3
"""Ask whether a guardrail is active in the live process, rather than
whether it was declared somewhere.

A hook can appear in a configuration file and never be registered. Reading
the configuration answers "was it declared". This answers "is it running",
which is a different question with the same shape of output.

The four failure modes it separates, all observed:

  declared-not-registered   the config line is there, the runtime dropped it
                            (a missing allowlist, a prompt with no terminal)
  invisible-in-namespace    registered, and the command cannot be seen from
                            inside the service's namespace -- most hooks
                            FAIL OPEN, so the write proceeds with a warning
  process-predates-config   the file on disk is newer than the process, and
                            hooks register only at start: the edit is inert
  active                    reachable from inside the live process

Exit codes
    0   every declared guardrail is active
    1   at least one is declared and not active
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


def classify(guardrail):
    if not guardrail.get("registered_in_process"):
        return "declared-not-registered", guardrail.get("why", "runtime did not register it")
    if not guardrail.get("command_visible_in_namespace"):
        return "invisible-in-namespace", "fails open: the write proceeds with a warning"
    config_mtime = guardrail.get("config_mtime")
    process_start = guardrail.get("process_started_at")
    if config_mtime and process_start and config_mtime > process_start:
        return "process-predates-config", ("config changed at %s, process started at %s"
                                           % (config_mtime, process_start))
    return "active", "reachable inside the live process"


def inspect(observation):
    guardrails = observation.get("guardrails") or []
    results = []
    for guardrail in guardrails:
        state, detail = classify(guardrail)
        results.append((guardrail.get("name", "<unnamed>"), state, detail))
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
        {"name": "brake-delta", "registered_in_process": True,
         "command_visible_in_namespace": True,
         "config_mtime": "2026-08-16T09:00:00", "process_started_at": "2026-08-17T04:22:00"},
    ],
}

EXPECTED = {
    "brake-alpha": "declared-not-registered",
    "brake-beta": "invisible-in-namespace",
    "brake-gamma": "process-predates-config",
    "brake-delta": "active",
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
    if not conforms:
        print("\nfixture did not behave as declared: the check cannot be trusted")
        return 3
    print("\nall four states told apart, including the one that fails open;")
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
    problems = report(examined, results, "install-check")
    if examined == 0:
        print("examined zero guardrails: that is a fault, not a protected system")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
