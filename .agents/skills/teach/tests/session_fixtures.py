from __future__ import annotations

from pathlib import Path


PROTOCOL = "2026-08-26.1"
ACTIVE_CHECK = "Given a fresh case, write the one invariant that determines the legal next move."


def session_note(
    title: str,
    *,
    status: str = "awaiting-retrieval",
    stage: str = "initial",
    passes: int = 0,
    due: str = "2026-01-03",
    source_link: str = "[[Source]]",
) -> str:
    return f'''---
type: learning-session
status: {status}
topic: Test topic
goal: Apply the scoped rule independently
created: 2026-01-01
updated: 2026-01-01
source-note: "{source_link}"
session-log: "[[{title} — Session Log]]"
protocol-version: "{PROTOCOL}"
interaction-mode: obsidian-read-cli-answer
retrieval-schema: "1"
retrieval-enabled: true
retrieval-timezone: America/Detroit
retrieval-started: 2026-01-01
retrieval-stage: {stage}
retrieval-required-passes: 2
retrieval-passes: {passes}
next-retrieval: "{due}"
tags:
  - learnings
---

# {title}

## Goal

Independent capability: Apply the scoped rule independently to a novel case.

Out of scope: Unrelated variants.

## Source pack

- [[Source]]
- Verification method: inspect the local source and test a counterexample.

## Learner map

```mermaid
flowchart LR
  foundation["Scoped foundation"]
```

| Strand | Verified floor | Observed ceiling | Misconception or uncertainty | Evidence type | Status |
| --- | --- | --- | --- | --- | --- |
| Rule | Defines invariant | Novel transfer | None observed | transfer | demonstrated |

Current node: Scoped foundation

Status: `demonstrated`

## Dependency plan

Root audit:

| Root | Classification | Conditions / caveats | Evidence or establishment |
| --- | --- | --- | --- |
| Scoped foundation | demonstrated | Within the stated source scope | Unscaffolded transfer in the session log |

```mermaid
flowchart TD
  foundation["Scoped foundation"] --> goal["Independent capability"]
```

- `foundation → goal`: the goal requires applying the scoped foundation.

## Lessons

### Node 1 — Scoped foundation

> [!info] Node status
> **Evidence:** `demonstrated`
> **Advance when:** the learner applies the invariant to a novel case.

#### Why this node

The cold attempt showed why the invariant controls the next move.

#### Core rule

Preserve the one source-grounded invariant.

#### Derivation

The legal next move follows by checking the invariant against the case.

#### Worked example or contrast

A legal case preserves the invariant; a nearby illegal case violates it.

#### Connection

This establishes the root needed for the independent capability.

#### Verification

The local [[Source]] note and a counterexample ground this rule.

#### Active check

{ACTIVE_CHECK}

## Transfer and retrieval

- Novel application: Applied the invariant to a new case not used in instruction.
- Result and verification: Correct result verified against [[Source]] and a counterexample.

### Delayed retrieval

- Completion criterion: Two committed delayed passes, in order (initial then interleaved), each presented after retrieval starts.
- Current stage: {stage}
- Next retrieval: {due}

#### Initial retrieval prompt

From memory, state the invariant and apply it to one new case.

#### Interleaved retrieval prompt

From memory, distinguish the invariant from the closest confusable rule using one counterexample.

### Evidence boundary

Known: The learner completed the same-day transfer.

Inference: The mechanism is available for near-term independent use.

Unknown: Delayed retention before both retrieval passes.

To verify: Two delayed, answer-hidden production attempts.

Smallest next action: Answer the scheduled prompt from memory.

## Related

- [[Learning System]]
- [[AI Learning Contract]]
'''


def session_log(title: str, *, status: str = "awaiting-retrieval", pending: bool = False) -> str:
    pending_block = (
        f"\n### Active check pending\n\nActive check:\n\n{ACTIVE_CHECK}\n\n"
        "Assessment: pending learner response.\n"
        if pending
        else ""
    )
    return f'''---
type: learning-session-log
status: {status}
session-note: "[[{title}]]"
protocol-version: "{PROTOCOL}"
created: 2026-01-01
updated: 2026-01-01
tags:
  - learnings
---

# {title} — Session Log

## Log

### 2026-01-01 closeout

- Transfer assessed as demonstrated.
{pending_block}
## Retrieval history
'''


def write_closed_session(root: Path, title: str = "Lifecycle") -> tuple[Path, Path]:
    source = root / "Source.md"
    source.write_text("# Source\n\nThe scoped rule is grounded here.\n", encoding="utf-8")
    note = root / f"{title}.md"
    log = root / f"{title} — Session Log.md"
    note.write_text(session_note(title), encoding="utf-8")
    log.write_text(session_log(title), encoding="utf-8")
    return note, log
