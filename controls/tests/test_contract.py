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
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SEARCH_DIRS = ("controls", "tools")


FIXTURE_FOUND_ITS_FAULT = 86


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
                if name.endswith(".py") and not name.startswith("test_"):
                    found.append(os.path.join(base, name))
    return sorted(found)


def main():
    checks = find_checks()
    failures = []

    for path in checks:
        relative = os.path.relpath(path, REPO)
        result = subprocess.run(
            [sys.executable, path, "--fixture"],
            capture_output=True, text=True,
        )
        code = result.returncode
        crashed = "Traceback (most recent call last)" in result.stderr
        if code == FIXTURE_FOUND_ITS_FAULT and not crashed:
            print("ok    %-28s --fixture found its planted fault" % relative)
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
