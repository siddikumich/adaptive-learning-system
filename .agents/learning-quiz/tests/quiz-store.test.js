import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { QuizError, QuizStore } from "../src/quiz-store.js";

const SECRET_CORRECT_VALUE = "answer_key_7f12f602";
const SECRET_WRONG_VALUE = "distractor_key_9e28b144";
const SECRET_EXPLANATION = "EXPLANATION_SECRET_105ab9f2";

async function fixture() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "learning-quiz-test-"));
  const vault = path.join(root, "vault");
  const state = path.join(root, "state");
  await fs.mkdir(path.join(vault, "Sessions"), { recursive: true });
  const logRelative = path.join("Sessions", "Topic — Session Log.md");
  const log = path.join(vault, logRelative);
  await fs.writeFile(
    log,
    [
      "---",
      "type: learning-session-log",
      "status: active",
      'session-note: "[[Topic]]"',
      'protocol-version: "2026-08-26.1"',
      "---",
      "",
      "# Topic — Session Log",
      "",
      "## Log",
      "",
    ].join("\n"),
    { mode: 0o600 },
  );
  const store = new QuizStore({ vaultRoot: vault, stateRoot: state });
  await store.ready;
  return {
    root,
    vault,
    state,
    log,
    logRelative,
    store,
    async cleanup() {
      await fs.rm(root, { recursive: true, force: true });
    },
  };
}

function registration(logRelative, overrides = {}) {
  return {
    session_log: logRelative,
    prompt: "Which operation produces net worth?",
    options: [
      { value: SECRET_CORRECT_VALUE, label: "Assets minus liabilities" },
      { value: SECRET_WRONG_VALUE, label: "Income minus expenses" },
    ],
    correct_value: SECRET_CORRECT_VALUE,
    explanation: SECRET_EXPLANATION,
    ...overrides,
  };
}

function assertNoRecursiveAnswerFields(value) {
  if (Array.isArray(value)) {
    value.forEach(assertNoRecursiveAnswerFields);
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    assert.doesNotMatch(key, /correct|answer|explanation|value/i);
    assertNoRecursiveAnswerFields(child);
  }
}

test("register and present recursively omit answer state and append an answer-hidden prompt", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);

  const registered = await env.store.register(registration(env.logRelative));
  assert.match(registered.quiz_id, /^qz_[A-Za-z0-9_-]{43}$/);
  assert.deepEqual(Object.keys(registered).sort(), ["quiz_id", "status"]);
  assertNoRecursiveAnswerFields(registered);

  const presented = await env.store.present(registered.quiz_id);
  assertNoRecursiveAnswerFields(presented);
  assert.deepEqual(presented.options[0], { token: "0", label: "I don't know" });
  assert.deepEqual(
    new Set(presented.options.slice(1).map(({ token }) => token)),
    new Set(["A", "B"]),
  );

  const publicBytes = JSON.stringify({ registered, presented });
  const logBytes = await fs.readFile(env.log, "utf8");
  for (const secret of [SECRET_CORRECT_VALUE, SECRET_WRONG_VALUE, SECRET_EXPLANATION]) {
    assert.equal(publicBytes.includes(secret), false);
    assert.equal(logBytes.includes(secret), false);
  }
  assert.equal(logBytes.includes("correct_value"), false);
  assert.equal(logBytes.includes("Assessment: pending"), true);
});

test("shuffle and display tokens survive a store restart", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const registered = await env.store.register(registration(env.logRelative));
  const first = await env.store.present(registered.quiz_id);

  const restarted = new QuizStore({ vaultRoot: env.vault, stateRoot: env.state });
  await restarted.ready;
  const second = await restarted.present(registered.quiz_id);
  assert.deepEqual(second, first);

  const logBytes = await fs.readFile(env.log, "utf8");
  assert.equal((logBytes.match(/learning-quiz:present:/g) ?? []).length, 1);
});

test("submit reveals feedback only after a response and identical resubmit is idempotent", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const registered = await env.store.register(registration(env.logRelative));
  const presented = await env.store.present(registered.quiz_id);
  const correctToken = presented.options.find(
    (option) => option.label === "Assets minus liabilities",
  ).token;
  const changedToken = correctToken === "A" ? "B" : "A";

  const first = await env.store.submit(registered.quiz_id, correctToken);
  assert.equal(first.is_correct, true);
  assert.equal(first.correct_token, correctToken);
  assert.equal(first.correct_label, "Assets minus liabilities");
  assert.equal(first.explanation, SECRET_EXPLANATION);
  const second = await env.store.submit(registered.quiz_id, correctToken.toLowerCase());
  assert.deepEqual(second, first);

  await assert.rejects(
    env.store.submit(registered.quiz_id, changedToken),
    (error) => error instanceof QuizError && error.code === "ALREADY_SUBMITTED",
  );
  const logBytes = await fs.readFile(env.log, "utf8");
  assert.equal((logBytes.match(/learning-quiz:submit:/g) ?? []).length, 1);
  assert.equal(logBytes.includes(SECRET_EXPLANATION), true);
  assert.equal(logBytes.includes(SECRET_CORRECT_VALUE), false);
  assert.equal(logBytes.includes(SECRET_WRONG_VALUE), false);
});

test("0 = I don't know is a valid, incorrect, idempotent response", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const registered = await env.store.register(registration(env.logRelative));
  await env.store.present(registered.quiz_id);
  const result = await env.store.submit(registered.quiz_id, "0");
  assert.equal(result.response_token, "0");
  assert.equal(result.selected_label, "I don't know");
  assert.equal(result.is_correct, false);
  assert.deepEqual(await env.store.submit(registered.quiz_id, "0"), result);
});

test("submit rejects stable values and requires presentation", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const registered = await env.store.register(registration(env.logRelative));
  await assert.rejects(
    env.store.submit(registered.quiz_id, "A"),
    (error) => error instanceof QuizError && error.code === "NOT_PRESENTED",
  );
  await env.store.present(registered.quiz_id);
  await assert.rejects(
    env.store.submit(registered.quiz_id, SECRET_CORRECT_VALUE),
    (error) => error instanceof QuizError && error.code === "INVALID_RESPONSE",
  );
});

test("registration rejects blank, duplicate, and unmatched stable option values", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const cases = [
    registration(env.logRelative, {
      options: [
        { value: "", label: "One" },
        { value: "two", label: "Two" },
      ],
      correct_value: "two",
    }),
    registration(env.logRelative, {
      options: [
        { value: "same", label: "One" },
        { value: "same", label: "Two" },
      ],
      correct_value: "same",
    }),
    registration(env.logRelative, { correct_value: "missing" }),
  ];
  for (const input of cases) {
    await assert.rejects(
      env.store.register(input),
      (error) => error instanceof QuizError && error.code === "INVALID_QUIZ",
    );
  }
});

test("state is atomic, private, and keyed by opaque quiz ID", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const registered = await env.store.register(registration(env.logRelative));
  const entries = await fs.readdir(env.state);
  assert.deepEqual(entries, [`${registered.quiz_id}.json`]);
  const stateStat = await fs.stat(env.state);
  const fileStat = await fs.stat(path.join(env.state, entries[0]));
  assert.equal(stateStat.mode & 0o777, 0o700);
  assert.equal(fileStat.mode & 0o777, 0o600);
  assert.equal(entries.some((entry) => entry.startsWith(".tmp-")), false);

  const privateState = await fs.readFile(path.join(env.state, entries[0]), "utf8");
  assert.equal(privateState.includes(SECRET_CORRECT_VALUE), true);
  assert.equal(privateState.includes(SECRET_EXPLANATION), true);
});

test("vault confinement rejects traversal, absolute paths, and symlink escapes", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const outside = path.join(env.root, "outside.md");
  await fs.writeFile(outside, await fs.readFile(env.log));
  const link = path.join(env.vault, "Sessions", "escape.md");
  await fs.symlink(outside, link);

  for (const sessionLog of ["../outside.md", outside, path.relative(env.vault, link)]) {
    await assert.rejects(
      env.store.register(registration(sessionLog)),
      (error) => error instanceof QuizError && error.code === "PATH_ESCAPE",
    );
  }
});

test("target Markdown must validate as a linked learning-session log", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const invalids = [
    ["missing-frontmatter.md", "# Ordinary note\n"],
    [
      "wrong-type.md",
      "---\ntype: note\nsession-note: '[[Topic]]'\nprotocol-version: '2026-08-26.1'\n---\n",
    ],
    ["missing-link.md", "---\ntype: learning-session-log\nprotocol-version: '2026-08-26.1'\n---\n"],
  ];
  for (const [name, contents] of invalids) {
    const relative = path.join("Sessions", name);
    await fs.writeFile(path.join(env.vault, relative), contents);
    await assert.rejects(
      env.store.register(registration(relative)),
      (error) => error instanceof QuizError && error.code === "INVALID_SESSION_LOG",
    );
  }
});

test("unsafe state permissions and state symlinks are rejected", async (t) => {
  const env = await fixture();
  t.after(env.cleanup);
  const registered = await env.store.register(registration(env.logRelative));
  const statePath = path.join(env.state, `${registered.quiz_id}.json`);
  await fs.chmod(statePath, 0o644);
  await assert.rejects(
    env.store.present(registered.quiz_id),
    (error) => error instanceof QuizError && error.code === "UNSAFE_STATE",
  );

  await fs.rm(statePath);
  await fs.symlink(env.log, statePath);
  await assert.rejects(
    env.store.present(registered.quiz_id),
    (error) => error instanceof QuizError && error.code === "UNSAFE_STATE",
  );
});
