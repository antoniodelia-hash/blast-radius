# Third-party material

This directory holds material that is **not** covered by the repository's
Apache 2.0 licence. It is here so that a check can run without depending on
a file the reader has to fetch by hand.

## owasp-agentic-top10-2026.txt

Plain-text extraction of the **OWASP Top 10 for Agentic Applications 2026**,
published by the **OWASP GenAI Security Project** and available at
<https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/>.

Extracted from the published PDF with `pdftotext -layout`. The text is
unmodified apart from that conversion, and the page footers the PDF carries
are what `tools/citation_check.py` uses to resolve page numbers.

**Licence: Creative Commons Attribution-ShareAlike 4.0 International
(CC BY-SA 4.0)** — <https://creativecommons.org/licenses/by-sa/4.0/legalcode>

The licence permits sharing and adaptation, including commercially, with
attribution and under the same licence for derivative works. This file is
redistributed under those terms. It is a copy, not a derivative: nothing in
this repository remixes or transforms the document itself, and the cards
quote from it under the same attribution.

The rest of this repository — the principles, the controls, the tests — is
original work under Apache 2.0. The two licences apply to different files
and neither one changes the other.

## Why the file is here at all

`tools/citation_check.py` verifies that every quotation in this repository
exists in the source and sits on the page it claims. Without the source
text present, that check is skipped, and a check that only runs when
somebody remembers to point it at a file is a check that stops running.

To refresh it after a new revision of the document is published:

    curl -sL -o owasp.pdf "<the download URL from the page above>"
    pdftotext -layout owasp.pdf third_party/owasp-agentic-top10-2026.txt
    python3 tools/citation_check.py third_party/owasp-agentic-top10-2026.txt

If page numbers moved, that last command says so, one citation at a time.
