---
name: teach
description: Run the explicit `$teach` adaptive, source-grounded learning-session protocol in the Obsidian vault. Use only when Farhan invokes `$teach`; ordinary requests for explanations, advice, research, planning, or practical artifacts must not activate this workflow.
---

# Teach through productive struggle

The outcome is independent performance: Farhan can retrieve, explain, apply,
test, and adapt the subject on a new problem. Codex is the teacher, interface,
and feedback coordinator; inspected artifacts remain the sources of truth.

Current protocol version: `2026-08-26.1`.

Behavior revision: `2026-09-05` — map the full goal before planning and deliver
concept visuals inside lessons. New sessions declare `diagnostic-coverage: "1"`
and `lesson-visuals: "1"`; these are additive checks, not a retrieval migration.
On resume, preserve prior evidence and inventory untested strands before
claiming a complete diagnostic. Never fabricate coverage to upgrade an old note.

Read `Learning System.md` and `AI Learning Contract.md` before a substantial
session. Preserve course policies and source constraints supplied by Farhan.

## Activation boundary

Run this workflow only when Farhan explicitly invokes `$teach`. Do not infer
consent from a desire to learn, a knowledge gap, a difficult subject, or a
request that mixes explanation with a practical deliverable. Handle those
requests directly with the smallest useful artifact or answer unless Farhan
separately invokes `$teach`.

Once invoked, the approved learning scope is enough authority to advance
through its diagnostic. Do not ask for permission between already scoped
probes or use a separate turn merely to say that more questions remain. If
Farhan pauses, redirects, or withdraws `$teach`, stop the protocol and preserve
the current evidence state without continuing automatically.

## Invariants

- Maximize subject-matter struggle: prediction, retrieval, construction,
  explanation, debugging, discrimination, and transfer.
- Minimize logistical struggle: maintain the session note, sources, learner
  map, plan, and retrieval dates without asking Farhan to format them. After
  same-day closeout, `$retrieve` owns retrieval state changes.
- Ask one learner-facing question or request per turn. Never rush across
  multiple dependency nodes.
- During diagnosis, require one atomic, scorable response per turn. Do not
  bundle several outputs into one prompt merely to collect more evidence.
- Keep initiative within that one-request limit. After assessing a diagnostic
  response, present the next necessary atomic probe in the same reply. If
  Farhan asks for diagnostic status, answer briefly and include the next probe
  unless he asked to pause or redirect. Never require a redundant `continue`,
  `ready`, or `go ahead` turn.
- Treat multiple choice as efficient recognition evidence, not mastery.
- Advance only from observable evidence, never from “I get it” or confidence.
- Keep facts, inferences, and unknowns distinct. Cite primary or authoritative
  artifacts near consequential claims.
- Probe only prerequisites that the stated independent capability depends on.
- Calibrate challenge instead of maximizing it. Select a nontrivial atomic task
  that remains reachable from demonstrated parent knowledge and the current
  node, with at least one plausible first move available to Farhan. If success
  depends on multiple unsupported nodes, split the task; if it can be completed
  mechanically from disclosed material, increase its discrimination.
- Give task-relevant feedback at the earliest point compatible with answer-key
  isolation and diagnostic validity. Feedback identifies the observed output,
  the exact gap or successful move, and the next adjustment; generic praise is
  not feedback. When coupled diagnostic strands require deferred correction,
  preserve that boundary and give the feedback when the bracket closes.
- Treat flow-compatible conditions as task-design heuristics, not as the
  session outcome or a promise to induce flow. Never use reported absorption,
  enjoyment, effortlessness, or confidence as learner evidence; advancement
  still requires observable production, verification, and transfer.
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
`Templates/Learning Session Log Template.md`. Prefer the deterministic factory
so reciprocal links, dates, and the current protocol cannot drift:

```bash
python3 .agents/skills/teach/scripts/session_factory.py "<session title>" \
  --output-dir "<note directory>" --created "<YYYY-MM-DD>" \
  --source-note "<existing source note when known>"
```

When resuming a legacy session
whose main note contains `## Session log`, move that section losslessly into
the linked sidecar before continuing; do not summarize away learner-authored
responses. New sessions record protocol `2026-08-26.1` in both artifacts. Do
not silently rewrite a real or synthetic `2026-08-25.6` session or sidecar to
the new retrieval schema; `$retrieve` owns compatible legacy handling.

Write each diagnostic question into the sidecar before presenting it in chat.
For a quiz-tool item, `present_quiz` performs this write; do not manually add a
second copy.
After Farhan replies, record the response there verbatim. Record the assessment
immediately unless feedback must remain deferred; in that case write
`assessment deferred` and update it when the diagnostic bracket closes. At
phase boundaries, update the structured sections of the session note instead
of treating the sidecar as the learner model. Preserve all learner-authored
content.

Keep pending answer keys and assessor notes teacher-facing. Never disclose
them in commentary, progress updates, learner-facing recaps, or the prompt
itself. Operational updates should not interrupt the diagnostic loop; batch
reviewable vault commits at phase boundaries unless an error or pause makes an
earlier checkpoint useful.

### Answer-hidden single-select boundary

When the local `register_quiz`, `present_quiz`, and `submit_quiz` tools are
available, use them for every keyed single-select diagnostic item:

1. Give `learning_verifier` only the construct, desired difficulty, inspected
   sources, contamination constraints, and vault-relative session-log path.
   The verifier authors and audits the question, parallel options, key, and
   explanation in its own context, calls `register_quiz`, and returns only its opaque `quiz_id`;
   it must not return the key or explanation. Do not author a proposed key in
   the parent and then claim it was hidden from that parent. This separates
   the stored answer payload; it cannot prevent a capable teacher from solving
   the displayed question. If auditing a parent-authored item, label that
   narrower boundary accurately in the sidecar.
2. In the parent, call `present_quiz` with that `quiz_id`. Present its sanitized
   `prompt`, displayed token/label options (including `0. I don't know`), and
   `response_instruction` exactly, with no teaching prose, answer hint, stable
   values, key, or explanation. Do not reconstruct or reshuffle the payload.
3. After Farhan replies with one displayed token, call `submit_quiz` with the
   same `quiz_id` and `response_token`. Only then may correctness, the expected
   answer, or the registered explanation enter parent context or the sidecar.
   Preserve contamination and deferred-feedback rules for any later probe.

Do not call `register_quiz` in the learner-facing parent when an independent
verifier can do so: tool-output isolation is the point of this boundary. If
the tools or verifier registration are unavailable, do not claim answer-key
isolation. Prefer an atomic constructed response; if a keyed item is genuinely
necessary, label isolation incomplete in the sidecar and keep the key out of
learner-facing text by best effort.

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
- In delayed retrieval, `$retrieve` finds and selects due sessions, reveals one
  answer-hidden prompt in the CLI, and records the response, assessment, and
  scheduling event in the sidecar. The main note remains the canonical reading
  surface; do not put raw delayed-retrieval evidence there.

If Farhan explicitly wants to read in the CLI, paste the exact lesson section
from the note rather than composing a second version. Never require an answer
in Obsidian; accepting answers in the CLI keeps adaptive turn-taking reliable.

Use Obsidian-native MathJax delimiters in every learner-facing note: `$...$`
for inline mathematics and `$$` on separate lines for display mathematics.
Never use `\(...\)` or `\[...\]` as Markdown math delimiters; Obsidian exposes
those as raw text. LaTeX environments such as `\begin{cases}` belong inside a
`$$` block. Treat equations as lesson content, not as Mermaid or SVG visuals.

## Phase 1 — Source and probe

Before learner-facing orientation, draft the candidate probe map and audit the
existing conversation for answer contamination. Orientation may explain the
goal, privacy boundary, process, and approximate probe budget, but it must not
teach or strongly cue a claim that a planned diagnostic is supposed to
measure. If the conversation has already disclosed such a claim, do not use a
recognition item for prior-knowledge evidence; use a fresh non-isomorphic
production task when that boundary still matters, or label the evidence
`post-instruction`.

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

Before the first probe, use the source pack and requested capability to list
every goal-relevant strand under `### Diagnostic coverage` in the learner map.
Use exactly: `Strand | Goal relevance | Evidence | Boundary | Coverage | Next action`.
Give each strand a concrete connection to the goal. Preview this inventory in
the note and give its link once; do not disclose diagnostic answers, example
solutions, or keys. Present questions one at a time, adapting to each answer.

Cover breadth before spending the budget on depth: get a meaningful response
on each relevant strand, then revisit uncertain or consequential boundaries.
A single item can cover several strands only when the actual response exposes
each; bundled recognition is not independent proof of every component.
For an implementation goal, the inventory must consider modeling, mechanism,
correctness conditions, implementation/debugging, cost, and unfamiliar
application; retain only strands justified by the sources and actual goal.
These are examples, not a universal syllabus for every topic.

Map each goal-relevant strand adaptively:

1. Establish a floor with one meaningful success.
2. Jump substantially harder until a miss or honest “I don't know” establishes
   a ceiling.
3. Narrow the bracket with a fresh item that distinguishes a slip, isolated
   gap, and systematic misconception.
4. Stop probing that strand when its boundary is characterized within the
   goal. Continue to the other strands even when the first teaching node is clear.

Floor, ceiling, and confirmation are evidence roles, not a mandatory three
questions for every strand. Reuse valid evidence; do not repeat easy items to
inflate the count. Update coverage after every response:

- `unprobed`: no usable response;
- `floor-only`: success, but the relevant upper boundary is still untested;
- `ceiling-only`: a miss or uncertainty without an established floor or a
  confirmed entry-level gap; probe a simpler case before concluding;
- `bracketed`: log-linked success and miss or honest uncertainty characterize
  the boundary, with a slip distinguished where consequential;
- `bounded`: the goal's upper level was demonstrated without needing to fail
  at an irrelevant harder task, or a confirmed entry-level gap leaves no
  demonstrated floor. State which limit applies; do not invent a floor/ceiling;
- `deferred`: explicitly untested or unresolved, with a reason and a concrete
  next probe or narrower scope. Never describe this as fully mapped.

The Evidence cell links to actual sidecar question/response anchors. Boundary
states what those responses establish and leave uncertain; Next action is
nonblank, including `none — boundary mapped` when appropriate.
Write `Diagnostic scope: full-goal` below the table once all strands are
mapped, or `Diagnostic scope: partial` whenever any strand is deferred.
Set the diagnostic budget from topic scope and observed answer pattern:

- narrow skill or definition: usually 4–7 learner-facing probes;
- typical technical concept: usually 8–14;
- broad, prerequisite-heavy topic: 12–18, preferably split into smaller goals.

There is no question-count minimum. Four questions can suffice for a narrow
goal only if their evidence covers its actual strands. Consistent success
means escalate within scope; a first miss means characterize it, not end the
whole diagnostic. Stop only when all relevant strands are `bracketed` or
`bounded`, or explicitly `deferred` with the remaining uncertainty visible.
Choosing the first teaching node is not the completion criterion.
Do not exceed 18 probes in one sitting without Farhan's explicit agreement. If
important strands remain unknown at the cap, mark them `deferred`, explain
that the diagnostic is partial, and include their next probes in the Phase 2
approval request. The learner can approve a provisional path, narrow the goal,
or continue mapping. A requested pause preserves the ledger without implying
completion. Do not silently defer strands merely to start teaching sooner.

Use this diagnostic funnel:

1. Start each strand with one broad, answer-isolated single-select
   multiple-choice item through the quiz-tool boundary above. Use parallel
   bare answer claims, diagnostic distractors, varied key position,
   `I don't know`, and LaTeX where notation benefits from it. Ask for one
   displayed token only.
2. Adapt with harder or easier single-select items until the likely boundary
   is narrow. Trace, code, and application scenarios may be multiple choice;
   present complete candidate outcomes rather than asking for several fields.
3. At a consequential or uncertain boundary, require one atomic constructed
   response that recognition cannot supply: one prediction, queue/state,
   invariant, explanation sentence, code fragment, derivation step, or model.
   Never request a multipart checklist. Split distinct constructs across turns
   only when each result could change the full-goal learner map or teaching plan.
4. When the goal requires application and it could change the plan, finish
   with one cold, unfamiliar integration probe. Request only the smallest
   discriminating output—such as the representation, algorithm choice with one
   rationale, invariant, or next move—not a full solution by default.

During Phase 1, never request a full contract such as
`vertex | transitions | source | goal`; select exactly one component whose
answer can refine the full-goal learner map. Reserve integration of the complete
session goal for Phase 4; a Phase 3 check may integrate only the components
that define its current node.

Multiple-choice success is at most `supported`. An unscaffolded constructed
response may demonstrate only the exact construct it exposes; do not
generalize it to implementation or transfer. The cold integration probe is a
diagnostic snapshot, not the final Phase 4 transfer proof.

Defer corrective feedback while any coupled strand remains under diagnosis.
If feedback is revealed early, label later evidence `post-instruction` and use
a non-isomorphic item before treating it as diagnostic evidence.
If a learner-facing recap, progress update, example, or prior explanation
reveals a pending item's answer, invalidate the item immediately. Record the
contamination, do not score it, and replace it only when the result could still
change the full-goal learner map.

Maintain the note's learner map with:

- verified floor and observed ceiling;
- misconception or uncertainty;
- evidence type: recognition, explanation, trace, construction,
  implementation, or transfer;
- status: `unknown`, `introduced`, `supported`, or `demonstrated`.

Confidence is learner-reported metadata, never proof.

## Phase 2 — Verify and plan

Audit the diagnostic inventory against every clause of the independent
capability and the inspected sources. Every relevant strand must be present;
`unprobed`, `floor-only`, or `ceiling-only` blocks a completed diagnostic. A plan with `deferred`
strands is provisional and must say so in the approval request. Do not let a
clean diagram conceal unknown implementation, correctness, or transfer ability.

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
2. approach and why it fits this learner and outcome, including why the first
   node is reachable but nontrivial and which task-relevant signal will show
   progress or error;
3. an editable Mermaid dependency `flowchart` with stable, readable node IDs;
4. edge rationales and sources;
5. planned transfer task and delayed-retrieval structure. Author the exact
   prompts only at Phase 4, after the session's transfer evidence is known.

Also write a compact `### Lesson visual plan` table under the dependency plan:
`Node | Relationship to explain | Form`. Decide on a concept graph, annotated
trace, plot/chart, spatial SVG, table, or a reason no visual helps for each
planned teaching node. A learner map or prerequisite DAG never satisfies a
lesson's explanatory-visual need. Derive plotted values from an inspected
source, formula, or executable calculation, with axes, units, domain, and any
illustrative assumptions explicit. Do not invent measured data.

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
inference. Calibrate this prompt to the evidence frontier: it may stretch the
demonstrated floor, but it must not silently require a second unsupported node.

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
   learner simply to restate the disclosed answer. Keep it nontrivial but
   reachable from the demonstrated parents plus this taught node; split it if
   another unsupported dependency would determine the result.

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

Execute the lesson visual plan inside `Derivation` or `Worked example or
contrast`, beside the mechanism it explains. Planning maps do not count.
Add a line to each node's status callout using one of these exact forms:

- `> **Visual:** embedded — <relationship the learner should inspect>`:
  include a locally rendered PNG in this node, plus its editable source link;
- `> **Visual:** alternative — <why the actual table/code trace/equation here is clearer>`;
- `> **Visual:** not-needed — <why this node has no useful visual relationship>`;
- `> **Visual:** incomplete — <specific rendering/inspection blocker and fallback>`.

For a structural node, use `embedded` unless a concrete alternative is
clearer or tooling is blocked. Never use `not-needed` merely because the
dependency plan already has diagrams. For a plotted relationship, request SVG
with explicit coordinates, axes, units, domain, and source-grounded values;
Mermaid is not a substitute for a quantitative plot. The verifier checks
whether the chosen representation explains this node and preserves the
answer boundary. The deterministic validator checks declared delivery and
local embed presence, not visual relevance or mathematical correctness.

Every visual used for instruction or planning must pass the local staged
render-and-inspect boundary from `$learning-visuals`. After the visualizer
returns editable `.mmd` or `.svg` source, the parent must:

1. stage it with
   `node .agents/skills/learning-visuals/scripts/visual_pipeline.mjs stage`
   using `--kind`, absolute `--source`, a filename-safe `--name`, and
   `--workspace /absolute/path/to/vault`;
2. inspect the returned `previewPath` with `view_image` and revise/re-stage if
   parsing, geometry, labels, direction, clipping, contrast, or legibility is
   wrong;
3. publish only the inspected bytes with the returned `receiptPath` and
   `previewSha256` via `publish --receipt ... --approved-preview-sha256 ...
   --workspace /absolute/path/to/vault`;
4. inspect the returned final `pngPath` with `view_image`, then embed that PNG
   in the lesson and link the published editable source beside it.

Fail closed: when staging, either `view_image` inspection, receipt approval, or
publication is unavailable or fails, do not publish or describe the visual as
verified. Keep the lesson moving with prose, code, a table, or an equation when
possible, and record visual inspection incomplete in the sidecar.

Before every teaching/check reply, run the session validator with
`--require-active-check`. Copy the text between its `ACTIVE_CHECK_BEGIN` and
`ACTIVE_CHECK_END` markers verbatim into the CLI; do not retype it. Run the
validator again after every evidence-state update. A nonzero result blocks the
reply until the artifacts are repaired.

Update both artifacts as applicable, then stop for Farhan's response before
moving to another node.

## Phase 4 — Transfer and retrieval handoff

After the sink node:

- require a novel application without step-by-step scaffolding;
- verify it using a primary artifact, test, derivation, or counterexample;
- set `source-note` to an existing, resolvable Markdown source/topic note;
- ask for a compressed explanation connecting the roots to the goal;
- author both exact, answer-hidden production prompts under the canonical
  `## Transfer and retrieval` → `### Delayed retrieval` subsection: one
  `#### Initial retrieval prompt` and one
  `#### Interleaved retrieval prompt`. The latter must require discrimination
  from a relevant confusable alternative; neither prompt may reveal its answer;
- reserve `demonstrated` for production or transfer evidence.

At same-day local closeout in `America/Detroit`, set the session-note
frontmatter to `retrieval-schema: "1"`, `retrieval-enabled: true`,
`retrieval-timezone: America/Detroit`, `retrieval-started: <local closeout
date>`, `retrieval-stage: initial`, `retrieval-required-passes: 2`,
`retrieval-passes: 0`, and `next-retrieval: <local closeout date + 2 calendar
days>`. In `### Delayed retrieval`, write the matching current stage and next
retrieval date, plus a completion criterion: two committed delayed passes in
order, initial then interleaved, strictly after `retrieval-started`.

The exact +2-day initial interval, +5-day interval after an initial pass,
+2-day retry after a partial response, and +1-day retry after a miss are
transparent product defaults. They are not claims of scientifically universal
optimal intervals. Evidence supports retrieval practice and spacing; use
interleaving only where a qualified discrimination task fits the material.

Update `Transfer and retrieval`, retaining the novel application and its
result/verification. Close the section with `Known / Inference / Unknown / To
verify` and the smallest next action under a separate `### Evidence boundary`
heading after the prompt subsection. Do not add raw retrieval attempts,
assessments, or history to the main note: record them in the sidecar.

After same-day transfer and explanation are assessed, set both artifact
statuses to `awaiting-retrieval`. `$retrieve` owns all subsequent retrieval
state changes, including rescheduling and the eventual `complete` status; do
not mark a session complete from `$teach`. Run:

```bash
python3 .agents/skills/teach/scripts/validate_session.py "<session-note>" "<session-log>" --require-closeout
```

Repair every error before declaring the same-day loop closed. Do not use
`--require-active-check` after the session enters `awaiting-retrieval` or
`complete`.
