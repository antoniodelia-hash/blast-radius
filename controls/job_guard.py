#!/usr/bin/env python3
"""Decide whether a scheduled agent job actually ran, and whether its
reported status can be believed.

This is the pure half of the check: it takes an observation file and
returns a verdict. Collecting that file from a live runtime is the
adapter's job, and lives elsewhere. Keeping the two apart is what lets
this run on a laptop with no runtime installed, and lets the verdict be
tested against failures that would be painful to reproduce for real.

Observation format (JSON):

    {
      "collected_at": "2026-08-18T07:20:00",
      "jobs": [
        {
          "id": "morning-digest",
          "last_status": "ok",
          "last_run_at": "2026-08-18T07:00:00",
          "expected_every_minutes": 1440,
          "output": "...the job's own last output, verbatim...",
          "reports_anomalies": false
        }
      ]
    }

`collected_at` is the clock. The check never reads the wall clock, so the
same observation file always produces the same verdict.

Exit codes
    0   examined at least one job, found nothing
    1   found at least one problem
    2   examined zero jobs -- a check that inspects nothing always passes

Usage
    job_guard.py observation.json
    job_guard.py --fixture
"""

import argparse
import datetime
import json
import os
import sys
import tempfile

# A fixture that behaved as designed exits with this, and nothing else
# does. Exit 1 is what a crashing program returns too, and the contract
# test used to read a traceback as proof that the check works.
FIXTURE_FOUND_ITS_FAULT = 86

# Strings that mean the run failed, whatever the status field says.
FAILURE_MARKERS = (
    "## Script Error",
    "Traceback (most recent call last)",
    "command not found",
    "No such file or directory",
    "Permission denied",
)

# Strings that mean the run finished but told nobody.
SILENT_DELIVERY_MARKERS = (
    "[alert]",
    "failed to send",
    "delivery suppressed",
    "no delivery targets",
)


def parse_time(value):
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def inspect(observation):
    """Return (examined, problems). A problem is (job_id, kind, detail)."""
    now = parse_time(observation["collected_at"])
    problems = []
    jobs = observation.get("jobs") or []

    for job in jobs:
        job_id = job.get("id", "<unnamed>")
        status = (job.get("last_status") or "").lower()
        output = job.get("output")
        reports_anomalies = bool(job.get("reports_anomalies"))

        # 1. The green that cannot turn red: status says ok, output says otherwise.
        if status == "ok" and output:
            for marker in FAILURE_MARKERS:
                if marker in output:
                    problems.append((job_id, "false-green",
                                     "status ok, output contains %r" % marker))
                    break

        # 2. A status nobody can check is not a status.
        if status == "ok" and not output:
            problems.append((job_id, "unverifiable",
                             "status ok with no output to check it against"))

        # 3. Ran, succeeded, reached nobody. Jobs whose trade is reporting
        #    anomalies are exempt: their output is meant to mention alerts.
        if output and not reports_anomalies:
            for marker in SILENT_DELIVERY_MARKERS:
                if marker in output:
                    problems.append((job_id, "silent-delivery-failure",
                                     "output contains %r while status is %r"
                                     % (marker, status or "unset")))
                    break

        # 4. The job that quietly stopped running.
        every = job.get("expected_every_minutes")
        last_run = job.get("last_run_at")
        if every and last_run:
            age = (now - parse_time(last_run)).total_seconds() / 60.0
            if age > 2 * every:
                problems.append((job_id, "stale",
                                 "last run %.0f minutes ago, expected every %d"
                                 % (age, every)))
        elif every and not last_run:
            problems.append((job_id, "never-ran",
                             "scheduled every %d minutes, never recorded a run" % every))

        # 5. An honest failure still needs to be seen.
        if status in ("error", "failed"):
            problems.append((job_id, "reported-failure", "status is %r" % status))

    return len(jobs), problems


def report(examined, problems, label):
    print("%-22s examined=%d problems=%d" % (label, examined, len(problems)))
    for job_id, kind, detail in problems:
        print("   %-22s %-24s %s" % (job_id, kind, detail))


# The fixture carries the failures that actually happened, in the shape
# they actually had. A job list of tidy successes would prove only that
# the parser reads JSON.
FIXTURE = {
    "collected_at": "2026-08-18T07:20:00",
    "jobs": [
        {
            # The original incident: the script failed, the agent wrote a
            # sensible summary about the failure, the turn closed cleanly,
            # and the scheduler recorded success.
            "id": "report-with-followup",
            "last_status": "ok",
            "last_run_at": "2026-08-18T07:00:00",
            "expected_every_minutes": 1440,
            "output": "## Script Error\nmodule not found: eb_lib\n",
        },
        {
            # One floor up: ran, succeeded, reached nobody.
            "id": "leadership-notice",
            "last_status": "ok",
            "last_run_at": "2026-08-18T06:30:00",
            "expected_every_minutes": 1440,
            "output": "[alert] telegram token rejected; continuing\n",
        },
        {
            # Mute for two months while its status stayed clean.
            "id": "weekly-scan",
            "last_status": "ok",
            "last_run_at": "2026-06-14T07:00:00",
            "expected_every_minutes": 10080,
            "output": "scan complete, 0 findings\n",
        },
        {
            # Status ok and nothing to check it against.
            "id": "opaque-job",
            "last_status": "ok",
            "last_run_at": "2026-08-18T05:00:00",
            "expected_every_minutes": 1440,
            "output": None,
        },
        {
            # Must stay silent: a sentinel whose trade is printing alerts,
            # running normally. Flagging this one would train everybody to
            # ignore the check.
            "id": "cron-sentinel",
            "last_status": "ok",
            "last_run_at": "2026-08-18T07:20:00",
            "expected_every_minutes": 1440,
            "output": "[alert] 12 anomalies across 5 profiles\nexamined=11 jobs\n",
            "reports_anomalies": True,
        },
        {
            # Must stay silent: an ordinary healthy job.
            "id": "healthy-job",
            "last_status": "ok",
            "last_run_at": "2026-08-18T07:15:00",
            "expected_every_minutes": 60,
            "output": "done, 4 records written\n",
        },
    ],
}

EXPECTED = {
    "report-with-followup": {"false-green"},
    "leadership-notice": {"silent-delivery-failure"},
    "weekly-scan": {"stale"},
    "opaque-job": {"unverifiable"},
    "cron-sentinel": set(),
    "healthy-job": set(),
}


def run_fixture():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "observation.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(FIXTURE, handle)
        with open(path, encoding="utf-8") as handle:
            observation = json.load(handle)

    examined, problems = inspect(observation)
    report(examined, problems, "fixture")

    found = {}
    for job_id, kind, _ in problems:
        found.setdefault(job_id, set()).add(kind)

    print("\n--- fixture verdict ---")
    conforms = True
    if examined != len(FIXTURE["jobs"]):
        print("FAIL  examined %d jobs, the fixture holds %d" % (examined, len(FIXTURE["jobs"])))
        conforms = False
    else:
        print("ok    every seeded job was examined (%d)" % examined)

    for job_id, expected_kinds in sorted(EXPECTED.items()):
        got = found.get(job_id, set())
        if got == expected_kinds:
            verdict = "ok   "
        else:
            verdict = "FAIL "
            conforms = False
        note = "  <- must stay silent" if not expected_kinds else ""
        print("%s %-22s expected=%-26s got=%s%s"
              % (verdict, job_id,
                 ",".join(sorted(expected_kinds)) or "(nothing)",
                 ",".join(sorted(got)) or "(nothing)", note))

    if not conforms:
        print("\nfixture did not behave as declared: the check cannot be trusted")
        return 3
    print("\nevery planted failure was caught and the two healthy jobs stayed quiet;")
    print("exiting 86: the code that means the fixture found the fault it planted")
    return FIXTURE_FOUND_ITS_FAULT


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("observation", nargs="?")
    parser.add_argument("--fixture", action="store_true", help="prove the check can fail")
    args = parser.parse_args()

    if args.fixture:
        return run_fixture()
    if not args.observation:
        parser.error("give an observation file, or --fixture")

    try:
        with open(args.observation, encoding="utf-8") as handle:
            observation = json.load(handle)
    except (OSError, ValueError) as error:
        # Exit 2, never 1: an unreadable observation is an invalid check,
        # and must not look like a check that ran and found problems.
        print("unusable observation file: %s" % error)
        return 2

    try:
        examined, problems = inspect(observation)
    except (KeyError, TypeError, ValueError) as error:
        print("observation file does not have the expected shape: %s" % error)
        return 2
    report(examined, problems, "job-guard")
    if examined == 0:
        print("examined zero jobs: that is a fault, not a healthy schedule")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
