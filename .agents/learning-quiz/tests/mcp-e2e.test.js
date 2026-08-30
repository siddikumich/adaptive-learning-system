import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const SERVER = path.resolve(TEST_DIR, "..", "src", "server.js");

function parsed(result) {
  assert.equal(result.isError, undefined);
  assert.equal(result.content.length, 1);
  return JSON.parse(result.content[0].text);
}

test("STDIO MCP exposes the three-tool answer-hidden lifecycle without transcript logging", async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "learning-quiz-mcp-"));
  const vault = path.join(root, "vault");
  const state = path.join(root, "state");
  await fs.mkdir(vault);
  const sessionLog = "MCP — Session Log.md";
  const logPath = path.join(vault, sessionLog);
  await fs.writeFile(
    logPath,
    "---\ntype: learning-session-log\nsession-note: '[[MCP]]'\nprotocol-version: '2026-08-26.1'\n---\n\n## Log\n",
  );

  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [SERVER],
    env: {
      PATH: process.env.PATH ?? "",
      LEARNING_QUIZ_VAULT_ROOT: vault,
      LEARNING_QUIZ_STATE_ROOT: state,
    },
    stderr: "pipe",
  });
  let stderr = "";
  transport.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  const client = new Client({ name: "quiz-e2e-test", version: "1.0.0" });
  await client.connect(transport);
  t.after(async () => {
    await client.close();
    await fs.rm(root, { recursive: true, force: true });
  });

  const tools = await client.listTools();
  assert.deepEqual(
    tools.tools.map(({ name }) => name).sort(),
    ["present_quiz", "register_quiz", "submit_quiz"],
  );
  const registerSchema = tools.tools.find(({ name }) => name === "register_quiz").inputSchema;
  assert.deepEqual(
    [...registerSchema.required].sort(),
    ["correct_value", "explanation", "options", "prompt", "session_log"],
  );

  const secretCorrect = "mcp_correct_secret_8d72";
  const secretWrong = "mcp_wrong_secret_13ae";
  const secretExplanation = "MCP_EXPLANATION_SECRET_19cc";
  const registeredResult = await client.callTool({
    name: "register_quiz",
    arguments: {
      session_log: sessionLog,
      prompt: "Pick the durable fact.",
      options: [
        { value: secretCorrect, label: "Primary artifacts outrank summaries" },
        { value: secretWrong, label: "Confident summaries outrank artifacts" },
      ],
      correct_value: secretCorrect,
      explanation: secretExplanation,
    },
  });
  const registered = parsed(registeredResult);
  assert.deepEqual(Object.keys(registered).sort(), ["quiz_id", "status"]);

  const presentedResult = await client.callTool({
    name: "present_quiz",
    arguments: { quiz_id: registered.quiz_id },
  });
  const presented = parsed(presentedResult);
  const preSubmissionBytes = JSON.stringify({ registeredResult, presentedResult });
  for (const secret of [secretCorrect, secretWrong, secretExplanation]) {
    assert.equal(preSubmissionBytes.includes(secret), false);
    assert.equal((await fs.readFile(logPath, "utf8")).includes(secret), false);
  }
  const correctToken = presented.options.find(
    ({ label }) => label === "Primary artifacts outrank summaries",
  ).token;

  const submittedResult = await client.callTool({
    name: "submit_quiz",
    arguments: { quiz_id: registered.quiz_id, response_token: correctToken },
  });
  const submitted = parsed(submittedResult);
  assert.equal(submitted.is_correct, true);
  assert.equal(submitted.explanation, secretExplanation);
  assert.equal((await fs.readFile(logPath, "utf8")).includes(secretExplanation), true);
  assert.equal(stderr, "");
});
