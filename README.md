# Adaptive Learning System

A private, portable implementation of an AI-in-the-loop learning protocol for
Codex and Obsidian. The system maps a learner's relevant knowledge boundary,
builds a verified dependency plan, teaches one node at a time, requires active
production and transfer, and persists the durable result in linked Markdown
artifacts.

Current protocol: `2026-08-26.1`.

## Start here

- [Portable specification](AI%20Learning%20System%20%E2%80%94%20Portable%20Specification.md)
- [Codex adapter](Codex%20Learning%20System.md)
- [Learning protocol](Learning%20System.md)
- [AI learning contract](AI%20Learning%20Contract.md)

## Repository layout

- `.agents/skills/teach/` — adaptive teaching protocol and deterministic
  session factory, validator, and lifecycle tests.
- `.agents/learning-quiz/` — local answer-hidden single-select STDIO MCP
  server and leakage/path/state tests.
- `.agents/skills/retrieve/` — due-session discovery, answer-hidden delayed
  retrieval, transactional sidecar evidence, scheduling, and completion
  validation.
- `.agents/skills/learning-visuals/` — constrained Mermaid/SVG contract plus a
  local render, inspect, receipt-publish pipeline with a pinned bundled SVG
  font.
- `.codex/agents/` — bounded researcher, verifier, and visualizer model roles.
- `Templates/` — linked learner-facing session and teacher-facing log.
- `.obsidian/snippets/` — responsive Mermaid styling for Obsidian.
- Root Markdown files — provider-neutral design, evidence standards, and
  research basis.

## Install or update a vault

`manifest.txt` is the privacy boundary and the complete list of files intended
for copying. Preview changes before applying them:

```bash
rsync -avni --files-from=manifest.txt ./ /absolute/path/to/vault/
rsync -avi --files-from=manifest.txt ./ /absolute/path/to/vault/
```

To refresh this repository from the authoritative files in a vault, reverse
the source and destination, again previewing first:

```bash
rsync -avni --files-from=manifest.txt /absolute/path/to/vault/ ./
rsync -avi --files-from=manifest.txt /absolute/path/to/vault/ ./
```

These commands can overwrite listed files. Inspect the dry-run and repository
diff before applying or committing.

## Install local runtime dependencies

The quiz server and visual renderer keep their dependencies inside their own
ignored directories:

```bash
npm --prefix .agents/learning-quiz ci
npm --prefix .agents/skills/learning-visuals ci
```

Configure the quiz as a project-scoped STDIO MCP server in the target vault's
`.codex/config.toml`, replacing the absolute paths with that vault's path:

```toml
[mcp_servers.learning_quiz]
command = "node"
args = ["src/server.js"]
cwd = "/absolute/path/to/vault/.agents/learning-quiz"
startup_timeout_sec = 10

[mcp_servers.learning_quiz.env]
LEARNING_QUIZ_VAULT_ROOT = "/absolute/path/to/vault"
LEARNING_QUIZ_STATE_ROOT = "/absolute/path/to/vault/.agents/learning-quiz/.state"
```

Restart the Codex client after changing MCP configuration, then verify the
entry with `codex mcp list`.

## Run deterministic regression tests

```bash
npm --prefix .agents/learning-quiz test
npm --prefix .agents/skills/learning-visuals test
npm --prefix .agents/skills/learning-visuals run test:python
python3 -m unittest discover -s .agents/skills/teach/tests -p 'test_*.py'
python3 -m unittest discover -s .agents/skills/retrieve/tests -p 'test_*.py'
```

## Validate a session

```bash
python3 .agents/skills/teach/scripts/validate_session.py \
  "Session Note.md" "Session Note — Session Log.md" --require-active-check
```

Use `--require-closeout` after same-day transfer. The validator enforces the
artifact structure and synchronization; the teacher/verifier must still audit
whether a transfer semantically covers every clause of the learning goal.

## Run delayed retrieval

List due sessions without mutating the vault:

```bash
python3 .agents/skills/retrieve/scripts/retrieval_state.py discover . --json
```

The `$retrieve` skill prepares exactly one due prompt, keeps raw answers and
assessments in the linked sidecar, and advances to `complete` only after two
ordered delayed passes. The documented intervals are configurable product
defaults, not claims of universal optimality.

## Privacy boundary

This repository contains only reusable system files. Learning-session notes,
learner responses, recruiting material, vault state, and other personal notes
must remain outside it even when the repository is private.
