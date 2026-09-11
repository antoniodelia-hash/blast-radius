#!/bin/sh
# Every check in this repository, in one place, so that "it passes locally"
# and "it passes in CI" run the same commands. A CI script that drifts from
# what a human runs is two checks, one of which is never exercised.
#
# Usage:
#   tools/run_all_checks.sh                  # everything runnable without the source PDF
#   tools/run_all_checks.sh path/to/owasp.txt  # also verify every quotation
set -e
root=$(cd "$(dirname "$0")/.." && pwd)
# The source document now travels with the repository, under its own licence
# in third_party/. A check that only runs when somebody remembers to point it
# at a file is a check that stops running.
source_text="${1:-$root/third_party/owasp-agentic-top10-2026.txt}"
failed=0

run() {
    name="$1"; shift
    printf '\n=== %s\n' "$name"
    if "$@"; then
        :
    else
        status=$?
        echo "FAILED ($name, exit $status)"
        failed=1
    fi
}

# Every check must be able to fail. This one finds new checks by itself, so
# a control added without a fixture is caught without editing this file.
run "every check can fail" python3 "$root/controls/tests/test_contract.py"

# The counters at the top of MAPPING.md must describe the table below it.
run "mapping counters" python3 "$root/tools/mapping_check.py"

# The validation that reads an observation is copied into every control
# rather than imported, so that a control stays one file. This is what the
# copy costs: the copies are compared byte for byte.
run "copied blocks agree" python3 "$root/tools/copy_check.py"

# Standard-library-only. Exit 2 here means this Python cannot answer the
# question (the module inventory arrived in 3.10), which is reported as
# skipped rather than passed: the two must never look alike.
printf '\n=== standard library only\n'
# The status of this check only. Reusing a variable another check had left
# behind reported a passing check as failed.
import_status=0
python3 "$root/tools/import_check.py" || import_status=$?
if [ "$import_status" = "2" ]; then
    echo "skipped: run this on Python 3.10 or newer, or let CI do it"
elif [ "$import_status" != "0" ]; then
    echo "FAILED (standard library only, exit $import_status)"
    failed=1
fi

# Test the file, not the variable. source_text is given a default above, so
# -n was true in every run and the skip branch below was unreachable: in a
# checkout without third_party/ the citation check exited 2 and the suite
# went red over an optional input. echo "\n" is implementation-defined under
# /bin/sh too, and prints a literal backslash-n on dash.
if [ -f "$source_text" ]; then
    run "quotations against the source" \
        python3 "$root/tools/citation_check.py" "$source_text"
else
    printf '\n=== %s\n' "quotations against the source"
    echo "skipped: no source text at $source_text"
    echo "the document travels with the repository; to refresh it from a new"
    echo "revision of the PDF:"
    echo "  pdftotext -layout owasp.pdf third_party/owasp-agentic-top10-2026.txt"
    echo "  tools/run_all_checks.sh"
fi

exit $failed
