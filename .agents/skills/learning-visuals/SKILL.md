---
name: learning-visuals
description: Create or revise an Obsidian-native Mermaid or SVG visual when a learning plan or teaching node is materially clearer through dependencies, flow, state, geometry, or spatial relationships. Use for lesson visuals, not decoration or ordinary prose.
---

# Create learning visuals

Represent one relationship that would otherwise consume working memory. The
visual is an explanation surface, not evidence; verify its underlying claims
against the lesson's sources.

## Choose the form

- Use inline Mermaid for dependency DAGs, flows, sequences, state transitions,
  trees, and compact comparisons.
- Use an SVG under `Attachments/Learning Visuals/` for coordinates, vectors,
  geometry, physical layouts, custom plots, or a changing algorithm trace that
  Mermaid cannot express clearly.
- Use prose, code, a table, or one equation when it is clearer than a picture.

Phase 2 always receives two editable Mermaid views: a compact learner-map
summary showing the evidence frontier, and the dependency plan. Keep the
learner-map table as the precise evidence record; the visual summarizes it
rather than replacing it.

Farhan prefers visual-first teaching when the subject itself is structural.
For graphs, BFS/DFS, state machines, flows, geometry, and changing algorithm
traces, include at least one explanatory visual in each taught node. When a
learner miss concerns edges, legal transitions, state splitting, reachability,
or trace order, prefer a new visual in the first reteach instead of repeating
the same prose. Additional visuals remain conditional for subjects where a
picture would not reduce working-memory load.

For graph-search questions, distinguish two possible pictures:

- **Input view:** the supplied rooms, cells, edges, colors, weights, or blocked
  structure. This may accompany an answer-hidden check when it contains only
  information already stated in the prompt.
- **Reasoning view:** the composite state graph, successor expansion, BFS
  layers, queue trace, or chosen path. Show this only after the learner has
  attempted the corresponding inference unless the visual is itself the input.

Do not draw a generic graph merely because the word “graph” appears. The
visual must expose the exact relationship being learned or diagnosed.

At planning time, record a lesson visual decision per teaching node: the
relationship to explain and its best representation. Learner maps and
prerequisite DAGs describe the learning process; they never count as the
explanatory visual for the concept. Deliver that visual in the node's
derivation or worked example, where the learner needs it. Examples of useful
briefs are a supplied graph with frontier layers, a changing queue trace, two
states with different legal futures, or a function plotted on specified axes.
These are examples, not required content for every lesson.

Use SVG for quantitative plots and spatial geometry that Mermaid cannot
express. The teacher supplies the formula/data, domain, coordinates, units,
and relevant assumptions; the visualizer must not invent values or turn an
illustrative example into an empirical claim. Use a table or code trace when
it exposes the mechanism more clearly. Record the node's `Visual` decision as
`embedded`, `alternative`, `not-needed`, or `incomplete`, with a concrete
reason. See the `$teach` contract for these callout fields and the staged
render/inspect/publish commands. Keep source and PNG together; only claim
inspection after looking at the rendered image.

The teacher owns the verified semantic brief. When `learning_visualizer` is
available, delegate only the formatting step to it with the exact nodes,
edges, directions, labels, values, desired form, and anything the visual must
not imply. Wait for its result. If it returns `NEEDS_BRIEF`, repair the brief
rather than letting it guess. The teacher validates the returned source and
writes it into the note or attachment; the read-only visualizer never
publishes.

If the named visualizer is unavailable, construct the source in the parent
session and label visual inspection incomplete when it cannot be performed.
Do not retry a failed visualizer repeatedly.

## Mermaid

Write the complete source in a fenced `mermaid` block inside the active note.
Show each diagram only once. For Mermaid, the inline block is the default
reader-facing view; rendered PNG/SVG copies are inspection artifacts, not
additional embeds. If an image-only fallback is needed, replace the inline
block with one inspected image and a plain editable-source link. Do not show
both representations of the same diagram. Keep distinct lesson diagrams.

Prefer `flowchart TD` for prerequisite depth and `flowchart LR` for short
processes. Keep node IDs stable and labels concise. Every arrow must have a
verified direction; explain non-obvious dependency edges directly below the
diagram.

Use a conservative Obsidian-compatible syntax subset. Every node ID must match
`n_[a-z0-9_]+`; never use a bare Mermaid keyword such as `graph`, `flowchart`,
`subgraph`, `end`, `class`, `classDef`, `style`, `click`, or a direction token
as an ID. Put each node declaration and edge on its own line. Keep punctuation
inside quoted labels, not IDs.

Avoid interactive links, initialization directives, decorative subgraphs, and
syntax that depends on a nonstandard Mermaid configuration. Do not install a
renderer merely to validate an ordinary diagram. When a local Mermaid parser
already exists, parse the exact source before writing it; a claimed validation
requires a successful parse. Otherwise apply the conservative syntax checks
above and label parser validation incomplete. Never publish source after a
known parse failure. If Obsidian reports a rendering failure, reproduce and
repair that exact failure.

## SVG

Create a complete, self-contained SVG with a clear `viewBox`, generous margins,
readable text, restrained color, and no scripts, event handlers,
`foreignObject`, external references, embedded data URLs, doctypes, or
entities. Preserve the editable `.svg` and embed it from the active note.

When local visual inspection is available, preview the SVG and check geometry,
labels, direction, clipping, contrast, and legibility before embedding it.

## Finish

Add one sentence below the visual naming the relationship Farhan should
inspect. Do not narrate every visible element. The `learning_verifier`, not the
visualizer, audits domain semantics when an incorrect arrow, scale, state, or
invariant would teach the wrong model.
