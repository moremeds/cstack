#!/usr/bin/env python3
"""Build one panelist's prompt from review.md without routing it through the model.

The orchestrator used to read review.md and re-emit ~6KB of it as a heredoc per
run — text that then sits in context and is re-read as cache on every later API
call. This does the same substitution in the shell, so the template's bytes
never enter the conversation.
"""
import argparse
import pathlib
import sys

TEMPLATE = pathlib.Path(__file__).with_name("review.md")
# class -> the parenthesised marker that opens its blocks in review.md
MARKER = {"code": "(code targets", "plan": "(plan/spec targets", "prose": "(prose targets"}


def select(text, cls):
    """Keep only the HOW TO REVIEW and SEVERITY blocks for `cls`."""
    want = MARKER[cls]
    out, drop = [], False
    for line in text.splitlines(True):
        if line.startswith("=== HOW TO REVIEW (") or line.startswith("SEVERITY ("):
            drop = want not in line
        elif drop and (line.startswith("=== ") or line.startswith("SEVERITY (")):
            drop = False
        if not drop:
            out.append(line)
    return "".join(out)


def drop_block(text, header):
    """Remove a whole `=== X ===` block, header included."""
    start = text.index(header)
    end = text.index("\n=== ", start + 1) + 1
    return text[:start] + text[end:]


def value(literal, path):
    return pathlib.Path(path).read_text() if path else literal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="cls", required=True, choices=sorted(MARKER))
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--specialty", required=True)
    ap.add_argument("--content", required=True, help="file holding the diff/plan/prose payload")
    ap.add_argument("--mode", default="branch diff")
    ap.add_argument("--focus", default="")
    ap.add_argument("--context", default="(none given)")
    ap.add_argument("--context-file")
    ap.add_argument("--standards", default="(none given)")
    ap.add_argument("--standards-file")
    a = ap.parse_args()

    text = TEMPLATE.read_text()
    # the leading HTML comment instructs the orchestrator; the panelist never needs it
    if text.startswith("<!--"):
        text = text[text.index("-->") + 3:].lstrip("\n")
    text = select(text, a.cls)
    if not a.focus.strip():
        # Step 1 rule 5: no focus given -> omit the block, never send an empty one
        text = drop_block(text, "=== FOCUS ===")
    for key, val in {
        "{reviewer_name}": a.reviewer,
        "{specialty}": a.specialty,
        "{focus_text}": a.focus,
        "{review_mode}": a.mode,
        "{project_context}": value(a.context, a.context_file),
        "{coding_standards}": value(a.standards, a.standards_file),
        "{review_content}": pathlib.Path(a.content).read_text(),
    }.items():
        text = text.replace(key, val)
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
