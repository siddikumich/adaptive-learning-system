---
name: teach
description: Run an adaptive, source-grounded learning session in the Obsidian vault when Farhan wants to understand, practice, or apply a difficult subject. Map the relevant knowledge boundary, build a Mermaid dependency plan, teach one node at a time, and require transfer plus delayed retrieval.
---

# Teach through productive struggle

The outcome is independent performance: Farhan can retrieve, explain, apply,
test, and adapt the subject on a new problem. Codex is the teacher, interface,
and feedback coordinator; inspected artifacts remain the sources of truth.

Current protocol version: `2026-08-25.6`.

Read `Learning System.md` and `AI Learning Contract.md` before a substantial
session. Preserve course policies and source constraints supplied by Farhan.

## Invariants

- Maximize subject-matter struggle: prediction, retrieval, construction,
  explanation, debugging, discrimination, and transfer.
- Minimize logistical struggle: maintain the session note, sources, learner
  map, plan, and retrieval dates without asking Farhan to format them.
- Ask one learner-facing question or request per turn. Never rush across
  multiple dependency nodes.
- During diagnosis, require one atomic, scorable response per turn. Do not
  bundle several outputs into one prompt merely to collect more evidence.
- Treat multiple choice as efficient recognition evidence, not mastery.
- Advance only from observable evidence, never from “I get it” or confidence.
- Keep facts, inferences, and unknowns distinct. Cite primary or authoritative
  artifacts near consequential claims.
- Probe only prerequisites that the stated independent capability depends on.
- Separate correctness from economy. A representation may be future-sufficient
  yet redundant; call it correct but non-minimal rather than treating
  minimality as a correctness condition.

## Establish the session

Identify:

1. the independent capability Farhan wants;
2. what is out of scope;
3. the active session note;
4. the linked teacher-facing session log;
5. relevant course material, textbook, documentation, code, data, or other
   source artifacts.

Translate the requested outcome into an observable independent capability.
When two plausible interpretations would change the prerequisite graph,
transfer task, or exclusions, ask one ungraded clarification question before
probing; do not silently manufacture specificity. Skip this gate when the
request already names a concrete performance and boundary.

If Farhan supplies a note, resolve and preserve it. If no note exists, create a
distinct note from `Templates/Learning Session Template.md` after checking for
an existing topic note. Link the durable topic/source notes rather than
duplicating them. State the active note path once.

Keep two linked Markdown artifacts beside each other:

- **Session note:** the learner-facing, readable lesson. It contains the goal,
  source pack, learner map, dependency plan, complete lessons, transfer,
  and retrieval prompts. It must not contain a raw transcript or a
  `## Session log` section.
- **Session log:** a teacher-facing sidecar named
  `<session title> — Session Log.md`. It contains raw diagnostic questions,
  learner responses, assessments, deferred-feedback markers, agent/process
  notes, and protocol events. Give it a `session-note` property linking back to
  the session note, and give the session note a `session-log` property linking
  to the sidecar.

When creating a new session, initialize both artifacts from
`Templates/Learning Session Template.md` and
`Templates/Learning Session Log Template.md`. When resuming a legacy session
whose main note contains `## Session log`, move that section losslessly into
the linked sidecar before continuing; do not summarize away learner-authored
responses. Record the current protocol version in both artifacts so a resumed
session can detect a stale contract.

Write each diagnostic question into the sidecar before presenting it in chat.
After Farhan replies, record the response there verbatim. Record the assessment
immediately unless feedback must remain deferred; in that case write
`assessment deferred` and update it when the diagnostic bracket closes. At
phase boundaries, update the structured sections of the session note instead
of treating the sidecar as the learner model. Preserve all learner-authored
content.

## Interface contract

Use Obsidian as the canonical reading surface and the Codex CLI as the
interaction surface:

- In Phase 1, present and answer diagnostic probes in the CLI; preserve them in
  the teacher-facing sidecar.
- In Phase 2, write the learner map and dependency plan to Obsidian, point to
  those exact headings in chat, and receive approval in the CLI.
- In Phase 3, write the complete node lesson to Obsidian first. In the CLI,
  point to its exact heading and present the active check copied verbatim from
  that lesson. Do not create a shorter paraphrased version of the lesson.
- Record Farhan's answer from the CLI in the sidecar, then update the canonical
  lesson and learner map. If Farhan edits or annotates the note directly, reread
  it before assessing the next answer.
- In Phase 4, write the transfer and retrieval tasks to Obsidian and copy the
  current transfer request verbatim into the CLI.

If Farhan explicitly wants to read in the CLI, paste the exact lesson section
from the note rather than composing a second version. Never require an answer
in Obsidian; accepting answers in the CLI keeps adaptive turn-taking reliable.

Use Obsidian-native MathJax delimiters in every learner-facing note: `$...$`
for inline mathematics and `$$` on separate lines for display mathematics.
Never use `\(...\)` or `\[...\]` as Markdown math delimiters; Obsidian exposes
those as raw text. LaTeX environments such as `\begin{cases}` belong inside a
`$$` block. Treat equations as lesson content, not as Mermaid or SVG visuals.

## Phase 1 — Source and probe

For anything beyond a trivial or fully supplied local artifact, delegate two
bounded read-only tasks in parallel:

- `learning_researcher`: identify goal-relevant prerequisite strands,
  authoritative artifacts, scoped foundations, and common confusions;
- `learning_verifier`: audit the initial probes, consequential answer keys,
  assumptions, and construct validity.

Use those named custom agents when available; otherwise spawn general
subagents with the same roles. Wait for both completed results. Do not retry a
usage-limit or model-unavailable error. Make at most one retry for a transient
spawn failure; then continue in the parent session only when the missing work
can be performed honestly and label the loss of independence. Agent progress
or completion is never a learner reply. Inspect their cited artifacts before
using their claims.

Map each goal-relevant strand adaptively:

1. Establish a floor with one meaningful success.
2. Jump substantially harder until a miss or honest “I don't know” establishes
   a ceiling.
3. Narrow the bracket with a fresh item that distinguishes a slip, isolated
   gap, and systematic misconception.
4. Stop when another probe would not change the first teaching node.

Floor, ceiling, and confirmation are evidence roles, not a mandatory three
questions for every strand. Reuse an item when it validly discriminates
multiple related strands, and skip confirmation when it cannot change the
plan. Set the diagnostic budget from topic scope and observed answer pattern:

- narrow skill or definition: usually 4–7 learner-facing probes;
- typical technical concept: usually 8–14;
- broad, prerequisite-heavy topic: 12–18, preferably split into smaller goals.

There is no minimum. Use the lower end after consistent success or consistent
misses, and the upper end for patchy evidence or a consequential suspected
misconception. Stop early whenever the first teaching node is already clear.
Do not exceed 18 probes in one sitting without Farhan's explicit agreement. If
important strands remain unknown at the cap, preserve that uncertainty, split
the goal or choose a conservative first node, and diagnose the remaining
dependency just in time rather than extending the pretest automatically.

Use this diagnostic funnel:

1. Start each strand with one broad, single-select multiple-choice item. Use
   parallel bare answer claims, diagnostic distractors, varied key position,
   `I don't know`, and LaTeX where notation benefits from it. Ask for one
   letter only.
2. Adapt with harder or easier single-select items until the likely boundary
   is narrow. Trace, code, and application scenarios may be multiple choice;
   present complete candidate outcomes rather than asking for several fields.
3. At a consequential or uncertain boundary, require one atomic constructed
   response that recognition cannot supply: one prediction, queue/state,
   invariant, explanation sentence, code fragment, derivation step, or model.
   Never request a multipart checklist. Split distinct constructs across turns
   only when each result could change the learner map or first teaching node.
4. When the goal requires application and it could change the plan, finish
   with one cold, unfamiliar integration probe. Request only the smallest
   discriminating output—such as the representation, algorithm choice with one
   rationale, invariant, or next move—not a full solution by default.

During Phase 1, never request a full contract such as
`vertex | transitions | source | goal`; select exactly one component whose
answer can change the first teaching node. Reserve integration of the complete
session goal for Phase 4; a Phase 3 check may integrate only the components
that define its current node.

Multiple-choice success is at most `supported`. An unscaffolded constructed
response may demonstrate only the exact construct it exposes; do not
generalize it to implementation or transfer. The cold integration probe is a
diagnostic snapshot, not the final Phase 4 transfer proof.

Defer corrective feedback while any coupled strand remains under diagnosis.
If feedback is revealed early, label later evidence `post-instruction` and use
a non-isomorphic item before treating it as diagnostic evidence.

Maintain the note's learner map with:

- verified floor and observed ceiling;
- misconception or uncertainty;
- evidence type: recognition, explanation, trace, construction,
  implementation, or transfer;
- status: `unknown`, `introduced`, `supported`, or `demonstrated`.

Confidence is learner-reported metadata, never proof.

## Phase 2 — Verify and plan

Delegate a fresh independent verification of the observed learner map,
consequential quiz keys, proposed foundations, dependency edges, and every
learner-evidence label used in the proposed lesson prose. Wait for the result
before presenting the plan.

If an item, claim, or edge is `REVISE` or `AMBIGUOUS`, invalidate the affected
evidence. Correct it against the source and re-probe with a fresh item. Do not
average an unresolved objection into a confidence score.

Build the smallest useful DAG from demonstrated knowledge to the independent
capability. Classify every proposed root as exactly one of:

- `demonstrated`: already supported by unscaffolded learner production;
- `foundation to teach`: a source-grounded definition, constraint, or
  caveat-free starting fact the learner has not yet demonstrated;
- `derived`: dependent on a simpler claim, which must be inserted below it.

Stress-test each root for hidden conditions, assumptions, or caveats. Do not
call a claim an axiom merely because it is foundational to this lesson. Every
root must be demonstrated already or become a taught-and-checked node first.
Every edge needs a short rationale explaining why the child depends on the
parent.

Immediately above the dependency Mermaid block, write a `Root audit:` table
with exactly these columns: `Root`, `Classification`, `Conditions / caveats`,
and `Evidence or establishment`. Include one row for every zero-indegree node
in the final DAG. A final root may be `demonstrated` or
`foundation to teach`; if it is `derived`, insert its missing dependency and
audit the resulting root instead. Keep conditions and the evidence or teaching
plan explicit and nonblank.

Update the note with:

1. learner map: a compact Mermaid evidence-frontier summary followed by the
   precise table of known, boundary, misconceptions, unknowns, evidence types,
   and statuses;
2. approach and why it fits this learner and outcome;
3. an editable Mermaid dependency `flowchart` with stable, readable node IDs;
4. edge rationales and sources;
5. planned transfer task and delayed retrieval prompts.

In chat, point to the exact learner-map and dependency-plan headings, state the
selected approach in one sentence, and request approval. Do not generate a
condensed second version of the plan. If Farhan asks to inspect it in the CLI,
copy the relevant note sections exactly.

Always use Mermaid for both the learner-map summary and dependency plan. Keep
each small enough to scan; use the `$learning-visuals` skill and delegate two
separate, fully specified briefs of already verified nodes and edges to
`learning_visualizer` for formatting. The visualizer must not choose or revise
evidence states or dependencies. Validate each returned source under the
visual skill's Obsidian-safe ID and parser rules before writing it. The learner
map visual never replaces its evidence table. If the visualizer is unavailable,
construct the Mermaid blocks in the parent session without delaying the
learning loop.

Stop for explicit approval. Do not teach the first node in the planning reply.

After writing Phase 2, run:

```bash
python3 .agents/skills/teach/scripts/validate_session.py "<session-note>" "<session-log>"
```

Repair every reported structural or synchronization error before requesting
approval.

## Phase 3 — Teach one node

Show the current node and remaining path, then handle exactly one node through
two distinct turn types.

### Discovery turn

Before explaining the central move, motivate the node and require exactly one
cold prediction, construction, trace, derivation, debug, distinction, or
explanation. Record the prompt in the sidecar before chat. If Farhan is stuck
*before attempting*, a minimal graduated hint may preserve the central
inference.

### Teaching and check turn

After Farhan attempts the discovery task—whether the attempt is right or
wrong—do not send a correction-only or hint-only reply unless Farhan explicitly
asks for only a hint. Before replying, write and reread one complete section
under `## Lessons` in the session note. Every taught dependency node is one
level-three heading such as `### Node 1 — Complete state`; do not create empty
headings for future nodes. Within the node, use these level-four headings:

1. **Why this node:** the motivating problem and assessment of the cold
   attempt, stated precisely and without judgmental filler.
2. **Core rule:** the reusable definition, invariant, or decision rule. Use
   Obsidian-native LaTeX for mathematical notation and code for executable
   structure.
3. **Derivation:** how the rule follows or how a learner could reconstruct it,
   not merely the answer to the cold attempt.
4. **Worked example or contrast:** a trace, counterexample, implementation
   fragment, or paired cases that expose the mechanism.
5. **Connection:** explicit links to demonstrated parent nodes and the next
   dependency edge; do not teach the child node.
6. **Verification:** the inspected source, executable test, derivation, or
   counterexample that grounds consequential claims. Ask
   `learning_verifier` when uncertainty matters.
7. **Active check:** exactly one fresh, answer-hidden production task. It must
   be non-isomorphic to any example whose answer was revealed; never ask the
   learner simply to restate the disclosed answer.

For state or graph modeling, teach future sufficiency as the correctness
criterion: the state must determine goal behavior and legal future outcomes.
Minimality is a separate preference. Redundant derivable fields may waste
space or obscure the invariant but do not make an otherwise consistent model
incorrect.

Use the headings `#### Why this node`, `#### Core rule`, `#### Derivation`,
`#### Worked example or contrast`, `#### Connection`, `#### Verification`, and
`#### Active check`. Immediately below the node heading, add a compact Obsidian
callout containing the current evidence state and what would advance it. Keep
the prose itself clean: no protocol commentary, process history, or teacher
instructions in the lesson.

After writing and rereading the node, the chat reply contains only a brief
current-node/path line, the exact note heading to read, and the active check
copied verbatim from the note. The sidecar records the learner's raw answer and
assessment and may link to the node heading rather than duplicating the lesson
prose. Writing the durable section is a prerequisite to the reply, not an
optional afterthought.

Before sending the teaching/check turn, reread the new section and fail the
preflight if any of these are false:

- all seven required elements are present;
- the response contains exactly one learner request;
- the CLI active check exactly matches the note's active check;
- the check's answer has not been revealed and cannot be copied from the
  worked example by changing labels;
- the current node has not been advanced without evidence;
- the node callout and learner-map `Current node` / `Status` agree;
- the lesson never describes recognition or scaffolded evidence as
  `demonstrated`;
- no child node is taught in the same turn.

Write the full seven-part unit once per node. Mark the node `introduced` after
teaching. If the active check fails, do not advance or repeat the whole unit:
append a concise `#### Reteach 1`, `#### Reteach 2`, and so on to the same node
with the exact error,
a materially different representation or example, and exactly one fresh
answer-hidden production check. End every reteach block with the literal line
`Active check:` followed by that fresh check. The newest reteach check replaces
the original as the canonical CLI prompt without overwriting prior history. If
the check succeeds, update the evidence
state in both the node callout and learner map, then stop; teach the next node
only on a later turn. Recognition-only success is at most `supported`.

Preserve every component already produced correctly and make the next check
request only the unresolved component. Repeat a full integrated response only
when cross-component consistency is itself the diagnosed error. After two
misses on the same construct, reduce the response schema and switch to a
concrete trace, table, diagram, typed signature, or executable example before
asking for another integration.

For subjects whose central reasoning is structural—especially graphs, BFS,
state machines, geometry, flows, and changing traces—visuals are default-on,
not an optional flourish. Include at least one verified Mermaid or SVG in each
taught node. When a miss concerns edges, transitions, reachability, state
splitting, or a trace, the first reteach should add a visual of that exact
relationship unless a table or executable trace is materially clearer. For a
graph-based active check, a visual may show only the given input topology and
labels; never reveal the composite state graph, path, or answer before the
attempt. Other subjects still use visuals only when they reduce working-memory
load. Give `learning_visualizer` a bounded, verified brief; keep domain
reasoning with the teacher and verifier.

Before every teaching/check reply, run the session validator with
`--require-active-check`. Copy the text between its `ACTIVE_CHECK_BEGIN` and
`ACTIVE_CHECK_END` markers verbatim into the CLI; do not retype it. Run the
validator again after every evidence-state update. A nonzero result blocks the
reply until the artifacts are repaired.

Update both artifacts as applicable, then stop for Farhan's response before
moving to another node.

## Phase 4 — Transfer and calibration

After the sink node:

- require a novel application without step-by-step scaffolding;
- verify it using a primary artifact, test, derivation, or counterexample;
- ask for a compressed explanation connecting the roots to the goal;
- create one retrieval prompt for 2–3 days later;
- create one interleaved or discriminating prompt for about a week later;
- reserve `demonstrated` for production or transfer evidence.

Update `Transfer and retrieval`, then close with
`Known / Inference / Unknown / To verify`, the retrieval dates, and the
smallest next action. Do not add a second study system or motivational filler.

After same-day transfer and explanation are assessed, set both artifact
statuses to `awaiting-retrieval`; use `complete` only after the required delayed
retrieval evidence is recorded. Run:

```bash
python3 .agents/skills/teach/scripts/validate_session.py "<session-note>" "<session-log>" --require-closeout
```

Repair every error before declaring the same-day loop closed. Do not use
`--require-active-check` after the session enters `awaiting-retrieval` or
`complete`.
