import {
  constants,
  createReadStream,
  promises as fs,
} from "node:fs";
import { randomBytes, randomInt } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseDocument } from "yaml";

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(MODULE_DIR, "..");
const DEFAULT_VAULT_ROOT = path.resolve(PROJECT_ROOT, "..", "..");
const DEFAULT_STATE_ROOT = path.join(PROJECT_ROOT, ".state");

const QUIZ_ID_RE = /^qz_[A-Za-z0-9_-]{43}$/;
const STABLE_VALUE_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
const PROTOCOL_RE = /^\d{4}-\d{2}-\d{2}\.\d+$/;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

export class QuizError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "QuizError";
    this.code = code;
  }
}

function fail(code, message) {
  throw new QuizError(code, message);
}

function opaqueId(prefix) {
  return `${prefix}${randomBytes(32).toString("base64url")}`;
}

function parseLearningSessionLog(markdown) {
  const match = markdown.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  if (!match) fail("INVALID_SESSION_LOG", "The session log needs YAML frontmatter.");

  const document = parseDocument(match[1], { strict: true, uniqueKeys: true });
  if (document.errors.length > 0) {
    fail("INVALID_SESSION_LOG", "The learning-session log has invalid YAML frontmatter.");
  }
  let metadata;
  try {
    metadata = document.toJS({ maxAliasCount: 0 });
  } catch {
    fail("INVALID_SESSION_LOG", "The learning-session log has unsafe YAML frontmatter.");
  }
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
    fail("INVALID_SESSION_LOG", "The learning-session log frontmatter must be a mapping.");
  }
  const type = metadata.type;
  const sessionNote = metadata["session-note"];
  const protocolVersion = metadata["protocol-version"];
  if (type !== "learning-session-log") {
    fail("INVALID_SESSION_LOG", "The target is not a learning-session log.");
  }
  if (typeof sessionNote !== "string" || !sessionNote.trim()) {
    fail("INVALID_SESSION_LOG", "The learning-session log is missing session-note.");
  }
  if (typeof protocolVersion !== "string" || !PROTOCOL_RE.test(protocolVersion)) {
    fail("INVALID_SESSION_LOG", "The learning-session log has an invalid protocol-version.");
  }
  return { type, sessionNote, protocolVersion };
}

function isInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== "..");
}

async function rejectSymlinkComponents(root, candidate) {
  const relative = path.relative(root, candidate);
  const parts = relative.split(path.sep).filter(Boolean);
  let cursor = root;
  for (const part of parts) {
    cursor = path.join(cursor, part);
    let stat;
    try {
      stat = await fs.lstat(cursor);
    } catch {
      fail("INVALID_SESSION_LOG", "The learning-session log does not exist.");
    }
    if (stat.isSymbolicLink()) {
      fail("PATH_ESCAPE", "Symbolic links are not allowed in a session-log path.");
    }
  }
}

async function readBoundedFile(filePath) {
  const stat = await fs.stat(filePath);
  if (!stat.isFile()) fail("INVALID_SESSION_LOG", "The session-log path is not a file.");
  if (stat.size > MAX_FILE_BYTES) fail("INVALID_SESSION_LOG", "The session log is too large.");
  return fs.readFile(filePath, "utf8");
}

function normalizeRelativeLogPath(value) {
  if (typeof value !== "string" || value.length === 0 || value.length > 1024) {
    fail("INVALID_SESSION_LOG", "session_log must be a non-empty relative path.");
  }
  if (value.includes("\0") || path.isAbsolute(value)) {
    fail("PATH_ESCAPE", "session_log must stay inside the vault.");
  }
  return path.normalize(value);
}

function normalizeRegistration(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    fail("INVALID_QUIZ", "Quiz registration is invalid.");
  }
  const prompt = typeof input.prompt === "string" ? input.prompt.trim() : "";
  const explanation =
    typeof input.explanation === "string" ? input.explanation.trim() : "";
  if (!prompt || prompt.length > 10_000) {
    fail("INVALID_QUIZ", "prompt must contain 1 to 10,000 characters.");
  }
  if (!explanation || explanation.length > 20_000) {
    fail("INVALID_QUIZ", "explanation must contain 1 to 20,000 characters.");
  }
  if (!Array.isArray(input.options) || input.options.length < 2 || input.options.length > 20) {
    fail("INVALID_QUIZ", "options must contain 2 to 20 choices.");
  }

  const seen = new Set();
  const options = input.options.map((option) => {
    if (!option || typeof option !== "object" || Array.isArray(option)) {
      fail("INVALID_QUIZ", "Every option must have a label and stable value.");
    }
    const label = typeof option.label === "string" ? option.label.trim() : "";
    const stableValue = typeof option.value === "string" ? option.value.trim() : "";
    if (!label || label.length > 2_000) {
      fail("INVALID_QUIZ", "Every option label must contain 1 to 2,000 characters.");
    }
    if (!STABLE_VALUE_RE.test(stableValue)) {
      fail("INVALID_QUIZ", "Every option value must be a non-blank stable identifier.");
    }
    if (seen.has(stableValue)) fail("INVALID_QUIZ", "Option values must be unique.");
    seen.add(stableValue);
    return { label, stableValue };
  });

  const correctValue =
    typeof input.correct_value === "string" ? input.correct_value.trim() : "";
  if (!seen.has(correctValue)) {
    fail("INVALID_QUIZ", "correct_value must match exactly one option value.");
  }

  return {
    prompt,
    explanation,
    options,
    correctValue,
    sessionLog: normalizeRelativeLogPath(input.session_log),
  };
}

function shuffle(items) {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const other = randomInt(index + 1);
    [result[index], result[other]] = [result[other], result[index]];
  }
  return result;
}

function displayToken(index) {
  // Twenty options are allowed, so a single stable A–T token is sufficient.
  return String.fromCharCode("A".charCodeAt(0) + index);
}

function publicPresentation(state) {
  return {
    quiz_id: state.quizId,
    status: state.submission ? "submitted" : "presented",
    prompt: state.prompt,
    options: [
      { token: "0", label: "I don't know" },
      ...state.options.map((option, index) => ({
        token: displayToken(index),
        label: option.label,
      })),
    ],
    response_instruction: "Reply with exactly one displayed token.",
  };
}

function publicSubmission(state) {
  return structuredClone(state.submission.publicResult);
}

function marker(kind, quizId) {
  return `<!-- learning-quiz:${kind}:${quizId} -->`;
}

function blockquote(text) {
  return text
    .split(/\r?\n/)
    .map((line) => `> ${line}`)
    .join("\n");
}

function presentationMarkdown(state) {
  const lines = [
    "",
    `### Diagnostic quiz — ${state.quizId}`,
    "",
    marker("present", state.quizId),
    "",
    "Prompt presented:",
    "",
    blockquote(state.prompt),
    ">",
    "> 0. I don't know",
  ];
  state.options.forEach((option, index) => {
    lines.push(`> ${displayToken(index)}. ${option.label}`);
  });
  lines.push("", "Assessment: pending", "");
  return lines.join("\n");
}

function submissionMarkdown(state) {
  const result = state.submission.publicResult;
  return [
    "",
    marker("submit", state.quizId),
    "",
    `Learner response: \`${result.response_token}\` — ${result.selected_label}`,
    "",
    `Assessment: ${result.is_correct ? "Correct." : "Incorrect."}`,
    "",
    `Expected answer: \`${result.correct_token}\` — ${result.correct_label}`,
    "",
    `Explanation: ${result.explanation}`,
    "",
  ].join("\n");
}

async function fileContains(filePath, needle) {
  return new Promise((resolve, reject) => {
    let carry = "";
    const stream = createReadStream(filePath, { encoding: "utf8" });
    stream.on("data", (chunk) => {
      const combined = carry + chunk;
      if (combined.includes(needle)) {
        stream.destroy();
        resolve(true);
        return;
      }
      carry = combined.slice(-needle.length + 1);
    });
    stream.on("end", () => resolve(false));
    stream.on("close", () => {
      // close follows destroy after a match; the promise is already resolved.
    });
    stream.on("error", reject);
  });
}

export class QuizStore {
  constructor({ vaultRoot, stateRoot } = {}) {
    this.vaultRoot = path.resolve(vaultRoot ?? process.env.LEARNING_QUIZ_VAULT_ROOT ?? DEFAULT_VAULT_ROOT);
    this.stateRoot = path.resolve(stateRoot ?? process.env.LEARNING_QUIZ_STATE_ROOT ?? DEFAULT_STATE_ROOT);
    this.ready = this.#initialize();
    this.mutations = Promise.resolve();
  }

  async #initialize() {
    await fs.mkdir(this.stateRoot, { recursive: true, mode: 0o700 });
    const stat = await fs.lstat(this.stateRoot);
    if (stat.isSymbolicLink() || !stat.isDirectory()) {
      fail("UNSAFE_STATE", "Quiz state must be a private directory, not a symbolic link.");
    }
    await fs.chmod(this.stateRoot, 0o700);
    this.realStateRoot = await fs.realpath(this.stateRoot);

    const vaultStat = await fs.lstat(this.vaultRoot);
    if (vaultStat.isSymbolicLink() || !vaultStat.isDirectory()) {
      fail("UNSAFE_VAULT", "The configured vault root must be a real directory.");
    }
    this.realVaultRoot = await fs.realpath(this.vaultRoot);
  }

  async #exclusiveMutation(callback) {
    const next = this.mutations.then(callback, callback);
    this.mutations = next.catch(() => {});
    return next;
  }

  #statePath(quizId) {
    if (!QUIZ_ID_RE.test(quizId)) fail("QUIZ_NOT_FOUND", "Unknown quiz identifier.");
    const candidate = path.join(this.realStateRoot, `${quizId}.json`);
    if (!isInside(this.realStateRoot, candidate)) fail("UNSAFE_STATE", "Unsafe quiz state path.");
    return candidate;
  }

  async #resolveSessionLog(relativeValue) {
    await this.ready;
    const relative = normalizeRelativeLogPath(relativeValue);
    const candidate = path.resolve(this.realVaultRoot, relative);
    if (!isInside(this.realVaultRoot, candidate)) {
      fail("PATH_ESCAPE", "session_log must stay inside the vault.");
    }
    await rejectSymlinkComponents(this.realVaultRoot, candidate);
    const realCandidate = await fs.realpath(candidate);
    if (!isInside(this.realVaultRoot, realCandidate)) {
      fail("PATH_ESCAPE", "session_log resolved outside the vault.");
    }
    const markdown = await readBoundedFile(realCandidate);
    parseLearningSessionLog(markdown);
    return { path: realCandidate, relative: path.relative(this.realVaultRoot, realCandidate) };
  }

  async #readState(quizId) {
    await this.ready;
    const statePath = this.#statePath(quizId);
    let stat;
    try {
      stat = await fs.lstat(statePath);
    } catch {
      fail("QUIZ_NOT_FOUND", "Unknown quiz identifier.");
    }
    if (stat.isSymbolicLink() || !stat.isFile()) fail("UNSAFE_STATE", "Unsafe quiz state entry.");
    if ((stat.mode & 0o077) !== 0) fail("UNSAFE_STATE", "Quiz state permissions are not private.");
    if (stat.size > 1024 * 1024) fail("UNSAFE_STATE", "Quiz state entry is too large.");
    let state;
    try {
      state = JSON.parse(await fs.readFile(statePath, "utf8"));
    } catch {
      fail("UNSAFE_STATE", "Quiz state is invalid.");
    }
    if (state.version !== 1 || state.quizId !== quizId || !Array.isArray(state.options)) {
      fail("UNSAFE_STATE", "Quiz state is invalid.");
    }
    return state;
  }

  async #writeState(state, { createOnly = false } = {}) {
    await this.ready;
    const destination = this.#statePath(state.quizId);
    if (createOnly) {
      try {
        await fs.lstat(destination);
        fail("UNSAFE_STATE", "Quiz identifier collision.");
      } catch (error) {
        if (error instanceof QuizError) throw error;
        if (error.code !== "ENOENT") throw error;
      }
    }

    const temp = path.join(
      this.realStateRoot,
      `.tmp-${process.pid}-${randomBytes(16).toString("hex")}`,
    );
    const handle = await fs.open(
      temp,
      constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY,
      0o600,
    );
    try {
      await handle.writeFile(`${JSON.stringify(state)}\n`, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    await fs.chmod(temp, 0o600);
    try {
      await fs.rename(temp, destination);
      const dir = await fs.open(this.realStateRoot, constants.O_RDONLY);
      try {
        await dir.sync();
      } finally {
        await dir.close();
      }
    } catch (error) {
      await fs.rm(temp, { force: true });
      throw error;
    }
  }

  async #appendOnce(state, kind, markdown) {
    const log = await this.#resolveSessionLog(state.sessionLog);
    const eventMarker = marker(kind, state.quizId);
    if (await fileContains(log.path, eventMarker)) return;

    const noFollow = constants.O_NOFOLLOW ?? 0;
    const handle = await fs.open(log.path, constants.O_WRONLY | constants.O_APPEND | noFollow);
    try {
      const stat = await handle.stat();
      if (!stat.isFile()) fail("INVALID_SESSION_LOG", "The session-log path is not a file.");
      await handle.writeFile(markdown, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
  }

  async register(input) {
    return this.#exclusiveMutation(async () => {
      const normalized = normalizeRegistration(input);
      const log = await this.#resolveSessionLog(normalized.sessionLog);
      const quizId = opaqueId("qz_");
      const state = {
        version: 1,
        quizId,
        sessionLog: log.relative,
        prompt: normalized.prompt,
        options: shuffle(normalized.options),
        correctValue: normalized.correctValue,
        explanation: normalized.explanation,
        createdAt: new Date().toISOString(),
        presentedAt: null,
        submission: null,
      };
      await this.#writeState(state, { createOnly: true });
      return { quiz_id: quizId, status: "registered" };
    });
  }

  async present(quizId) {
    return this.#exclusiveMutation(async () => {
      const state = await this.#readState(quizId);
      await this.#appendOnce(state, "present", presentationMarkdown(state));
      if (!state.presentedAt) {
        state.presentedAt = new Date().toISOString();
        await this.#writeState(state);
      }
      return publicPresentation(state);
    });
  }

  async submit(quizId, responseToken) {
    return this.#exclusiveMutation(async () => {
      const state = await this.#readState(quizId);
      if (!state.presentedAt) {
        fail("NOT_PRESENTED", "The quiz must be presented before it can be submitted.");
      }
      const token = typeof responseToken === "string" ? responseToken.trim().toUpperCase() : "";
      const validTokens = new Set([
        "0",
        ...state.options.map((_, index) => displayToken(index)),
      ]);
      if (!validTokens.has(token)) {
        fail("INVALID_RESPONSE", "response_token must be one displayed token or 0.");
      }

      if (state.submission) {
        if (state.submission.responseToken !== token) {
          fail("ALREADY_SUBMITTED", "This quiz was already submitted with a different response.");
        }
        await this.#appendOnce(state, "submit", submissionMarkdown(state));
        return publicSubmission(state);
      }

      const selected = token === "0" ? null : state.options[token.charCodeAt(0) - 65];
      const correctIndex = state.options.findIndex(
        (option) => option.stableValue === state.correctValue,
      );
      if (correctIndex < 0) fail("UNSAFE_STATE", "Quiz answer state is invalid.");
      const correct = state.options[correctIndex];
      const publicResult = {
        quiz_id: state.quizId,
        status: "submitted",
        response_token: token,
        selected_label: selected?.label ?? "I don't know",
        is_correct: selected?.stableValue === state.correctValue,
        correct_token: displayToken(correctIndex),
        correct_label: correct.label,
        explanation: state.explanation,
      };
      state.submission = {
        responseToken: token,
        submittedAt: new Date().toISOString(),
        publicResult,
      };
      await this.#writeState(state);
      await this.#appendOnce(state, "submit", submissionMarkdown(state));
      return structuredClone(publicResult);
    });
  }
}

export const internals = {
  parseLearningSessionLog,
  publicPresentation,
  presentationMarkdown,
  submissionMarkdown,
};
