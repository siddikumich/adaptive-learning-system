# Assessment JSON

`record` accepts one UTF-8 JSON object. It never evaluates the answer itself.
The teacher supplies the semantic assessment after rereading the current
prompt, source pack, lesson, and learner map.

```json
{
  "outcome": "pass",
  "source_lesson_basis": ["[[Source note]]", "### Node 2 — Invariant"],
  "rationale": "The response states the required invariant and applies it to the new case.",
  "corrective_feedback": ""
}
```

Required fields:

- `outcome`: one of `pass`, `partial`, `miss`, or `ungradable`.
- `source_lesson_basis`: a nonempty string or a nonempty list of nonempty
  strings identifying the source and/or lesson basis used for the judgment.
- `rationale`: a nonempty string.
- `corrective_feedback`: a string. It is delivered only after the answer.

`ungradable` records the repair information but does not alter stage, pass
count, status, or due date. Correct the assessment or session artifact and
prepare the same retrieval again.
