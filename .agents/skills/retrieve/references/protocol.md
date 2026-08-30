# Retrieval protocol

The main note carries these canonical properties:

```yaml
retrieval-schema: "1"
retrieval-enabled: true
retrieval-timezone: America/Detroit
retrieval-started: YYYY-MM-DD
retrieval-stage: initial # initial | interleaved | complete
retrieval-required-passes: 2
retrieval-passes: 0 # 0 | 1 | 2
next-retrieval: YYYY-MM-DD # blank only when complete
status: awaiting-retrieval # complete only after the second pass
```

All retrieval dates are all-day dates in the per-note IANA timezone. The
initial due date is `retrieval-started + 2` local calendar days. A pass at the
initial stage schedules interleaved retrieval for the local assessment date
plus five days. A partial response schedules the same stage at +2 days; a miss
schedules it at +1 day; `ungradable` leaves the stage, pass count, status, and
date unchanged. An interleaved pass sets `complete`, `2`, and a blank next
date. A late answer is assessed normally; retain the old scheduled date in the
sidecar and calculate any next date from the actual local assessment date.

Each prepared and committed event lives only in the linked sidecar. Events are
append-only, readable Markdown with an unobtrusive HTML JSON marker for safe
recovery. A committed event preserves its attempt ID, stage, scheduled and
presented dates, prompt fingerprint, prompt, verbatim answer, assessment,
assessment date, next date, answer/assessment fingerprints, and transaction
marker. The helper serializes mutations with a
per-session lock, so a prepared attempt is reused rather than duplicated.
State synchronization updates only the main note's compact retrieval fields,
status lines, and operational `Smallest next action`. It does not rewrite the
lesson, learner map, or semantic evidence-boundary claims.

Legacy `2026-08-25.6` notes may be migrated when the linked sidecar contains a
dated closeout heading. The helper never guesses `retrieval-started`; without
that evidence it reports a repair requirement. Migration derives the initial
schema-1 due date from that evidenced closeout date rather than preserving an
arbitrary legacy date.
