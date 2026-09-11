#!/usr/bin/env python3
"""Check that every check in this repository can fail.

A check that cannot fail is indistinguishable from one that works, and it
is the failure mode that hides all the others. So the contract is tested
rather than promised:

    every executable check exposes --fixture
    --fixture seeds real failure shapes and exits 86, and only 86
    exit 3 means the fixture ran and did not behave as declared

86 is the whole point of this file. It used to accept exit 1 as proof that
a check can fail -- and a Python program that raises an exception exits 1
as well, so a fixture that crashed on its first line was recorded as
working. An external judge found it by planting a broken fixture; the same
plant now sits in this test's own proofs.

This test declares how many checks it examined and refuses to pass on
zero. It is the same rule it enforces, applied to itself.

Exit codes
    0   every check honoured the contract
    1   at least one check did not
    2   found no checks to examine
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SEARCH_DIRS = ("controls", "tools")


FIXTURE_FOUND_ITS_FAULT = 86

# A fixture seeds its own data and answers nobody, so it has no reason to
# take this long. Without a limit, one fixture waiting on a prompt or a
# socket holds the whole suite open for as long as CI allows.
FIXTURE_TIMEOUT_SECONDS = 60

# A traceback at the start of a line, which is where Python puts one. The
# bare substring also matched checks that scan and echo untrusted text --
# job output, staged files -- so a fixture that had done its job was
# reported as having crashed on the strength of what it was quoting.
TRACEBACK_LINE = re.compile(r"^Traceback \(most recent call last\):$", re.MULTILINE)

# The summary line every check prints, which is the authoritative one.
SUMMARY = re.compile(r"examined=(\d+)")


def find_checks():
    """Every .py under the search directories, at any depth.

    Listing only the top level would miss a control filed one folder down,
    and miss it silently.
    """
    found = []
    for directory in SEARCH_DIRS:
        full = os.path.join(REPO, directory)
        if not os.path.isdir(full):
            continue
        for base, dirs, names in os.walk(full):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
            for name in sorted(names):
                if not name.endswith(".py") or name.startswith("test_"):
                    continue
                path = os.path.join(base, name)
                # A check is a file that offers --fixture. Running every .py
                # as a check would run a helper module as a script: a
                # definitions-only file exits 0 and gets reported as "this
                # check cannot fail", which points at the wrong cause and
                # executes import-time side effects on the way.
                try:
                    with open(path, encoding="utf-8") as handle:
                        if "--fixture" not in handle.read():
                            continue
                except (OSError, UnicodeDecodeError):
                    continue
                found.append(path)
    return sorted(found)


def main():
    checks = find_checks()
    failures = []

    for path in checks:
        relative = os.path.relpath(path, REPO)
        try:
            result = subprocess.run(
                [sys.executable, path, "--fixture"],
                capture_output=True, text=True,
                # Pinned rather than locale-dependent, or a fixture holding
                # an accented name dies in the decoder under LC_ALL=C and
                # the exception leaves main() as exit 1 -- which is also
                # "a check failed", the ambiguity this file removes.
                encoding="utf-8", errors="replace",
                stdin=subprocess.DEVNULL, timeout=FIXTURE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            failures.append((relative, "--fixture did not finish in %ds"
                             % FIXTURE_TIMEOUT_SECONDS))
            continue
        code = result.returncode
        crashed = bool(TRACEBACK_LINE.search(result.stderr or ""))
        # 86 alone is a password a hollow fixture can say. A fixture that
        # ran has also declared how much it examined, so the contract asks
        # for the evidence rather than the announcement.
        #
        # The last declaration on stdout, not the first anywhere: several
        # checks print "examined=0" on an early path before the real
        # summary, and stderr can carry a quoted one.
        declarations = SUMMARY.findall(result.stdout or "")
        declared = declarations[-1] if declarations else None
        examined_zero = declared == "0"

        if code == FIXTURE_FOUND_ITS_FAULT and not crashed and declared and not examined_zero:
            print("ok    %-28s --fixture found its planted fault (examined=%s)"
                  % (relative, declared))
        elif code == FIXTURE_FOUND_ITS_FAULT and not crashed and not declared:
            failures.append((relative, "--fixture exited %d without declaring what it "
                                       "examined: 86 is not evidence"
                             % FIXTURE_FOUND_ITS_FAULT))
        elif code == FIXTURE_FOUND_ITS_FAULT and examined_zero and not crashed:
            failures.append((relative, "--fixture exited %d having examined nothing"
                             % FIXTURE_FOUND_ITS_FAULT))
        elif crashed:
            last = [l for l in result.stderr.strip().splitlines() if l.strip()]
            failures.append((relative, "--fixture crashed: %s"
                             % (last[-1][:70] if last else "traceback")))
        elif code == 0:
            failures.append((relative, "--fixture exited 0: this check cannot fail"))
        elif code == 1:
            failures.append((relative, "--fixture exited 1, which is also what a crash "
                                       "returns: use %d" % FIXTURE_FOUND_ITS_FAULT))
        elif code == 2:
            failures.append((relative, "--fixture examined nothing"))
        elif code == 3:
            failures.append((relative, "--fixture ran and did not match its own expectations"))
        else:
            failures.append((relative, "--fixture exited %d, expected %d"
                             % (code, FIXTURE_FOUND_ITS_FAULT)))

    print("\n%-22s examined=%d problems=%d" % ("contract", len(checks), len(failures)))
    for relative, detail in failures:
        print("   %-28s %s" % (relative, detail))

    if not checks:
        print("found no checks to examine: that is a fault, not a clean repository")
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
