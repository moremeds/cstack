# Skills-first README redesign

## Goal

Rewrite the public README around the four skills that now define cstack:
`whatup`, `execute-plan`, `review-cycle`, and `tribunal-review`.

The README should sound like it was written by someone who has used coding
agents long enough to know where they fail. It should be direct and human,
without turning into marketing copy or an internal implementation note.

## Audience

The primary reader already uses Claude Code or Codex and wants a more reliable
way to carry work from an approved plan to a verified result. A reader who is
new to agent workflows should still understand the problem and the four-skill
chain.

## Structure

1. Open with one memorable promise and the failure mode cstack addresses.
2. Name four recognizable moments when agent work goes off track.
3. Map each moment to one skill.
4. Put the fastest supported installation path near the top.
5. Show how the four skills fit into one workflow.
6. Explain each skill in plain language, with its invocation and output.
7. Keep the strongest trust evidence: grounding, independent model review,
   verification gates, and the measured lesson behind the workflow.
8. Move rules, hooks, commands, and tests into a compact supporting section.
9. End with checkout installation details and the license.

## Voice

- Use concrete situations instead of abstract claims.
- Write in the first person only when a real observation supports it.
- Prefer short paragraphs and plain verbs.
- Keep technical detail where it earns trust; remove it where it interrupts the
  reader's understanding of the skills.
- Do not claim that cstack prevents every agent failure. Say what it verifies
  and what remains outside its proof.

## Non-goals

- Changing any skill, hook, rule, command, manifest, or installation behavior.
- Adding branding assets, demos, or new dependencies.
- Turning the README into complete reference documentation for every internal
  mechanism.

## Acceptance

- The opening, first screenful, and main navigation are centered on the four
  skills rather than repository scaffolding.
- A reader can identify which skill to use and install the plugin without
  reading the entire README.
- All commands and factual claims match the current repository files.
- The prose feels personal and experienced without becoming chatty or
  promotional.
- Existing repository tests pass, including the public-content guard.
