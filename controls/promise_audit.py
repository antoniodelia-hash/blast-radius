#!/usr/bin/env python3
"""Compare what an agent said it would do against what the records show.

A message that describes an act is delivered, well formed, and pleasant.
The act behind it is a separate event. Delivery monitoring cannot tell the
two apart, because the message really was delivered.

Feed it the agent's turns and the register of acts. It reports promises it
could not match to a recorded act, and it prints THE SENTENCE that
triggered the match rather than the opening line of the message: the
difference between a false positive dismissed in two seconds and one that
costs a re-read.

Exit codes
    0   every turn examined, every promise matched
    1   at least one promise has no act behind it
    2   nothing examined
    3   --fixture did not behave as declared
"""

import argparse
import json
import re
import sys

# A fixture that behaved as designed exits with this, and nothing else
# does. Exit 1 is what a crashing program returns too, and the contract
# test used to read a traceback as proof that the check works.
FIXTURE_FOUND_ITS_FAULT = 86

# Phrasings that describe an act the system is expected to perform. Kept
# deliberately narrow: a broad matcher turns every polite sentence into an
# alert, and an alert stream nobody reads is the failure this check is for.
PROMISE_PATTERNS = [
    r"\bI'?ll (?:pass|forward|send|file|register|open|notify)\b[^.]*",
    r"\bI'?m (?:sending|forwarding|filing|registering)\b[^.]*",
    r"\bI(?:'ve| have) (?:filed|registered|forwarded|opened)\b[^.]*",
    r"\bI'?ll take care of (?:it|this)\b[^.]*",
]
COMPILED = [re.compile(p, re.IGNORECASE) for p in PROMISE_PATTERNS]


def find_promise(text):
    """Return the matched sentence, or None."""
    for pattern in COMPILED:
        found = pattern.search(text or "")
        if found:
            return " ".join(found.group(0).split())
    return None


def inspect(observation):
    turns = observation.get("turns") or []
    acts = observation.get("acts") or []
    problems = []

    by_turn = {}
    for act in acts:
        by_turn.setdefault(act.get("turn_id"), []).append(act)

    for turn in turns:
        sentence = find_promise(turn.get("text"))
        if not sentence:
            continue
        turn_id = turn.get("id")
        recorded = by_turn.get(turn_id, [])
        if not recorded:
            problems.append((turn_id, "unkept", sentence))
        elif len(recorded) > 1:
            problems.append((turn_id, "duplicated",
                             "%d acts recorded for one promise: %s" % (len(recorded), sentence)))
    return len(turns), problems


def report(examined, problems, label):
    print("%-22s examined=%d problems=%d" % (label, examined, len(problems)))
    for turn_id, kind, detail in problems:
        print("   %-12s %-12s %s" % (turn_id, kind, detail))
    return problems


# The four real promises from a 62-day window, plus the shapes that must
# stay silent. The duplicated case is here because deduplication was
# missing from the first version of the fix and created twin requests.
FIXTURE = {
    "turns": [
        {"id": "t1", "text": "That request sits outside what I can write here. "
                             "I'll pass it to the operator, I'll take care of it."},
        {"id": "t2", "text": "Here are the figures you asked for. "
                             "I'm sending them the message with the rates."},
        {"id": "t3", "text": "Understood. Alright, I'll forward the request to them."},
        {"id": "t4", "text": "I've filed proposal 27 for review."},
        {"id": "t5", "text": "The window closes on Friday, and the crew is already booked."},
        {"id": "t6", "text": "I'll pass this on as soon as the gate approves it."},
    ],
    "acts": [
        {"turn_id": "t4", "kind": "proposal_filed"},
        {"turn_id": "t6", "kind": "request_filed"},
        {"turn_id": "t6", "kind": "request_filed"},
    ],
}

EXPECTED = {"t1": "unkept", "t2": "unkept", "t3": "unkept", "t6": "duplicated"}


def run_fixture():
    examined, problems = inspect(FIXTURE)
    report(examined, problems, "fixture")
    got = dict((turn_id, kind) for turn_id, kind, _ in problems)

    print("\n--- fixture verdict ---")
    conforms = True
    if examined != len(FIXTURE["turns"]):
        print("FAIL  examined %d turns, fixture holds %d" % (examined, len(FIXTURE["turns"])))
        conforms = False
    else:
        print("ok    every seeded turn was examined (%d)" % examined)
    for turn_id in ("t1", "t2", "t3", "t4", "t5", "t6"):
        expected = EXPECTED.get(turn_id)
        actual = got.get(turn_id)
        if expected == actual:
            note = "  <- must stay silent" if expected is None else ""
            print("ok    %-4s %s%s" % (turn_id, expected or "(nothing)", note))
        else:
            print("FAIL  %-4s expected=%s got=%s" % (turn_id, expected, actual))
            conforms = False
    sentences = [detail for _, kind, detail in problems if kind == "unkept"]
    if all(s.lower().startswith("i'") or s.lower().startswith("i ") for s in sentences):
        print("ok    the triggering sentence is reported, not the message opening")
    else:
        print("FAIL  reported something other than the triggering sentence")
        conforms = False

    if not conforms:
        print("\nfixture did not behave as declared: the audit cannot be trusted")
        return 3
    print("\nthree empty promises caught, the kept one and the plain turn stayed quiet;")
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
    report(examined, problems, "promise-audit")
    if examined == 0:
        print("examined zero turns: that is a fault, not a silent agent")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
