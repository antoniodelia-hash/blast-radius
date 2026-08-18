#!/usr/bin/env python3
"""Scan files for identifying strings before they reach a public repository.

Generic secret scanners look for credentials. This one also looks for the
things that identify a *client*: company names, site names, suppliers,
towns, plate numbers. Those are not secrets in the cryptographic sense and
no off-the-shelf scanner knows them, so they travel into public repos
unnoticed.

The list of real strings lives outside the repository. This file ships the
mechanism; `tools/denylist.example.txt` ships the shape.

Exit codes
    0   examined at least one file, found nothing
    1   found at least one hit
    2   examined zero files -- treated as a fault, never as a pass
    3   --fixture ran and the results did not match what was expected

Usage
    secret_scan.py [--denylist PATH] [PATH ...]
    secret_scan.py --staged            # what git is about to commit
    secret_scan.py --fixture           # prove the scanner can fail
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".sh", ".yml", ".yaml", ".json", ".toml",
    ".cfg", ".ini", ".html", ".css", ".js", ".ts", "",
}


def load_denylist(path):
    """Return (literals, words, regexes). Raises if the file yields nothing."""
    literals, words, regexes = [], [], []
    with open(path, encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError("%s:%d: entry without a kind prefix: %r" % (path, lineno, line))
            kind, value = line.split(":", 1)
            kind = kind.strip().lower()
            if kind == "literal":
                literals.append(value.lower())
            elif kind == "word":
                words.append((value, re.compile(r"\b%s\b" % re.escape(value), re.IGNORECASE)))
            elif kind == "regex":
                regexes.append((value, re.compile(value)))
            else:
                raise ValueError("%s:%d: unknown kind %r" % (path, lineno, kind))
    if not (literals or words or regexes):
        raise ValueError("%s holds no usable entries: an empty denylist passes everything" % path)
    return literals, words, regexes


ALLOW_MARKER = "scan:allow"


def scan_text(text, literals, words, regexes):
    """Return (hits, allowed): lists of (lineno, rule, matched_text).

    A line carrying the allow marker still gets scanned; its matches move to
    the second list instead of disappearing. Counting them out loud is the
    point -- an exception nobody sees again is how a denylist rots.
    """
    hits, allowed = [], []
    for lineno, line in enumerate(text.splitlines(), 1):
        lowered = line.lower()
        bucket = allowed if ALLOW_MARKER in lowered else hits
        for literal in literals:
            if literal in lowered:
                bucket.append((lineno, "literal:%s" % literal, literal))
        for value, pattern in words:
            found = pattern.search(line)
            if found:
                bucket.append((lineno, "word:%s" % value, found.group(0)))
        for value, pattern in regexes:
            found = pattern.search(line)
            if found:
                bucket.append((lineno, "regex:%s" % value, found.group(0)))
    return hits, allowed


def collect_files(paths):
    """Walk paths into a file list. Hidden directories are included on purpose."""
    files = []
    for path in paths:
        if os.path.isfile(path):
            files.append(path)
            continue
        for root, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".venv")]
            for name in sorted(filenames):
                files.append(os.path.join(root, name))
    keep = []
    for path in files:
        suffix = os.path.splitext(path)[1].lower()
        if suffix in TEXT_SUFFIXES:
            keep.append(path)
    return keep


def staged_files():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [p for p in out.splitlines() if p and os.path.isfile(p)]


def run_scan(files, denylist_path, label):
    literals, words, regexes = load_denylist(denylist_path)
    rules = len(literals) + len(words) + len(regexes)
    problems = []
    allowed_total = 0
    examined = 0
    for path in files:
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except (UnicodeDecodeError, OSError):
            continue
        examined += 1
        hits, allowed = scan_text(text, literals, words, regexes)
        allowed_total += len(allowed)
        for lineno, rule, matched in hits:
            problems.append((path, lineno, rule, matched))

    print("%-22s examined=%d rules=%d problems=%d allowed=%d"
          % (label, examined, rules, len(problems), allowed_total))
    for path, lineno, rule, matched in problems:
        print("   %s:%d  %s  ->  %r" % (path, lineno, rule, matched))
    return examined, problems


FIXTURE_DENYLIST = """
literal:acme-industries
literal:acmeindustries.example
word:AIN
regex:\\b(?!10\\.|127\\.|192\\.168\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.)(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b
regex:(?i)chat[_-]?id\\D{0,10}-?[0-9]{6,}
regex:\\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\\b
regex:\\b[a-z][a-z0-9+.-]*://[^/\\s:@]+:[^/\\s@]{3,}@
"""

# Each entry: (relative path, file body, how many hits that file must produce).
# The legitimate lines are the point of the exercise: a scanner that flags
# everything is as useless as one that flags nothing, and only a fixture
# carrying both can tell the two apart.
FIXTURE_FILES = [
    (
        "notes.md",
        "The client is Acme-Industries and it shows.\n"
        "Reach the box at 203.0.113.5 over ssh.\n"  # scan:allow -- bait, not a real address
        # A password inside a connection URL. Neither this scanner nor
        # gitleaks caught this shape until it was planted here on purpose.
        "DSN = postgres://admin:hunter2@db.internal:5432/prod\n",  # scan:allow -- bait
        3,
    ),
    (
        # Hidden directory. The scanner that shipped this repo's first draft
        # dropped every path starting with "." and reported a clean tree
        # while examining nothing at all. This file is here so that failure
        # can never come back unnoticed.
        ".hidden/config.yml",
        "chat_id: 987654321\n"  # scan:allow -- bait
        "token: ghp_abcdefghijklmnopqrstuvwxyz01\n",  # scan:allow -- bait
        2,
    ),
    (
        # Accented filename and blank lines: the shape of the real tree.
        "relazione-attività.txt",
        "\n\nSupplier AIN delivered late.\n\n",
        1,
    ),
    (
        # Nothing here may fire. "chain" contains "ain", "similar" contains
        # "imi", 127.0.0.1 and 10.0.0.4 are non-routable, and "risk" talk is  scan:allow
        # ordinary English.
        "legit.md",
        "The supply chain is the weak point, and similar systems fail alike.\n"
        "Bind the service to 127.0.0.1 and let 10.0.0.4 reach it.\n"
        "Containment beats detection; the main idea is plain.\n",
        0,
    ),
]


def run_fixture():
    """Seed the known traps, then check the scanner reacted exactly as expected."""
    expected_total = sum(count for _, _, count in FIXTURE_FILES)
    with tempfile.TemporaryDirectory() as tmp:
        denylist_path = os.path.join(tmp, "denylist.txt")
        with open(denylist_path, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_DENYLIST)

        tree = os.path.join(tmp, "tree")
        per_file_expected = {}
        for relative, body, count in FIXTURE_FILES:
            full = os.path.join(tree, relative)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write(body)
            per_file_expected[os.path.abspath(full)] = count

        files = collect_files([tree])
        examined, problems = run_scan(files, denylist_path, "fixture")

        print("\n--- fixture verdict ---")
        conforms = True

        if examined != len(FIXTURE_FILES):
            print("FAIL  examined %d files, the fixture holds %d" % (examined, len(FIXTURE_FILES)))
            conforms = False
        else:
            print("ok    every seeded file was examined, hidden and accented ones included (%d)" % examined)

        found_per_file = {}
        for path, _, _, _ in problems:
            found_per_file[os.path.abspath(path)] = found_per_file.get(os.path.abspath(path), 0) + 1

        for full, expected in sorted(per_file_expected.items()):
            got = found_per_file.get(full, 0)
            name = os.path.relpath(full, tree)
            if got == expected:
                verdict = "ok   "
            else:
                verdict = "FAIL "
                conforms = False
            note = "  <- must stay silent" if expected == 0 else ""
            print("%s %-28s expected=%d got=%d%s" % (verdict, name, expected, got, note))

        if len(problems) != expected_total:
            conforms = False

        if not conforms:
            print("\nfixture did not behave as declared: the scanner cannot be trusted")
            return 3
        print("\nthe scanner found every planted string and left the legitimate lines alone;")
        print("exiting 1 on purpose, because a check that cannot fail is not a check")
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", default=None)
    parser.add_argument("--denylist", default=None)
    parser.add_argument("--staged", action="store_true", help="scan what git is about to commit")
    parser.add_argument("--fixture", action="store_true", help="prove the scanner can fail")
    args = parser.parse_args()

    if args.fixture:
        return run_fixture()

    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    denylist_path = args.denylist or os.path.join(os.path.dirname(repo_root), "denylist.local.txt")
    if not os.path.exists(denylist_path):
        print("no denylist at %s" % denylist_path)
        print("copy tools/denylist.example.txt somewhere outside the repository and fill it in")
        return 2

    if args.staged:
        files = collect_files(staged_files())
    else:
        files = collect_files(args.paths or [repo_root])

    try:
        examined, problems = run_scan(files, denylist_path, "secret-scan")
    except ValueError as error:
        print("unusable denylist: %s" % error)
        return 2
    if examined == 0:
        print("examined zero files: that is a fault, not a clean tree")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
