---
name: retrieve
description: Run and record delayed retrieval for completed learning sessions, using their source-grounded prompts and sidecars without putting answers in the learner-facing note.
---

# Delayed retrieval

Use this skill after a learning session has entered delayed retrieval. It
maintains the operational state in a linked session-log sidecar while the main
Obsidian note remains a compact learner-facing reminder.

Run discovery before choosing a session:

```bash
python3 .agents/skills/retrieve/scripts/retrieval_state.py discover . --json
```

If discovery reports a legacy session as migratable, run `recover` on that
session and rediscover. Never invent a missing closeout date. Select only the
first item in the sorted `due` list; `prepare` refuses future items.

For a due session, reread its source pack, completed lesson, learner map, and
the one current prompt before judging an answer. The helper intentionally does
not author prompts or grade semantics. Prepare the attempt before displaying
the prompt, present exactly the `PROMPT` between its markers, and do not reveal
feedback until after the learner answers:

```bash
python3 .agents/skills/retrieve/scripts/retrieval_state.py prepare "<session-note>"
```

Write the learner's response verbatim to a temporary answer file. Write an
assessment JSON conforming to [the assessment contract](references/assessment.md),
then commit it:

```bash
python3 .agents/skills/retrieve/scripts/retrieval_state.py record "<session-note>" \
  --attempt-id "<id>" --answer-file "<answer-file>" --assessment-file "<assessment.json>"
```

Use `recover` after an interrupted operation and `validate` before declaring a
retrieval cycle complete. `prepare` reuses a pending attempt; never pose a
second prompt while one is prepared. A repeated `record` is idempotent only
when its answer and assessment match the original commit. The default intervals (initial +2 days,
then +5 after a pass; retries +2/+1) are product defaults, not universal
learning claims.

The main note must use retrieval schema `1`: compact status lines and exactly
one `#### Initial retrieval prompt` and `#### Interleaved retrieval prompt`
under `## Transfer and retrieval` → `### Delayed retrieval`. Do not put raw
answers, assessments, grading rationale, or event history in the main note.

For CLI fields, recovery rules, and sidecar event details, read
[the retrieval protocol](references/protocol.md) when changing state or
repairing a session.
