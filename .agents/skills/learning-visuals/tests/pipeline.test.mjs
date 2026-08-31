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

test("bundled SVG font makes labels affect rendered PNG bytes", async () => {
  const context = await workspaceWith("vector-balance.svg");
  try {
    const labeled = await stageVisual({ kind: "svg", name: "labeled", ...context });
    const strippedSource = path.join(context.workspace, "vector-balance-stripped.svg");
    const sourceText = await fs.readFile(context.source, "utf8");
    await fs.writeFile(strippedSource, sourceText.replace(/<text\b[^>]*>.*?<\/text>/gs, ""));
    const stripped = await stageVisual({
      kind: "svg",
      source: strippedSource,
      name: "stripped",
      workspace: context.workspace,
      cacheDir: context.cacheDir,
    });
    assert.notDeepEqual(await fs.readFile(labeled.previewPath), await fs.readFile(stripped.previewPath));
    assert.deepEqual(labeled.receipt.renderer.svgFont, {
      family: "Noto Sans",
      sha256: "b85c38ecea8a7cfb39c24e395a4007474fa5a4fc864f6ee33309eb4948d232d5",
    });
  } finally {
    await cleanup(context.workspace);
  }
});

test("workspace symlink aliases map source, cache, and receipt onto the canonical root", async (t) => {
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), "learning-visual-alias-"));
  const workspace = path.join(parent, "workspace");
  const alias = path.join(parent, "alias");
  await fs.mkdir(workspace);
  const canonicalWorkspace = await fs.realpath(workspace);
  try {
    await fs.symlink(workspace, alias, process.platform === "win32" ? "junction" : "dir");
  } catch (error) {
    await cleanup(parent);
    if (["EPERM", "EACCES", "ENOSYS"].includes(error.code)) return t.skip("directory symlinks unavailable");
    throw error;
  }
  try {
    const source = path.join(alias, "visual.svg");
    await fs.copyFile(path.join(FIXTURES, "vector-balance.svg"), source);
    const staged = await stageVisual({
      kind: "svg",
      source,
      name: "alias-lifecycle",
      workspace: alias,
      cacheDir: path.join(alias, ".cache"),
    });
    assert.ok(staged.receiptPath.startsWith(`${canonicalWorkspace}${path.sep}`));
    const receiptAlias = path.join(alias, path.relative(canonicalWorkspace, staged.receiptPath));
    const published = await publishVisual({
      receipt: receiptAlias,
      approvedPreviewSha256: staged.previewSha256,
      workspace: alias,
    });
    assert.ok(published.pngPath.startsWith(`${canonicalWorkspace}${path.sep}`));
  } finally {
    await cleanup(parent);
  }
});

test("explicit macOS /tmp lifecycle maps to /private/tmp", { skip: process.platform !== "darwin" }, async () => {
  const lexicalWorkspace = await fs.mkdtemp("/tmp/learning-visual-tmp-alias-");
  try {
    const source = path.join(lexicalWorkspace, "visual.svg");
    await fs.copyFile(path.join(FIXTURES, "vector-balance.svg"), source);
    const staged = await stageVisual({
      kind: "svg",
      source,
      name: "tmp-alias",
      workspace: lexicalWorkspace,
      cacheDir: path.join(lexicalWorkspace, ".cache"),
    });
    const published = await publishVisual({
      receipt: staged.receiptPath.replace(/^\/private\/tmp\//, "/tmp/"),
      approvedPreviewSha256: staged.previewSha256,
      workspace: lexicalWorkspace,
    });
    assert.ok(published.pngPath.startsWith("/private/tmp/"));
  } finally {
    await cleanup(await fs.realpath(lexicalWorkspace));
  }
});

test("outside caches and cache symlinks escaping the workspace remain refused", async (t) => {
  const context = await workspaceWith("vector-balance.svg");
  const outside = await fs.mkdtemp(path.join(os.tmpdir(), "learning-visual-outside-"));
  try {
    await assert.rejects(
      stageVisual({ kind: "svg", name: "outside", ...context, cacheDir: outside }),
      (error) => error instanceof PipelineError && error.code === "PATH_ESCAPE",
    );
    const cacheLink = path.join(context.workspace, "linked-cache");
    try {
      await fs.symlink(outside, cacheLink, process.platform === "win32" ? "junction" : "dir");
    } catch (error) {
      if (["EPERM", "EACCES", "ENOSYS"].includes(error.code)) return t.skip("directory symlinks unavailable");
      throw error;
    }
    await assert.rejects(
      stageVisual({ kind: "svg", name: "linked-cache", ...context, cacheDir: cacheLink }),
      (error) => error instanceof PipelineError && error.code === "UNSAFE_DIRECTORY",
    );
  } finally {
    await cleanup(context.workspace);
    await cleanup(outside);
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
