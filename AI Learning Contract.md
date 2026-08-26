---
type: guide
status: active
updated: 2026-08-26
---

# AI learning contract

AI is a questioning partner, practice generator, and feedback tool. It is not
the primary source, an answer dispenser, or a substitute for doing the hard
cognitive work.

## Required loop

**Attempt → hint → explain → verify → retrieve**

1. Attempt alone and preserve your assumptions, plan, and sticking point.
2. Ask for one Socratic question or a graduated hint—not a solution.
3. Explain or implement the next step in your own words/code.
4. Ask for the most consequential error, missing assumption, counterexample, or
   test case.
5. Verify claims against original course materials, official documentation,
   papers, runnable code, tests, or data. AI is never the evidence source. Use
   [[Vault Source Integrity Protocol]] when a web source is incomplete or
   inaccessible.
6. Close the same-day lesson as `awaiting-retrieval`, then use `$retrieve` at
   the scheduled time. It shows one answer-hidden prompt in the CLI; the
   teacher rereads the source pack, learner map, and lesson before a
   source-grounded correction, and the raw response and assessment stay in the
   session-log sidecar. `complete` requires two committed delayed passes in
   order, not a feeling of fluency.

The system's +2 / +5 / +2 / +1 calendar-day schedule is a transparent product
default (initial / passed interleaved / partial retry / miss retry), not a
universal optimum. Retrieval and spacing are supported practices; feedback and
interleaving need the task-sensitive interpretation summarized in
[[Learning Research Sources]].

For a structured version of this loop, use [[Codex Learning System]]. Its
diagnostic quiz is a fast way to select the next task, not proof of mastery.
Important nodes still require free explanation, construction, tracing,
derivation, implementation, or transfer, followed by verification against an
original artifact.

## Good uses

- Generate varied practice questions, edge cases, and test cases after a real
  attempt.
- Critique a concrete solution, explanation, design, PR, or benchmark read.
- Role-play an interviewer, reviewer, or skeptical teammate.
- Turn *your processed notes* into retrieval questions.
- Explain a source after you have read it; contrast approaches; expose missing
  assumptions; help organize a synthesis.

## Default-off uses

- First-pass answers to coursework or interview problems.
- Submitting AI-written work or code you cannot trace, test, modify, and defend.
- AI-generated citations, measurements, project claims, or sources without
  direct verification.
- Uploading private class, internship, employer, financial, health, or personal
  material without permission and a clear privacy decision.

## Prompt to start with

> I am learning **[topic]**. Do not give a solution. First ask me to state my
> approach. Then give one minimal hint at a time, diagnose my reasoning, and
> require me to explain the next step. Flag uncertainty and name the primary
> source or test that would verify each important claim.

## Record material AI use

For a major learning, recruiting, or research artifact, add a short footer when
useful: tool/date, AI role, and what you independently verified or changed. It
keeps your understanding and provenance clear.

## Related

- [[Learning System]]
- [[AI Learning System — Portable Specification]]
- [[Learning Research Sources]]
- [[Vault Source Integrity Protocol]]
- [[Codex Learning System]]
- [[Learning Session Template]]
- [[AGENTS]]
