import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  PipelineError,
  publishVisual,
  stageVisual,
} from "../scripts/visual_pipeline.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIXTURES = path.resolve(HERE, "../fixtures");
const digest = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");

async function workspaceWith(fixture) {
  const workspace = await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(), "learning-visual-")));
  const source = path.join(workspace, path.basename(fixture));
  await fs.copyFile(path.join(FIXTURES, fixture), source);
  return { workspace, source, cacheDir: path.join(workspace, ".visual-cache") };
}

async function cleanup(workspace) {
  await fs.rm(workspace, { recursive: true, force: true });
}

test("SVG stage and publish preserve exact inspected bytes and editable source", async () => {
  const context = await workspaceWith("vector-balance.svg");
  try {
    const staged = await stageVisual({ kind: "svg", name: "vector-balance", ...context });
    const preview = await fs.readFile(staged.previewPath);
    assert.equal(digest(preview), staged.previewSha256);
    assert.equal(staged.receipt.status, "staged");
    assert.equal(staged.receipt.renderer.resvg, "2.6.2");

    await assert.rejects(
      publishVisual({ receipt: staged.receiptPath, approvedPreviewSha256: "0".repeat(64), workspace: context.workspace }),
      (error) => error instanceof PipelineError && error.code === "APPROVAL_MISMATCH",
    );
    const published = await publishVisual({ receipt: staged.receiptPath, approvedPreviewSha256: staged.previewSha256, workspace: context.workspace });
    assert.deepEqual(await fs.readFile(published.pngPath), preview);
    assert.deepEqual(await fs.readFile(published.sourcePath), await fs.readFile(context.source));
    const receipt = JSON.parse(await fs.readFile(published.publishedReceiptPath, "utf8"));
    assert.equal(receipt.status, "published");
    assert.equal(receipt.inspection.requiredTool, "view_image");
    assert.equal(receipt.publishedFiles.png.sha256, staged.previewSha256);
  } finally {
    await cleanup(context.workspace);
  }
});

test("publish refuses overwrite and source symlinks", async (t) => {
  const context = await workspaceWith("vector-balance.svg");
  try {
    const staged = await stageVisual({ kind: "svg", name: "no-overwrite", ...context });
    const output = path.join(context.workspace, "Attachments", "Learning Visuals");
    await fs.mkdir(output, { recursive: true });
    await fs.writeFile(path.join(output, "no-overwrite.png"), "user data");
    await assert.rejects(
      publishVisual({ receipt: staged.receiptPath, approvedPreviewSha256: staged.previewSha256, workspace: context.workspace }),
      (error) => error instanceof PipelineError && error.code === "OVERWRITE_REFUSED",
    );
    assert.equal(await fs.readFile(path.join(output, "no-overwrite.png"), "utf8"), "user data");

    const link = path.join(context.workspace, "linked.svg");
    try {
      await fs.symlink(context.source, link);
    } catch (error) {
      if (error.code === "EPERM") return t.skip("symlinks unavailable");
      throw error;
    }
    await assert.rejects(
      stageVisual({ kind: "svg", name: "linked", source: link, workspace: context.workspace, cacheDir: context.cacheDir }),
      (error) => error instanceof PipelineError && error.code === "SYMLINK_REFUSED",
    );
  } finally {
    await cleanup(context.workspace);
  }
});

test("publish detects staged-byte tampering", async () => {
  const context = await workspaceWith("vector-balance.svg");
  try {
    const staged = await stageVisual({ kind: "svg", name: "tamper-check", ...context });
    await fs.appendFile(staged.previewPath, "tamper");
    await assert.rejects(
      publishVisual({ receipt: staged.receiptPath, approvedPreviewSha256: staged.previewSha256, workspace: context.workspace }),
      (error) => error instanceof PipelineError && error.code === "STAGED_BYTES_CHANGED",
    );
  } finally {
    await cleanup(context.workspace);
  }
});

test("publish rejects a forged safe source that does not match the inspected preview", async () => {
  const context = await workspaceWith("vector-balance.svg");
  try {
    const staged = await stageVisual({ kind: "svg", name: "source-preview-binding", ...context });
    const receipt = JSON.parse(await fs.readFile(staged.receiptPath, "utf8"));
    const forgedSource = Buffer.from(
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360"><rect x="0" y="0" width="640" height="360" fill="#fff"/></svg>`,
    );
    await fs.writeFile(receipt.source.path, forgedSource);
    receipt.source.sha256 = digest(forgedSource);
    receipt.source.byteLength = forgedSource.length;
    await fs.writeFile(staged.receiptPath, `${JSON.stringify(receipt, null, 2)}\n`);
    await assert.rejects(
      publishVisual({ receipt: staged.receiptPath, approvedPreviewSha256: staged.previewSha256, workspace: context.workspace }),
      (error) => error instanceof PipelineError && error.code === "SOURCE_PREVIEW_MISMATCH",
    );
  } finally {
    await cleanup(context.workspace);
  }
});

test("pinned Mermaid renderer produces a staged PNG under strict configuration", { timeout: 45_000 }, async () => {
  const context = await workspaceWith("dependency-map.mmd");
  try {
    const staged = await stageVisual({ kind: "mermaid", name: "dependency-map", ...context });
    assert.equal(staged.receipt.renderer.mermaidCli, "11.16.0");
    assert.equal(staged.receipt.renderer.puppeteer, "25.9.0");
    assert.equal(staged.receipt.renderer.security, "mermaid-strict");
    assert.ok(staged.receipt.preview.width > 100);
    assert.ok(staged.receipt.preview.height > 50);
  } finally {
    await cleanup(context.workspace);
  }
});
