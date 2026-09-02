# Tribunal direct transport — implementation plan

> **For Codex and Claude:** REQUIRED SUB-SKILL: Use `execute-plan`.

**Goal:** Route the tribunal's debate and rebuttal rounds through the model
APIs directly, leaving the review round on the CLI, so two of every three panel
calls drop their ~18k-token CLI floor without losing repo access where it matters.

**Spec:** `docs/plans/2026-09-02-tribunal-direct-transport-design.md`

## Global constraints

- cstack is a **public** repo. `tests/test_no_private_content.py` rejects any
  tracked file containing an absolute `/Users/<name>` path, a bare IP, an email
  address, or an SSH remote. Use `$HOME`, never a literal home path.
- No credential value appears in any tracked file. Tokens are read at runtime.
- Tests are stdlib `unittest`, matching `tests/test_review_chain.py`.
- The suite must never make a network call. Live transport was verified by hand
  during design; CI has no credentials.
- Step 3 (review) is **not** modified by this plan. Its `-C "$REPO_OR_WORKTREE"`
  is the anti-hallucination mechanism the design exists to protect.

## File structure

- Create `skills/tribunal-review/panel/direct.sh` — the whole transport: a
  preflight check, one function per seat, one SSE/JSON extractor per seat, CLI
  fallback inside each. One file because the two functions share nothing but a
  fallback shape, and an abstraction over "provider" would be one implementation
  pretending to be two.
- Create `tests/test_tribunal_transport.py` — contract tests over that file and
  over SKILL.md.
- Modify `skills/tribunal-review/prompts/assemble.py` — the template becomes a
  parameter, so debate and rebuttal prompts get built instead of pasted.
- Modify `skills/tribunal-review/SKILL.md` — Step 5 gains dispatch code.
- Modify `skills/tribunal-review/references/panel-cli-notes.md` — record the
  Node/TLS and stale-credential findings.

---

### Task 1: The Codex seat

**Files:**
- Create: `skills/tribunal-review/panel/direct.sh`
- Test: `tests/test_tribunal_transport.py`

**Produces:** `direct_preflight`, `direct_codex <prompt-file> <out-file>`.

- [ ] **Step 1: Write the failing tests**

```python
"""Contract tests for the tribunal's direct API transport."""

import os
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRECT = ROOT / "skills" / "tribunal-review" / "panel" / "direct.sh"
SKILL = ROOT / "skills" / "tribunal-review" / "SKILL.md"


def run_fn(fn, *args, env=None, path_prefix=None):
    """Source direct.sh and call one function, with a stubbed PATH if given."""
    e = dict(os.environ)
    if env is not None:
        e.update(env)
    if path_prefix:
        e["PATH"] = f"{path_prefix}:{e['PATH']}"
    quoted = " ".join(f"'{a}'" for a in args)
    return subprocess.run(
        ["bash", "-c", f". '{DIRECT}'; {fn} {quoted}"],
        capture_output=True, text=True, env=e,
    )


class TestNoSecretsInSource(unittest.TestCase):
    """A public repo cannot carry a credential or a personal path."""

    def test_no_literal_credentials_or_home_paths(self):
        src = DIRECT.read_text()
        self.assertNotRegex(src, r"sk-[A-Za-z0-9_-]{10}")
        self.assertNotRegex(src, r"/Users/[a-z]")
        # the account id is derived from the JWT, never pasted
        self.assertIn("chatgpt_account_id", src)


class TestPreflight(unittest.TestCase):
    """A missing credential must die before the panel launches, not mid-round."""

    def test_unset_token_fails_and_names_the_variable(self):
        r = run_fn("direct_preflight", env={"CLAUDE_CODE_OAUTH_TOKEN": ""})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", r.stderr)


class TestCodexSeat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tribunal-")
        self.bin = pathlib.Path(self.tmp) / "bin"
        self.bin.mkdir()

    def _stub(self, name, body):
        p = self.bin / name
        p.write_text("#!/usr/bin/env bash\n" + body)
        p.chmod(0o755)

    def test_sse_deltas_are_concatenated_into_the_output_file(self):
        """The reply is assembled from response.output_text.delta events."""
        sse = (
            'data: {"type":"response.created"}\n'
            'data: {"type":"response.output_text.delta","delta":"ISSUE-1 "}\n'
            'data: {"type":"response.output_text.delta","delta":"real bug"}\n'
            'data: {"type":"response.completed"}\n'
        )
        self._stub("curl", f"""
for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done
cat > "$out" <<'SSE'
{sse}
SSE
printf 200
""")
        prompt = pathlib.Path(self.tmp) / "p.md"
        prompt.write_text("review this")
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", str(prompt), str(out), path_prefix=str(self.bin))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out.read_text(), "ISSUE-1 real bug")

    def test_non_200_falls_back_to_the_cli(self):
        """A dead seat silently changes the consensus arithmetic. It must not."""
        self._stub("curl", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\n: > "$out"\nprintf 429\n')
        self._stub("codex", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\necho "from the cli" > "$out"\n')
        prompt = pathlib.Path(self.tmp) / "p.md"
        prompt.write_text("review this")
        out = pathlib.Path(self.tmp) / "codex.txt"
        r = run_fn("direct_codex", str(prompt), str(out), path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "from the cli")
        self.assertIn("429", r.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m unittest discover -s tests -q`
Expected: FAIL — `direct.sh` does not exist.

- [ ] **Step 3: Write `panel/direct.sh`**

```bash
#!/usr/bin/env bash
# Direct API transport for the tribunal rounds that need no repo access.
#
# Debate and rebuttal reason over findings already collected in Step 4, so they
# do not need a coding agent — only a completion. Spawning one costs ~18k tokens
# of CLI system prompt per call. The review round is NOT routed through here:
# it reads the repository, and that is what keeps its findings honest.

direct_preflight() {
  if [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
    echo "tribunal: CLAUDE_CODE_OAUTH_TOKEN is unset. Export it from ~/.zshenv" >&2
    echo "          (~/.zshrc is read by interactive shells only; a panelist is not one)" >&2
    return 1
  fi
  if [ ! -r "$HOME/.codex/auth.json" ]; then
    echo "tribunal: \$HOME/.codex/auth.json is unreadable; run 'codex login'" >&2
    return 1
  fi
}

_codex_token() {
  python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.codex/auth.json')))['tokens']['access_token'])"
}

_codex_account() {   # _codex_account <jwt>
  python3 - "$1" <<'PY'
import base64, json, sys
payload = sys.argv[1].split(".")[1]
payload += "=" * (-len(payload) % 4)
claims = json.loads(base64.urlsafe_b64decode(payload))
print(claims["https://api.openai.com/auth"]["chatgpt_account_id"])
PY
}

direct_codex() {   # direct_codex <prompt-file> <out-file>
  local prompt="$1" out="$2" tok acct body code
  tok=$(_codex_token) || return 1
  acct=$(_codex_account "$tok") || return 1

  body=$(python3 - "$prompt" <<'PY'
import json, sys
print(json.dumps({
    "model": "gpt-5.6-sol",
    "store": False,
    "stream": True,
    "instructions": "Follow the instructions in the message exactly. Output only the report.",
    "input": [{"type": "message", "role": "user",
               "content": [{"type": "input_text", "text": open(sys.argv[1]).read()}]}],
    "reasoning": {"effort": "high"},
    "tool_choice": "auto",
    "parallel_tool_calls": True,
}))
PY
)
  # --http1.1: h2 measured ~1.2s slower to first byte against this endpoint.
  code=$(curl -sS --http1.1 -o "$out.sse" -w '%{http_code}' \
    https://chatgpt.com/backend-api/codex/responses \
    -H "authorization: Bearer $tok" \
    -H "chatgpt-account-id: $acct" \
    -H "originator: codex_cli_rs" \
    -H "OpenAI-Beta: responses=experimental" \
    -H "accept: text/event-stream" \
    -H "content-type: application/json" \
    -H "session-id: $(uuidgen)" \
    -H "user-agent: codex_cli_rs/0.144.4 (Mac OS 25.5.0; arm64)" \
    -d "$body" 2>>"$out.log") || code=000

  if [ "$code" = "200" ]; then
    python3 - "$out.sse" > "$out" <<'PY'
import json, sys
parts = []
for line in open(sys.argv[1]):
    if not line.startswith("data: "):
        continue
    try:
        ev = json.loads(line[6:])
    except ValueError:
        continue
    if ev.get("type") == "response.output_text.delta":
        parts.append(ev.get("delta", ""))
sys.stdout.write("".join(parts))
PY
  fi

  if [ ! -s "$out" ]; then
    echo "tribunal: codex direct failed (http=$code), falling back to the CLI" >&2
    codex exec -s read-only --skip-git-repo-check -o "$out" - \
      < "$prompt" >>"$out.log" 2>&1 || return 1
  fi
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -q`
Expected: PASS, and `tests/test_no_private_content.py` still green.

- [ ] **Step 5: Commit**

```bash
git add skills/tribunal-review/panel/direct.sh tests/test_tribunal_transport.py
git commit -m "feat(tribunal): direct transport for the Codex seat"
```

---

### Task 2: The Claude seat

**Files:**
- Modify: `skills/tribunal-review/panel/direct.sh`
- Test: `tests/test_tribunal_transport.py`

**Consumes:** `direct_preflight` from Task 1.
**Produces:** `direct_claude <prompt-file> <out-file>`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_tribunal_transport.py`:

```python
class TestClaudeSeat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tribunal-")
        self.bin = pathlib.Path(self.tmp) / "bin"
        self.bin.mkdir()

    def _stub(self, name, body):
        p = self.bin / name
        p.write_text("#!/usr/bin/env bash\n" + body)
        p.chmod(0o755)

    def test_text_blocks_are_joined_into_the_output_file(self):
        self._stub("curl", """
for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done
cat > "$out" <<'JSON'
{"content":[{"type":"text","text":"ISSUE-1 "},{"type":"text","text":"real bug"}]}
JSON
printf 200
""")
        prompt = pathlib.Path(self.tmp) / "p.md"
        prompt.write_text("debate this")
        out = pathlib.Path(self.tmp) / "claude.txt"
        r = run_fn("direct_claude", str(prompt), str(out),
                   env={"CLAUDE_CODE_OAUTH_TOKEN": "stub"}, path_prefix=str(self.bin))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out.read_text(), "ISSUE-1 real bug")

    def test_non_200_falls_back_to_the_cli(self):
        self._stub("curl", 'for a in "$@"; do [ "$prev" = "-o" ] && out=$a; prev=$a; done\n: > "$out"\nprintf 401\n')
        self._stub("claude", 'cat > /dev/null; echo "from the cli"\n')
        prompt = pathlib.Path(self.tmp) / "p.md"
        prompt.write_text("debate this")
        out = pathlib.Path(self.tmp) / "claude.txt"
        r = run_fn("direct_claude", str(prompt), str(out),
                   env={"CLAUDE_CODE_OAUTH_TOKEN": "stub"}, path_prefix=str(self.bin))
        self.assertEqual(out.read_text().strip(), "from the cli")
        self.assertIn("401", r.stderr)

    def test_the_identity_line_is_present(self):
        """The OAuth path rejects a system prompt that omits it."""
        src = DIRECT.read_text()
        self.assertIn("You are Claude Code, Anthropic's official CLI for Claude.", src)

    def test_no_second_credential_source(self):
        """A chain can silently pick the revoked .credentials.json. One source only."""
        src = DIRECT.read_text()
        self.assertNotIn(".credentials.json", src)
        self.assertNotIn("find-generic-password", src)
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m unittest discover -s tests -q`
Expected: FAIL — `direct_claude: command not found`.

- [ ] **Step 3: Append to `panel/direct.sh`**

```bash
direct_claude() {   # direct_claude <prompt-file> <out-file>
  local prompt="$1" out="$2" body code

  body=$(python3 - "$prompt" <<'PY'
import json, sys
print(json.dumps({
    "model": "claude-opus-5",
    "max_tokens": 8192,
    # The OAuth path rejects a system prompt that does not open with this line.
    # It is the 26-token floor, and the reason direct is 700x cheaper than spawn.
    "system": [{"type": "text",
                "text": "You are Claude Code, Anthropic's official CLI for Claude."}],
    "messages": [{"role": "user", "content": open(sys.argv[1]).read()}],
}))
PY
)
  code=$(curl -sS -o "$out.json" -w '%{http_code}' \
    https://api.anthropic.com/v1/messages \
    -H "authorization: Bearer $CLAUDE_CODE_OAUTH_TOKEN" \
    -H "anthropic-beta: oauth-2025-04-20" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$body" 2>>"$out.log") || code=000

  if [ "$code" = "200" ]; then
    python3 - "$out.json" > "$out" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
sys.stdout.write("".join(b.get("text", "") for b in doc.get("content", [])))
PY
  fi

  if [ ! -s "$out" ]; then
    echo "tribunal: claude direct failed (http=$code), falling back to the CLI" >&2
    env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
      claude -p --restricted --strict-mcp-config \
        --disallowedTools "Write,Edit,NotebookEdit" \
        --allowedTools Read,Grep,Glob \
        < "$prompt" > "$out" 2>>"$out.log" || return 1
  fi
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/tribunal-review/panel/direct.sh tests/test_tribunal_transport.py
git commit -m "feat(tribunal): direct transport for the Claude seat"
```

---

### Task 3: Teach the assembler the other two templates

`assemble.py` hardcodes `review.md` and substitutes seven review-only
placeholders. `debate.md` wants `{contested_items}` and `{code_context}`;
`rebuttal.md` wants `{challenges}`. Neither is supported, which is why Step 5
has no dispatch code: there is nothing to build its prompts with, so an
orchestrator falls back to pasting the template — the exact ~10KB context cost
`assemble.py` exists to prevent, reintroduced for rounds two and three.

**Files:**
- Modify: `skills/tribunal-review/prompts/assemble.py`
- Test: `tests/test_tribunal_transport.py`

**Produces:** `assemble.py --template {review,debate,rebuttal}` plus
`--contested`, `--challenges`, `--code-context`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_tribunal_transport.py`:

```python
ASSEMBLE = ROOT / "skills" / "tribunal-review" / "prompts" / "assemble.py"


class TestAssemblerTemplates(unittest.TestCase):
    def _write(self, name, text):
        p = pathlib.Path(tempfile.mkdtemp(prefix="tribunal-")) / name
        p.write_text(text)
        return str(p)

    def test_debate_template_substitutes_its_own_placeholders(self):
        contested = self._write("c.md", "ISSUE-3 disputed")
        ctx = self._write("d.diff", "--- a/x.py")
        r = subprocess.run(
            ["python3", str(ASSEMBLE), "--template", "debate", "--class", "code",
             "--contested", contested, "--code-context", ctx],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ISSUE-3 disputed", r.stdout)
        self.assertIn("--- a/x.py", r.stdout)
        self.assertNotIn("{contested_items}", r.stdout)
        self.assertNotIn("{code_context}", r.stdout)

    def test_rebuttal_template_substitutes_challenges(self):
        ch = self._write("h.md", "you ignored the null case")
        ctx = self._write("d.diff", "--- a/x.py")
        r = subprocess.run(
            ["python3", str(ASSEMBLE), "--template", "rebuttal", "--class", "code",
             "--challenges", ch, "--code-context", ctx],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("you ignored the null case", r.stdout)
        self.assertNotIn("{challenges}", r.stdout)

    def test_review_template_is_still_the_default(self):
        """Task 1-3 must not change what Step 3 already sends."""
        content = self._write("t.diff", "--- a/x.py")
        r = subprocess.run(
            ["python3", str(ASSEMBLE), "--class", "code", "--reviewer", "Codex",
             "--specialty", "BUG DETECTION", "--content", content],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("HOW TO REVIEW (code targets", r.stdout)

    def test_a_template_without_a_focus_block_does_not_crash(self):
        """drop_block() indexes blindly; rebuttal.md has no FOCUS block."""
        ch = self._write("h.md", "x")
        ctx = self._write("d.diff", "y")
        r = subprocess.run(
            ["python3", str(ASSEMBLE), "--template", "rebuttal", "--class", "code",
             "--challenges", ch, "--code-context", ctx, "--focus", ""],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m unittest discover -s tests -q`
Expected: FAIL — `unrecognized arguments: --template`.

- [ ] **Step 3: Make the template a parameter**

In `assemble.py`, replace the module-level constant:

```python
TEMPLATE = pathlib.Path(__file__).with_name("review.md")
```

with a lookup, and guard `drop_block` against a missing header:

```python
TEMPLATES = {n: pathlib.Path(__file__).with_name(f"{n}.md")
             for n in ("review", "debate", "rebuttal")}


def drop_block(text, header):
    """Remove a whole `=== X ===` block, header included. No-op if absent."""
    if header not in text:
        return text
    start = text.index(header)
    end = text.index("\n=== ", start + 1) + 1
    return text[:start] + text[end:]
```

Add the arguments. `--reviewer`, `--specialty` and `--content` become optional,
because debate and rebuttal have no such placeholders:

```python
    ap.add_argument("--template", default="review", choices=sorted(TEMPLATES))
    ap.add_argument("--reviewer", default="")
    ap.add_argument("--specialty", default="")
    ap.add_argument("--content")
    ap.add_argument("--contested")
    ap.add_argument("--challenges")
    ap.add_argument("--code-context", dest="code_context")
```

Read the chosen template, and extend the substitution map. A placeholder whose
file was not supplied substitutes empty, so an unused key cannot leak braces
into a prompt:

```python
    text = TEMPLATES[a.template].read_text()
    ...
    def read(path):
        return pathlib.Path(path).read_text() if path else ""

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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -q`
Expected: PASS, including `tests/test_review_chain.py` — Step 3's existing
invocation must be unchanged.

- [ ] **Step 5: Commit**

```bash
git add skills/tribunal-review/prompts/assemble.py tests/test_tribunal_transport.py
git commit -m "feat(tribunal): let the assembler build debate and rebuttal prompts"
```

---

### Task 4: Wire Step 5 and record the findings

**Files:**
- Modify: `skills/tribunal-review/SKILL.md` (Step 5 only)
- Modify: `skills/tribunal-review/references/panel-cli-notes.md`
- Test: `tests/test_tribunal_transport.py`

**Consumes:** `direct_preflight`, `direct_codex`, `direct_claude`,
`assemble.py --template`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_tribunal_transport.py`:

```python
class TestSkillWiring(unittest.TestCase):
    def _step(self, heading):
        text = SKILL.read_text()
        start = text.index(heading)
        rest = text[start + len(heading):]
        nxt = re.search(r"\n## ", rest)
        return rest[: nxt.start()] if nxt else rest

    def test_step5_dispatches_through_direct_sh(self):
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        self.assertIn("direct.sh", step5)
        self.assertIn("direct_codex", step5)

    def test_step5_does_not_spawn_a_codex_cli(self):
        """The whole point: debate and rebuttal stop paying the CLI floor."""
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        self.assertNotIn("codex exec", step5)

    def test_step5_cursor_resumes_rather_than_starting_over(self):
        """Cursor cannot go direct, so it must at least not re-read the diff."""
        step5 = self._step("## Step 5 — Debate, then rebuttal")
        self.assertIn("--resume \"$CURSOR_CHAT\"", step5)

    def test_review_round_still_gets_the_repository(self):
        """Mutation guard: this is the regression the whole design avoids."""
        step3 = self._step("## Step 3 — Launch the panel in parallel")
        self.assertIn('-C "$REPO_OR_WORKTREE"', step3)
        self.assertIn("codex exec -s read-only", step3)

    def test_preflight_runs_before_the_panel(self):
        text = SKILL.read_text()
        self.assertLess(text.index("direct_preflight"),
                        text.index("## Step 5 — Debate, then rebuttal"))
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python3 -m unittest discover -s tests -q`
Expected: FAIL — `direct.sh` is not referenced in SKILL.md.

- [ ] **Step 3: Add the preflight call to Step 2**

In `## Step 2 — Prepare the workspace`, after the workspace variables are set,
append:

```bash
for D in ~/.agents/skills ~/.claude/skills ~/.codex/skills; do
  [ -f "$D/tribunal-review/panel/direct.sh" ] && . "$D/tribunal-review/panel/direct.sh" && break
done
direct_preflight || exit 1   # a missing credential dies here, not mid-debate
```

- [ ] **Step 4: Replace the Step 5 prose with dispatch code**

Keep the existing A/B/C explanation. After the sentence "Run debate and
rebuttal for all contested items in one batched call each — not one call per
issue.", add:

````markdown
Both rounds reason over findings already merged in Step 4. Neither reads the
repository, so neither pays for a coding-agent CLI. `panel/direct.sh` was
sourced in Step 2.

```bash
python3 "$TR/prompts/assemble.py" --template debate --class "$TARGET_CLASS" \
  --focus "$FOCUS" --contested "$SP/contested.md" --code-context "$SP/target.diff" \
  > "$SP/prompt-debate-codex.md"
direct_codex "$SP/prompt-debate-codex.md" "$SP/debate-codex.txt" &
PANEL_PIDS+=("$!")
# Cursor has no direct path. It resumes the chat Step 3 opened, so it still
# remembers the diff it read; --workspace must repeat or the session forks.
cursor-agent -p --trust --mode ask --model cursor-grok-4.6-high \
    --resume "$CURSOR_CHAT" --workspace "$REPO_OR_WORKTREE" \
    --output-format text \
    < "$SP/prompt-debate-cursor.md" > "$SP/debate-cursor.txt" 2>&1 &
PANEL_PIDS+=("$!")
```

Rebuttal repeats the same shape with `--template rebuttal --challenges`. A seat that fell
back to its CLI says so on stderr; name it in the Step 6 header.
````

- [ ] **Step 5: Record the findings in `panel-cli-notes.md`**

Append:

````markdown
### Why the direct transport uses curl, not Node

`node:https` and `undici` share one TLS stack, and Cloudflare rejects its
fingerprint at `chatgpt.com/backend-api` with a 403. Reordering ciphers to
match curl's does not fix it. Measured 2026-09-02; use `curl`.

### Why only `$CLAUDE_CODE_OAUTH_TOKEN`

`$HOME/.claude/.credentials.json` may still exist holding a token the server
reports as revoked — reading it yields a silent 401 that looks like a dead
seat. The Keychain entry is live but expires within hours. The env var is a
long-lived `sk-ant-oat0` credential and is the only source `direct.sh` reads.
Export it from `~/.zshenv`: `~/.zshrc` is read by interactive shells only, and
a backgrounded panelist is not one.

### Round split

Review reads the repository and stays on the CLI. Debate and rebuttal do not,
and go direct. Do not "simplify" by routing review through `direct.sh` — that
deletes the check behind `review.md`'s "a wrong file path or line number
discredits every other finding you make."
````

- [ ] **Step 6: Run the full suite**

Run: `python3 -m unittest discover -s tests -q`
Expected: PASS, including `test_no_private_content` and `test_review_chain`.

- [ ] **Step 7: Commit**

```bash
git add skills/tribunal-review/SKILL.md \
        skills/tribunal-review/references/panel-cli-notes.md \
        tests/test_tribunal_transport.py
git commit -m "feat(tribunal): route debate and rebuttal through the direct transport"
```

---

### Task 5: Keep one Cursor chat for the whole panel

Cursor is the one seat with no direct transport, so it converts by reusing a
server-side session instead. Step 3 opens the chat; Steps 5 and 6 resume it, and
never resend the diff the seat already read.

The panel weight change this implies (Cursor 0.95 → 0.90, confidence bypass
1.95 → 1.90) is **already applied** in `SKILL.md`, `README.md`, `rules/CLAUDE.md`
and `tests/test_review_chain.py`. Do not redo it; do not revert it.

**Files:**
- Modify: `skills/tribunal-review/SKILL.md` — Step 3 Cursor block
- Test: `tests/test_tribunal_transport.py`

**Interfaces:**
- Produces: `$CURSOR_CHAT`, a chat UUID set in Step 3 and read in Step 5.

- [ ] **Step 1: Write the failing tests**

```python
class TestCursorSession(unittest.TestCase):
    def _step(self, header):
        body = TRIBUNAL.read_text()
        start = body.index(header)
        nxt = body.find("\n## ", start + 1)
        return body[start:nxt if nxt != -1 else len(body)]

    def test_step3_opens_one_chat(self):
        """One chat for the run; without it there is nothing to resume."""
        step3 = self._step("## Step 3 — Launch the panel in parallel")
        self.assertIn("create-chat", step3)
        self.assertIn("CURSOR_CHAT=", step3)

    def test_every_cursor_call_carries_resume_and_workspace(self):
        """Dropping --workspace on a resumed turn forks the session silently.

        The panelist then answers from an empty context with no error, which is
        exactly the disqualifying failure review.md names: a confident finding
        with a fabricated file path.
        """
        body = TRIBUNAL.read_text()
        calls = [ln for ln in body.splitlines() if "cursor-agent -p" in ln]
        self.assertTrue(calls, "no cursor-agent invocation found")
        for ln in calls:
            block = body[body.index(ln):body.index(ln) + 400]
            self.assertIn("--resume", block, f"no --resume near: {ln}")
            self.assertIn("--workspace", block, f"no --workspace near: {ln}")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m unittest discover -s tests -q -k TestCursorSession`
Expected: FAIL — `create-chat` is not in Step 3 yet.

- [ ] **Step 3: Open the chat in `SKILL.md` Step 3**

Replace the Cursor block:

```bash
# --- Cursor / Grok 4.6 ---------------------------------------------------
# One chat for the whole panel. Later rounds resume it instead of resending
# the diff. --workspace must repeat on every turn: dropping it forks the
# session silently and the seat answers from an empty context.
CURSOR_CHAT=$(cursor-agent create-chat 2>/dev/null | tr -d '[:space:]')
cursor-agent -p --trust --mode ask --model cursor-grok-4.6-high \
    --resume "$CURSOR_CHAT" --workspace "$REPO_OR_WORKTREE" \
    --output-format text \
    < "$SP/prompt-cursor.md" > "$SP/cursor.txt" 2>"$SP/cursor.log" &
CURSOR_PID=$!
PANEL_PIDS+=("$CURSOR_PID")
```

If `create-chat` returns empty, `$CURSOR_CHAT` is empty and `--resume ""` fails
fast with `chat ID must be a UUID`. That is the correct behaviour: a Cursor seat
that cannot hold a session is reported missing in the Step 6 header, not run
blind.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -q`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add skills/tribunal-review/SKILL.md tests/test_tribunal_transport.py
git commit -m "feat(tribunal): keep one Cursor chat across all three rounds"
```

## Verification

Contract tests cover shape, not liveness. Before reporting done, run one real
debate call by hand and record the evidence:

```bash
. skills/tribunal-review/panel/direct.sh
direct_preflight && echo preflight-ok
printf 'Reply with exactly READY\n' > /tmp/p.md
direct_codex /tmp/p.md /tmp/o.txt && cat /tmp/o.txt
direct_claude /tmp/p.md /tmp/oc.txt && cat /tmp/oc.txt
```

Expected: `preflight-ok`, then `READY` from each, with no fallback line on
stderr. A fallback line means the direct path failed and the CLI covered it —
report that as a failure of this plan, not a pass.

Then prove the Cursor chat actually carries context between rounds:

```bash
CID=$(cursor-agent create-chat | tr -d '[:space:]')
cursor-agent -p --trust --mode ask --model cursor-grok-4.6-high \
  --resume "$CID" --workspace "$PWD" --output-format text \
  <<< 'Read README.md and reply with ONLY its first heading text.'
cursor-agent -p --trust --mode ask --model cursor-grok-4.6-high \
  --resume "$CID" --workspace "$PWD" --output-format text \
  <<< 'From memory, without reading anything: which file did you just read?'
```

Expected: the second call names `README.md`. If it says it has read nothing,
the session forked — check that `--workspace` is on both calls.

## Out of scope

Converting the review round; a direct transport for Cursor; the Gemini seat;
token refresh. All are argued in the design doc.
