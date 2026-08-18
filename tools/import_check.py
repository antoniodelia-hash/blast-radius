#!/usr/bin/env python3
"""Check that every control imports nothing but the standard library.

The promise this repository makes about its controls is that you can copy
one file and run it. A single third-party import breaks that promise
quietly, on someone else's machine, weeks later.

Needs Python 3.10 or newer, where the standard-library module inventory is
available. On older versions there is nothing to compare against, and this
says so and exits 2 rather than inspecting every file and approving them
all.

Exit codes
    0   every file imports only the standard library
    1   at least one third-party import
    2   nothing examined, or this Python cannot answer the question
    3   --fixture did not behave as declared
"""

import argparse
import ast
import os
import sys
import tempfile

FOLDERS = ("controls", "tools")


def stdlib_names():
    return getattr(sys, "stdlib_module_names", None)


def imported_modules(source):
    modules = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules += [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module.split(".")[0])
    return modules


def inspect(root, folders, allowed):
    examined, problems = 0, []
    for folder in folders:
        full = os.path.join(root, folder)
        if not os.path.isdir(full):
            continue
        for base, dirs, files in os.walk(full):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(base, name)
                examined += 1
                with open(path, encoding="utf-8") as handle:
                    for module in imported_modules(handle.read()):
                        if module not in allowed:
                            problems.append((os.path.relpath(path, root), module))
    return examined, problems


def report(examined, problems, label):
    print("%-22s examined=%d problems=%d" % (label, examined, len(problems)))
    for path, module in problems:
        print("   %-34s imports %s" % (path, module))


def run_fixture():
    # The fixture exercises the logic, which does not depend on the running
    # version, so it passes its own inventory instead of asking this Python
    # for one. Otherwise the self-test would inherit the 3.9 limitation and
    # look mute on exactly the versions where the real check declines to run.
    allowed = {"json", "os", "re", "sys", "ast"}
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "controls"))
        clean = os.path.join(tmp, "controls", "clean.py")
        with open(clean, "w", encoding="utf-8") as handle:
            handle.write("import json\nimport os.path\nfrom re import compile\n")
        dirty = os.path.join(tmp, "controls", "dirty.py")
        with open(dirty, "w", encoding="utf-8") as handle:
            handle.write("import json\nimport requests\nfrom pandas import DataFrame\n")
        examined, problems = inspect(tmp, ("controls",), allowed)
        report(examined, problems, "fixture")

    modules = sorted(module for _, module in problems)
    print("\n--- fixture verdict ---")
    conforms = True
    if examined != 2:
        print("FAIL  examined %d files, the fixture holds 2" % examined)
        conforms = False
    else:
        print("ok    both seeded files were examined")
    if modules == ["pandas", "requests"]:
        print("ok    caught both third-party imports, and left the stdlib ones alone")
    else:
        print("FAIL  expected ['pandas', 'requests'], got %s" % modules)
        conforms = False
    if not conforms:
        print("\nfixture did not behave as declared: the check cannot be trusted")
        return 3
    print("\nexiting 1 on purpose, because a check that cannot fail is not a check")
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    if args.fixture:
        return run_fixture()

    allowed = stdlib_names()
    if allowed is None:
        print("this Python (%d.%d) has no standard-library inventory: nothing to"
              % sys.version_info[:2])
        print("compare against. Run this check on 3.10 or newer.")
        return 2

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    examined, problems = inspect(root, FOLDERS, allowed)
    report(examined, problems, "import-check")
    if examined == 0:
        print("examined zero files: that is a fault, not a clean tree")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
