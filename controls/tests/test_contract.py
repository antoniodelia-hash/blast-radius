#!/usr/bin/env python3
"""Check that every check in this repository can fail.

A check that cannot fail is indistinguishable from one that works, and it
is the failure mode that hides all the others. So the contract is tested
rather than promised:

    every executable check exposes --fixture
    --fixture seeds real failure shapes and exits non-zero
    exit 3 means the fixture ran and did not behave as declared

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


def find_checks():
    found = []
    for directory in SEARCH_DIRS:
        full = os.path.join(REPO, directory)
        if not os.path.isdir(full):
            continue
        for name in sorted(os.listdir(full)):
            if name.endswith(".py") and not name.startswith("test_"):
                found.append(os.path.join(full, name))
    return found


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
        if code == 0:
            failures.append((relative, "--fixture exited 0: this check cannot fail"))
        elif code == 2:
            failures.append((relative, "--fixture examined nothing"))
        elif code == 3:
            failures.append((relative, "--fixture ran and did not match its own expectations"))
        elif code != 1:
            failures.append((relative, "--fixture exited %d, expected 1" % code))
        else:
            print("ok    %-28s --fixture failed on purpose" % relative)

    print("\n%-22s examined=%d problems=%d" % ("contract", len(checks), len(failures)))
    for relative, detail in failures:
        print("   %-28s %s" % (relative, detail))

    if not checks:
        print("found no checks to examine: that is a fault, not a clean repository")
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
