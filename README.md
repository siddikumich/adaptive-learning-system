# Adaptive Learning System

A private, portable implementation of an AI-in-the-loop learning protocol for
Codex and Obsidian. The system maps a learner's relevant knowledge boundary,
builds a verified dependency plan, teaches one node at a time, requires active
production and transfer, and persists the durable result in linked Markdown
artifacts.

Current protocol: `2026-08-25.6`.

## Start here

- [Portable specification](AI%20Learning%20System%20%E2%80%94%20Portable%20Specification.md)
- [Codex adapter](Codex%20Learning%20System.md)
- [Learning protocol](Learning%20System.md)
- [AI learning contract](AI%20Learning%20Contract.md)

## Repository layout

- `.agents/skills/teach/` — adaptive teaching protocol and deterministic
  session validator.
- `.agents/skills/learning-visuals/` — Obsidian-native Mermaid/SVG contract.
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

## Validate a session

```bash
python3 .agents/skills/teach/scripts/validate_session.py \
  "Session Note.md" "Session Note — Session Log.md" --require-active-check
```

Use `--require-closeout` after same-day transfer. The validator enforces the
artifact structure and synchronization; the teacher/verifier must still audit
whether a transfer semantically covers every clause of the learning goal.

## Privacy boundary

This repository contains only reusable system files. Learning-session notes,
learner responses, recruiting material, vault state, and other personal notes
must remain outside it even when the repository is private.
