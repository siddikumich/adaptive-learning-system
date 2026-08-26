---
type: guide
status: active
updated: 2026-08-26
---

# Learning system

## Aim

Build durable technical judgment and skill—not the feeling of studying, a large
set of notes, or dependence on [[AI Learning Contract|AI]]. The standard is:
can I retrieve, explain, apply, test, and adapt this on a new problem?

This is a starting protocol, not an identity test. Run it for two weeks, then
change only what evidence from your work says to change.

## The core loop

1. **Attempt.** Before notes, documentation, or AI, state the problem, a plan
   or hypothesis, and your confidence. Solve, trace, design, or explain from
   memory.
2. **Inspect.** Compare the attempt against an authoritative artifact:
   course material, textbook, official documentation, runnable code, test
   output, data, or a qualified instructor's feedback.
3. **Correct.** Name the exact gap: missing knowledge, faulty mental model,
   implementation error, misunderstood specification, or rushed reasoning.
4. **Apply.** Solve a nearby problem, write a variation from a blank file, or
   test the updated model. Do not stop at recognizing the correction.
5. **Revisit.** Return to the idea after a delay; mix it with similar concepts
   once the basics are stable.

[[Learning Research Sources|Why this works and the evidence boundaries]]

## AI-guided deep-learning sessions

For a difficult topic that benefits from a personal teacher, use the
[[Codex Learning System|Codex learning interface]]. It operationalizes the same
core loop as **probe → verify and plan → teach one dependency node → apply →
retrieve**.

The provider-neutral contract and migration handoff live in
[[AI Learning System — Portable Specification]].

The division of labor is deliberate:

- Farhan does the productive struggle: retrieval, prediction, construction,
  explanation, debugging, discrimination, and transfer.
- Codex removes logistical struggle: adaptive question selection, source
  coordination, dependency mapping, feedback timing, teacher-facing sidecar
  logging, and retrieval-prompt generation.
- Original course material, official documentation, papers, runnable code,
  tests, and data remain the sources of truth.

Start from [[Learning Session Template]]. The diagnostic phase brackets the
relevant edge of knowledge rather than asking a fixed generic pretest. The plan
is shown as an editable Mermaid dependency graph, stress-tests each proposed
root, and requires approval before teaching. A materially vague learning goal
gets one clarifying question rather than invented specificity. Teaching then
advances exactly one node at a time. The readable
session note receives a complete lesson after the first cold attempt;
raw questions, responses, and assessments stay in a linked session-log
sidecar. A node is not treated as demonstrated until Farhan produces an
explanation, trace, derivation, implementation, counterexample, or novel
application; a correct multiple-choice response is supporting evidence only.
For state modeling, sufficiency determines correctness; eliminating redundant
fields is a separate clarity and efficiency improvement.

Use Obsidian to read the canonical node lesson and dependency visuals. Use the
Codex CLI to answer the active check, ask questions, and approve or redirect
the path. The CLI check must match the note exactly; it should not introduce a
second condensed version of the lesson.

Before plan approval and each teaching/check reply, the session validator
checks the learner-note/sidecar backlinks, protocol versions, lesson hierarchy,
status synchronization, dependency-root audit, and pending active-check
equality. If a node is reteaught, the newest append-only check becomes the
canonical prompt while the earlier attempt remains in the record.
The reteach preserves already-correct components and isolates the remaining
output instead of repeatedly requesting a full solution. Graph- and
state-heavy nodes receive explanatory visuals by default, while answer-hidden
visuals contain only the supplied input.
The same preflight rejects non-Obsidian math delimiters: use `$...$` inline and
`$$` display blocks, never `\(...\)` or `\[...\]`.

The same-day session ends with a transfer task, dated retrieval prompts, and
an `awaiting-retrieval` closeout validated separately from an active check.
This adds
the missing calibration loop without turning the vault into a transcript
archive: keep sessions that contain a durable learner map, decision, source
trail, or retrieval artifact, and discard empty experiments.

## Class and reading workflow

Keep handwriting if it helps you attend and think. Do not transcribe it into
Obsidian.

Within 24 hours, create or update the relevant course/concept note with a
five-to-ten-minute synthesis:

- Three claims in your own words.
- One worked example, derivation, code trace, or counterexample.
- Two to five questions you should answer without notes later.
- One unresolved question and a link to its course, concept, project, person,
  or source.

This is the bridge between handwriting for first-pass processing and Obsidian
for retrieval, linking, and reuse. [[Evergreen]] notes are optional: use one
only when an idea survives beyond a single course or project.

## Study cadence

- **Same day:** a brief closed-note recall or one representative problem.
- **2–3 days later:** retrieve again; correct misses from the source.
- **About a week later:** mixed practice with similar, confusable concepts.
- **2–3 weeks later:** retrieve only ideas still likely to matter.

Use the timing as a starting point, not a streak. A miss is a signal to revisit,
not evidence that you are failing.

## Technical practice

For a focused 60–120 minute session outside ordinary coursework:

1. Choose one concrete subskill and an observable output.
2. Spend 10 minutes on closed-note recall, prediction, or a plan.
3. Spend 35–70 minutes solving, building, reading real code, or debugging.
4. Spend 10 minutes verifying with tests, source, docs, data, or focused human
   feedback.
5. Spend 5 minutes recording the surprise, error type, and next retrieval
   prompt in the relevant note.

For systems/code reading, predict control flow, data flow, invariants, failure
modes, and one concrete trace *before* running it. Then run focused tests or
instrumentation and update the model from evidence.

For debugging, make a minimal reproduction and a small hypothesis table:
`hypothesis → predicted observation → cheapest discriminating test → result`.
Change one causal variable at a time; finish with a regression test or stated
invariant.

For projects, work in vertical slices: correctness baseline → instrumentation
→ stress/failure condition → bottleneck hypothesis → change → before/after
measurement. This is how project work creates feedback rather than becoming
tutorial-following.

For algorithm-interview preparation, use [[NC150 Reactivation]] rather than
starting a rusty prior problem set from zero.

For unfamiliar problems across domains, use [[General Reasoning Practice]] to
separate representation, hypothesis testing, transfer, and retrieval.

## Weekly calibration

In the current [[Weekly Notes|weekly note]]:

- Pick one or two measurable learning objectives, not an aspirational list.
- Do one cold mixed practice, code-reading, debugging, or explanation task.
- Review misses by category: knowledge, mental model, implementation,
  specification, or rushing.
- Adapt next week's practice to the largest category.

Track evidence of capability—accurate explanation, passed tests, quality of a
new design, benchmark result, or performance on a novel variant—not hours,
pages, or flashcard counts.

For a live choice between broadening and deepening, use [[Exploration, Exploitation, and Simulated Annealing]] to run a bounded probe rather than adding novelty without a decision or feedback loop.

## Capacity is part of the system

Protect a sustainable sleep routine, recovery, and time outside work. The
evidence supports their importance to learning capacity, but they are not
optimization projects. Five to seven focused hours of deliberate supplemental
practice in a week is more valuable than intermittent anxiety-driven marathons.

## Related

- [[AI Learning Contract]]
- [[Learning Research Sources]]
- [[General Reasoning Practice]]
- [[Exploration, Exploitation, and Simulated Annealing]]
- [[Terminal Workflow — tmux and Neovim]]
- [[NC150 Reactivation]]
- [[AI Learning System — Portable Specification]]
- [[Codex Learning System]]
- [[Learning Session Template]]
- [[Fall 2026]]
- [[CURRENT-STATE]]
