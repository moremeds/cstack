=== CONTEXT ===
Reviewers on a code-review tribunal disagreed. The items below are CONTESTED —
they were raised by some reviewers and not others. Your job is to ATTACK them.

Weights: Codex 1.0 (trusted) · Claude 1.0 (trusted) · Gemini 0.5 (advisory).

An issue that survives this round becomes a real finding the user will act on.
An issue that does not survive is dropped. Both errors are expensive, so attack
honestly: if the position is right, say VALID and say why.

=== FOCUS ===
{focus_text}

(Omit this block when the user gave no focus.)

=== CODE UNDER DISPUTE ===
{code_context}

=== CONTESTED ITEMS ===
{contested_items}

Each item is given as:
  ISSUE-N: [description]
    Category / Original confidence
    Position A (raised by [model]): [their argument and evidence]
    Position B (raised by [model]): [their counter-argument, or "silence"]

=== YOUR TASK ===
For each contested item, attack the position you find weakest:

ISSUE-N:
  COUNTER-EVIDENCE: <specific code, control flow, or precedent in this repo that
    weakens the position — quote it. "I disagree" is not counter-evidence.>
  ATTACK-VECTOR: <the concrete scenario in which that position is wrong.
    Code targets: give inputs and state, not a category.
    Plan targets: give the implementation moment where the step breaks — what
    the implementer hits at that point that the plan did not account for.>
  VERDICT: VALID | INVALID | PARTIALLY_VALID
  REASONING: <one or two sentences. If PARTIALLY_VALID, say precisely which part
    survives and which part does not.>

For Category: over-engineering items the burden of proof is INVERTED: the code
must justify its existence. Defending the structure requires naming a concrete
CURRENT caller or requirement that needs it — "we might need it later",
"it's more flexible", or "it's best practice" count as conceding the deletion.
Attacking a deletion requires the same: name what breaks today if it goes.

Do not hedge every item to PARTIALLY_VALID. That is a non-answer and it will be
scored as one.
