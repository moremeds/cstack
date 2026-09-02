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

TEMPLATES = {n: pathlib.Path(__file__).with_name(f"{n}.md")
             for n in ("review", "debate", "rebuttal")}
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
    """Remove a whole `=== X ===` block, header included. No-op if absent.

    rebuttal.md has no FOCUS block, so an unguarded index() raises there.
    """
    if header not in text:
        return text
    start = text.index(header)
    end = text.index("\n=== ", start + 1) + 1
    return text[:start] + text[end:]


def value(literal, path):
    return pathlib.Path(path).read_text() if path else literal


def read(path):
    """One map serves three templates, so a key the template lacks must
    substitute empty rather than leave a literal brace in the prompt."""
    return pathlib.Path(path).read_text() if path else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="cls", required=True, choices=sorted(MARKER))
    ap.add_argument("--template", default="review", choices=sorted(TEMPLATES))
    # review-only; debate and rebuttal carry no such placeholders
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--specialty", default="")
    ap.add_argument("--content", help="file holding the diff/plan/prose payload")
    ap.add_argument("--contested", help="debate: the contested findings")
    ap.add_argument("--challenges", help="rebuttal: challenges against your positions")
    ap.add_argument("--code-context", dest="code_context")
    ap.add_argument("--mode", default="branch diff")
    ap.add_argument("--focus", default="")
    ap.add_argument("--context", default="(none given)")
    ap.add_argument("--context-file")
    ap.add_argument("--standards", default="(none given)")
    ap.add_argument("--standards-file")
    a = ap.parse_args()
    # --content is optional only because debate and rebuttal have no such
    # placeholder; a review without a target is still a bug, not an empty prompt.
    if a.template == "review" and not a.content:
        ap.error("--content is required for the review template")

    text = TEMPLATES[a.template].read_text()
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
        "{review_content}": read(a.content),
        "{contested_items}": read(a.contested),
        "{challenges}": read(a.challenges),
        "{code_context}": read(a.code_context),
    }.items():
        text = text.replace(key, val)
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
