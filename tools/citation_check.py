#!/usr/bin/env python3
"""Check that every quotation in this repository exists in the source
document, on the page it claims.

The cards in this repository make their case by quoting a published PDF.
A quotation that drifts by one word, or that names the wrong page, costs
more than a missing quotation: it invites the reader to check, and then
rewards them for doubting everything else.

The source document is not redistributed here. Extract it yourself and
pass the text:

    pdftotext -layout owasp-agentic-2026.pdf owasp.txt
    tools/citation_check.py owasp.txt

What gets checked: any double-quoted run of 10+ characters that is
followed by a `(p.N)` marker. Quoted text without a page marker is
counted and reported as unchecked rather than silently ignored -- a
parser that hides what it skipped is worse than no parser.

Whitespace is flattened on both sides before comparing. PDF extraction
breaks sentences across lines, and a naive search reports genuine
quotations as missing. That happened here, twice, before this tool
existed.

Exit codes
    0   every quotation found, on the page it claims
    1   at least one quotation missing or on the wrong page
    2   nothing examined, or the source text is unusable
"""

import argparse
import os
import re
import sys
import tempfile

QUOTE_WITH_PAGE = re.compile(r'"([^"\n]{10,})"\s*\(p\.(\d+)\)')
QUOTE_ANY = re.compile(r'"([^"\n]{10,})"')
PAGE_FOOTER = re.compile(r"Page (\d+)")


def flatten(text):
    return re.sub(r"\s+", " ", text)


def flatten_with_offsets(raw):
    """Flatten whitespace while keeping, for each flattened character, the
    index it came from in the original text.

    A proportional estimate of that index looks reasonable and lands two
    or three pages off, which turns correct citations into reported
    errors. The map costs one pass and is exact.
    """
    chars, offsets = [], []
    previous_was_space = False
    for index, char in enumerate(raw):
        if char.isspace():
            if not previous_was_space:
                chars.append(" ")
                offsets.append(index)
            previous_was_space = True
        else:
            chars.append(char)
            offsets.append(index)
            previous_was_space = False
    return "".join(chars), offsets


def page_index(raw):
    """Return [(position, page_number)] from the PDF footers, in order."""
    return [(m.start(), int(m.group(1))) for m in PAGE_FOOTER.finditer(raw)]


def page_of(offsets, flat, pages, needle):
    """The page a quotation sits on, from the footer that follows it."""
    position = flat.find(flatten(needle))
    if position < 0 or not pages or position >= len(offsets):
        return None
    exact = offsets[position]
    for offset, number in pages:
        if offset >= exact:
            return number
    return pages[-1][1]


def collect_documents(paths):
    documents = []
    for path in paths:
        if os.path.isfile(path):
            documents.append(path)
            continue
        for root, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for name in sorted(filenames):
                if name.endswith(".md"):
                    documents.append(os.path.join(root, name))
    return documents


def run_check(documents, source_text, label):
    raw = source_text
    flat, offsets = flatten_with_offsets(raw)
    pages = page_index(raw)

    examined = 0
    unchecked = 0
    problems = []

    for path in documents:
        with open(path, encoding="utf-8") as handle:
            body = handle.read()

        with_page = QUOTE_WITH_PAGE.findall(body)
        all_quotes = QUOTE_ANY.findall(body)
        unchecked += max(0, len(all_quotes) - len(with_page))

        for quotation, claimed in with_page:
            examined += 1
            if flatten(quotation) not in flat:
                problems.append((path, quotation, "not found in the source document"))
                continue
            actual = page_of(offsets, flat, pages, quotation)
            if actual is not None and abs(actual - int(claimed)) > 1:
                problems.append((path, quotation,
                                 "claims p.%s, found around p.%s" % (claimed, actual)))

    print("%-22s examined=%d problems=%d unchecked=%d"
          % (label, examined, len(problems), unchecked))
    for path, quotation, detail in problems:
        print("   %s\n      %r\n      %s" % (path, quotation[:70], detail))
    if unchecked:
        print("   (%d quoted passages carry no (p.N) marker and were not verified)" % unchecked)
    return examined, problems


FIXTURE_SOURCE = """ASI02: Tool Misuse and Exploitation
Description
Agents call tools on behalf of users.

    5. Loop amplification: Planner repeatedly calls costly APIs, causing
       DoS or bill spikes.

genai.owasp.org                                            Page 12
ASI03: Identity and Privilege Abuse
Broken identity boundaries make enforcing true least privilege
impossible across the agent fleet.

genai.owasp.org                                            Page 15
"""

# One correct quotation, one that PDF extraction split across two lines
# (the trap this tool was written for), one absent, one on the wrong page.
FIXTURE_DOC = '''# Fixture card

Quoting correctly: "Loop amplification: Planner repeatedly calls costly APIs" (p.12).

Split across lines by the extractor, and genuine: "causing DoS or bill spikes" (p.12).

Split across lines and genuine: "make enforcing true least privilege impossible" (p.15).

Invented, and it must be caught: "agents must never touch production" (p.12).

Right words, wrong page: "Loop amplification: Planner repeatedly calls costly" (p.30).

Quoted without a page marker, so it stays unchecked: "some other phrase entirely".
'''

EXPECTED_PROBLEMS = 2
EXPECTED_EXAMINED = 5
EXPECTED_UNCHECKED = 1


def run_fixture():
    with tempfile.TemporaryDirectory() as tmp:
        doc = os.path.join(tmp, "card.md")
        with open(doc, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_DOC)
        examined, problems = run_check([doc], FIXTURE_SOURCE, "fixture")

    print("\n--- fixture verdict ---")
    conforms = True
    checks = [
        ("quotations examined", examined, EXPECTED_EXAMINED),
        ("problems found", len(problems), EXPECTED_PROBLEMS),
    ]
    for name, got, expected in checks:
        if got == expected:
            print("ok    %-24s expected=%d got=%d" % (name, expected, got))
        else:
            print("FAIL  %-24s expected=%d got=%d" % (name, expected, got))
            conforms = False

    kinds = [detail for _, _, detail in problems]
    if any("not found" in k for k in kinds):
        print("ok    the invented quotation was caught")
    else:
        print("FAIL  the invented quotation slipped through")
        conforms = False
    if any("claims p." in k for k in kinds):
        print("ok    the wrong page was caught")
    else:
        print("FAIL  the wrong page slipped through")
        conforms = False
    if len(problems) == EXPECTED_PROBLEMS:
        print("ok    both line-split quotations were accepted as genuine")

    if not conforms:
        print("\nfixture did not behave as declared: the checker cannot be trusted")
        return 3
    print("\nevery planted error was caught and the genuine quotations survived;")
    print("exiting 1 on purpose, because a check that cannot fail is not a check")
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", nargs="?", help="extracted text of the source PDF")
    parser.add_argument("paths", nargs="*", help="documents to check (default: the repository)")
    parser.add_argument("--fixture", action="store_true", help="prove the checker can fail")
    args = parser.parse_args()

    if args.fixture:
        return run_fixture()
    if not args.source:
        parser.error("give the extracted source text, or --fixture")

    try:
        with open(args.source, encoding="utf-8") as handle:
            source_text = handle.read()
    except (OSError, UnicodeDecodeError) as error:
        print("unusable source text: %s" % error)
        return 2
    if len(flatten(source_text)) < 500:
        print("source text is too short to be the document: %d characters" % len(source_text))
        return 2

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    documents = collect_documents(args.paths or [repo])
    examined, problems = run_check(documents, source_text, "citation-check")
    if examined == 0:
        print("examined zero quotations: that is a fault, not a clean repository")
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
