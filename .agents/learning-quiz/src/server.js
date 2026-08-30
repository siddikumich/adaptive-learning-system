#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import * as z from "zod/v4";
import { QuizError, QuizStore } from "./quiz-store.js";

const store = new QuizStore();
const server = new McpServer({
  name: "learning-quiz",
  version: "1.0.0",
});

function toolResult(data) {
  return {
    content: [{ type: "text", text: JSON.stringify(data) }],
    structuredContent: data,
  };
}

function safeFailure(error) {
  const message =
    error instanceof QuizError ? `${error.code}: ${error.message}` : "INTERNAL_ERROR: Quiz operation failed.";
  return {
    isError: true,
    content: [{ type: "text", text: message }],
  };
}

server.registerTool(
  "register_quiz",
  {
    description:
      "Teacher/verifier-only: register an answer key and persist a shuffled diagnostic quiz. Do not call this in the learner-facing/main transcript.",
    inputSchema: {
      session_log: z
        .string()
        .min(1)
        .max(1024)
        .describe("Vault-relative path to an existing type: learning-session-log Markdown sidecar."),
      prompt: z.string().min(1).max(10_000).describe("The learner-facing question."),
      options: z
        .array(
          z.object({
            value: z
              .string()
              .min(1)
              .max(128)
              .describe("Stable, non-learner-facing option identifier."),
            label: z.string().min(1).max(2_000).describe("Learner-facing option text."),
          }),
        )
        .min(2)
        .max(20),
      correct_value: z
        .string()
        .min(1)
        .max(128)
        .describe("The stable value of exactly one option."),
      explanation: z
        .string()
        .min(1)
        .max(20_000)
        .describe("Feedback revealed only after the first submission."),
    },
  },
  async (input) => {
    try {
      return toolResult(await store.register(input));
    } catch (error) {
      return safeFailure(error);
    }
  },
);

server.registerTool(
  "present_quiz",
  {
    description:
      "Present a registered quiz with a persisted server-side shuffle and automatic 0 = I don't know. The answer key and stable values remain hidden.",
    inputSchema: {
      quiz_id: z.string().describe("Opaque identifier returned by register_quiz."),
    },
  },
  async ({ quiz_id }) => {
    try {
      return toolResult(await store.present(quiz_id));
    } catch (error) {
      return safeFailure(error);
    }
  },
);

server.registerTool(
  "submit_quiz",
  {
    description:
      "Submit exactly one displayed token. This reveals and records correctness, the answer label/token, and the explanation. Identical resubmission is idempotent; changed resubmission is rejected.",
    inputSchema: {
      quiz_id: z.string().describe("Opaque identifier returned by register_quiz."),
      response_token: z
        .string()
        .describe("A displayed A–T token, or 0 for I don't know. Stable option values are rejected."),
    },
  },
  async ({ quiz_id, response_token }) => {
    try {
      return toolResult(await store.submit(quiz_id, response_token));
    } catch (error) {
      return safeFailure(error);
    }
  },
);

const transport = new StdioServerTransport();
server.connect(transport).catch(() => {
  process.exitCode = 1;
});
