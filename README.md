# Adaptive Learning System

An Obsidian and Codex workflow for learning difficult material through short,
source-grounded sessions. It turns a broad goal into a dependency map, teaches
one ready concept at a time, records evidence of an attempt, and schedules
later retrieval.

The repository is a reusable system, not a collection of learner notes. It
contains no sessions, responses, recruiting materials, or vault state.

## What is here

- A `$teach` skill that maps relevant prerequisites, plans a session, and
  validates the linked learner note and session log.
- An answer-hidden local MCP quiz server for multiple-choice checks.
- A `$retrieve` skill for scheduled, answer-hidden follow-up retrieval.
- A Mermaid/SVG pipeline that renders and records inspected lesson visuals.
- Templates, source-integrity rules, and narrow researcher/verifier/visualizer
  roles for Codex.

The protocol is designed to make work inspectable. Its structural validators
check artifact consistency; they do not establish that a lesson is pedagogically
effective or that a learner has mastered a subject.

## Use it in an Obsidian vault

`manifest.txt` lists every file intended to be copied into a vault. Start with
a dry run:

```bash
rsync -avni --files-from=manifest.txt ./ /absolute/path/to/vault/
```

Apply the same copy only after reviewing the dry run and the repository diff:

```bash
rsync -avi --files-from=manifest.txt ./ /absolute/path/to/vault/
```

To update this repository from a vault, reverse the source and destination and
again use the dry run first. These commands can overwrite files in the
manifest.

## Local dependencies

The quiz server requires Node 20 or later. The visual pipeline requires Node 22
or later.

```bash
npm --prefix .agents/learning-quiz ci
npm --prefix .agents/skills/learning-visuals ci
```

To use the quiz server, configure it as a project-scoped STDIO MCP server in
the target vault's `.codex/config.toml`:

```toml
[mcp_servers.learning_quiz]
command = "node"
args = ["src/server.js"]
cwd = "/absolute/path/to/vault/.agents/learning-quiz"
startup_timeout_sec = 10

[mcp_servers.learning_quiz.env]
LEARNING_QUIZ_VAULT_ROOT = "/absolute/path/to/vault"
LEARNING_QUIZ_STATE_ROOT = "/absolute/path/to/vault/.agents/learning-quiz/.state"
```

Restart Codex after changing its configuration, then check the server with
`codex mcp list`.

## Tests

```bash
npm --prefix .agents/learning-quiz test
npm --prefix .agents/skills/learning-visuals test
npm --prefix .agents/skills/learning-visuals run test:python
python3 -m unittest discover -s .agents/skills/teach/tests -p 'test_*.py'
python3 -m unittest discover -s .agents/skills/retrieve/tests -p 'test_*.py'
```

To validate a real session after active retrieval:

```bash
python3 .agents/skills/teach/scripts/validate_session.py \
  "Session Note.md" "Session Note — Session Log.md" --require-active-check
```

The portable design and protocol are linked from [the learning system
overview](Learning%20System.md).

## Privacy

Keep learner sessions, answer data, source material with access restrictions,
and personal vault notes outside this repository. The quiz server stores its
state locally under the configured vault path.
