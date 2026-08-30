---
type: finding
status: active
created: 2026-08-30
updated: 2026-08-30
tags:
  - learnings
  - systems
---

# Learning system gap closure — 2026-08-30

## Scope and sources

This audit compares the local [[Codex Learning System]] with the pinned
[Amos Blomqvist learning configuration](https://github.com/amosblomqvist/learn/tree/73eaf7c5a1a0c19217ba98580e4fc4de35841aa6),
especially its
[quiz extension](https://github.com/amosblomqvist/learn/blob/73eaf7c5a1a0c19217ba98580e4fc4de35841aa6/extensions/quiz.ts)
and
[Markdown-log extension](https://github.com/amosblomqvist/learn/blob/73eaf7c5a1a0c19217ba98580e4fc4de35841aa6/extensions/md-log.ts).
The Codex adaptation was checked against the official
[plugin](https://developers.openai.com/codex/plugins/),
[MCP](https://developers.openai.com/codex/mcp/), and
[hook](https://developers.openai.com/codex/hooks/) documentation.

## Findings and closure

| Capability | Pinned upstream evidence | Local result | Status |
| --- | --- | --- | --- |
| Keyed quiz with stable values, shuffled display order, `I don't know`, and post-answer feedback | `extensions/quiz.ts` | `.agents/learning-quiz/` provides a local STDIO MCP lifecycle: verifier-only registration, sanitized presentation, and post-response submission. Stable values, key, and explanation are absent from the parent pre-answer payload. | Major safety gap closed for single-select diagnostics |
| Persistent linked Markdown record | `extensions/md-log.ts` | Learning sessions already use reciprocal main-note and sidecar links. The new session factory creates the pair from current templates without overwriting existing files. | Existing capability hardened |
| Rendered instructional visuals | Upstream lists `visual-tools` and visual-maker agents | `.agents/skills/learning-visuals/` validates constrained Mermaid/SVG, renders a local PNG, requires preview inspection, binds source to inspected bytes, publishes without clobbering, and requires final inspection. | Major render/inspection gap closed |
| Protocol regression coverage | No equivalent claim inferred from the upstream README | Current-protocol factory, validator, closeout, exact active-check, retrieval, and full two-pass lifecycle tests now run without model calls. | Major assurance gap closed |
| Explicit invocation | Local requirement prompted by an observed accidental self-invocation | The existing `allow_implicit_invocation: false` policy is now locked by a regression check. | Safeguard added |

## Verification performed

- Quiz MCP: 11 tests passed, including recursive pre-answer leakage checks,
  stable-value rejection on submission, persisted shuffle, path confinement,
  private atomic state, and an end-to-end STDIO MCP lifecycle.
- Visual pipeline: 10 Node tests and 2 CLI-contract tests passed. Real Mermaid
  and SVG fixtures rendered from the vault root and were inspected with
  `view_image`; both were legible and unclipped.
- Teaching integration: 10 tests passed, including reciprocal session creation,
  exact active-check synchronization, resolvable Obsidian source links,
  closeout, and a factory-to-two-delayed-pass lifecycle.
- Retrieval: 15 tests passed, including the initial `retrieval-started + 2`
  invariant and named legacy migration behavior.
- Skill packaging validation passed for `teach`, `retrieve`, and
  `learning-visuals`. `codex mcp list` recognized `learning_quiz` as enabled.

## Evidence boundary

Known: the deterministic implementations and tests above pass in this vault on
2026-08-30. The answer key is stored locally in mode-restricted runtime state
and is not returned by `register_quiz` or `present_quiz`.

Inference: this closes the consequential safety and reliability differences
that can be adapted through documented Codex MCP and local-script interfaces.
It does not reproduce Pi's custom blocking TUI; Codex uses a two-turn chat
interaction around MCP calls.

Unknown: deterministic validation still cannot prove that a transfer exercise
covers every semantic clause of an arbitrary natural-language goal. The
teacher and verifier must audit that alignment. Model-level behavioral evals
were not added, so explicit-only host behavior and teaching judgment are not
proven by the zero-model-cost test suites.

To verify: run the next real explicitly invoked `$teach` session through one
quiz item, one inspected visual where materially useful, same-day closeout, and
both delayed retrieval passes. Record any observed workflow failure before
adding more machinery.

## Related

- [[Learning System]]
- [[AI Learning Contract]]
- [[AI Learning System — Portable Specification]]
- [[Codex Learning System]]
- [[CURRENT-STATE]]
