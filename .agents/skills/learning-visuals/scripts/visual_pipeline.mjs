#!/usr/bin/env node

import crypto from "node:crypto";
import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import puppeteer, { PUPPETEER_REVISIONS } from "puppeteer";
import {
  Browser as PuppeteerBrowser,
  computeExecutablePath,
  detectBrowserPlatform,
} from "@puppeteer/browsers";
import { renderMermaid } from "@mermaid-js/mermaid-cli";
import { Resvg } from "@resvg/resvg-js";

const require = createRequire(import.meta.url);
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = path.resolve(SCRIPT_DIR, "..");
const DEFAULT_WORKSPACE = path.resolve(SKILL_DIR, "../../../..");
const DEFAULT_CACHE = path.join(SKILL_DIR, ".cache", "staged");
const SCHEMA_VERSION = "learning-visual/v1";
const PIPELINE_VERSION = "1.0.0";
const MAX_SOURCE_BYTES = 256 * 1024;
const RENDER_TIMEOUT_MS = 30_000;

const MERMAID_ID = "n_[a-z0-9_]+";
const MERMAID_LABEL = String.raw`\["(?:[^"\\]|\\["\\n])*"\]`;
const MERMAID_NODE_RE = new RegExp(`^(${MERMAID_ID})${MERMAID_LABEL}$`);
const MERMAID_EDGE_RE = new RegExp(
  `^(${MERMAID_ID})(?:${MERMAID_LABEL})?\\s*-->(?:\\|"(?:[^"\\]|\\["\\n])*"\\|)?\\s*(${MERMAID_ID})(?:${MERMAID_LABEL})?$`,
);

const SVG_ELEMENTS = new Set([
  "svg", "g", "defs", "clippath", "lineargradient", "radialgradient",
  "stop", "rect", "circle", "ellipse", "line", "polyline", "polygon",
  "path", "text", "tspan", "title", "desc",
]);
const SVG_ATTRS = new Set([
  "xmlns", "viewbox", "width", "height", "x", "y", "x1", "y1", "x2",
  "y2", "cx", "cy", "r", "rx", "ry", "d", "points", "fill", "stroke",
  "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray",
  "stroke-dashoffset", "fill-opacity", "stroke-opacity", "opacity", "transform",
  "font-family", "font-size", "font-weight", "font-style", "text-anchor",
  "dominant-baseline", "letter-spacing", "dx", "dy", "offset", "stop-color",
  "stop-opacity", "gradientunits", "gradienttransform", "id",
  "clip-path", "fill-rule", "clip-rule", "vector-effect", "aria-label", "role",
]);
const SAFE_COLOR = /^(?:none|transparent|currentColor|#[0-9a-fA-F]{3,8}|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)|rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(?:0(?:\.\d+)?|1(?:\.0+)?)\s*\)|[a-zA-Z]+)$/;

export class PipelineError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "PipelineError";
    this.code = code;
  }
}

function fail(code, message) {
  throw new PipelineError(code, message);
}

function packageVersion(packageName) {
  let cursor = path.dirname(require.resolve(packageName));
  while (cursor !== path.dirname(cursor)) {
    const manifest = path.join(cursor, "package.json");
    if (fsSync.existsSync(manifest)) {
      const parsed = JSON.parse(fsSync.readFileSync(manifest, "utf8"));
      if (parsed.name === packageName) return parsed.version;
    }
    cursor = path.dirname(cursor);
  }
  fail("PACKAGE_VERSION_UNKNOWN", `Cannot locate installed package metadata for ${packageName}`);
}

function sha256(data) {
  return crypto.createHash("sha256").update(data).digest("hex");
}

function inside(child, parent) {
  const relative = path.relative(parent, child);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

async function assertNoSymlinkPath(target, stopAt, allowMissingLeaf = false) {
  const absolute = path.resolve(target);
  const boundary = path.resolve(stopAt);
  if (!inside(absolute, boundary)) fail("PATH_ESCAPE", `Path escapes allowed root: ${target}`);
  const relative = path.relative(boundary, absolute);
  let cursor = boundary;
  const boundaryStat = await fs.lstat(boundary).catch(() => null);
  if (!boundaryStat?.isDirectory() || boundaryStat.isSymbolicLink()) {
    fail("UNSAFE_ROOT", `Allowed root is missing, not a directory, or a symlink: ${boundary}`);
  }
  const parts = relative ? relative.split(path.sep) : [];
  for (let index = 0; index < parts.length; index += 1) {
    cursor = path.join(cursor, parts[index]);
    const stat = await fs.lstat(cursor).catch((error) => {
      if (error.code === "ENOENT") return null;
      throw error;
    });
    if (!stat) {
      if (allowMissingLeaf && index === parts.length - 1) return;
      fail("MISSING_PATH", `Required path component does not exist: ${cursor}`);
    }
    if (stat.isSymbolicLink()) fail("SYMLINK_REFUSED", `Symlink path component refused: ${cursor}`);
    if (index < parts.length - 1 && !stat.isDirectory()) {
      fail("NOT_DIRECTORY", `Non-directory path component refused: ${cursor}`);
    }
  }
}

async function mkdirSafe(target, workspaceRoot) {
  const absolute = path.resolve(target);
  if (!inside(absolute, workspaceRoot)) fail("PATH_ESCAPE", `Directory escapes workspace: ${target}`);
  const relative = path.relative(workspaceRoot, absolute);
  let cursor = workspaceRoot;
  for (const part of relative.split(path.sep).filter(Boolean)) {
    cursor = path.join(cursor, part);
    const stat = await fs.lstat(cursor).catch((error) => error.code === "ENOENT" ? null : Promise.reject(error));
    if (stat) {
      if (!stat.isDirectory() || stat.isSymbolicLink()) fail("UNSAFE_DIRECTORY", `Unsafe directory component: ${cursor}`);
    } else {
      await fs.mkdir(cursor, { mode: 0o700 });
    }
  }
}

async function readSafeSource(sourcePath, workspaceRoot, expectedExtension) {
  const absolute = path.resolve(sourcePath);
  await assertNoSymlinkPath(absolute, workspaceRoot);
  const real = await fs.realpath(absolute);
  if (!inside(real, workspaceRoot)) fail("PATH_ESCAPE", "Source resolves outside the workspace");
  const stat = await fs.stat(real);
  if (!stat.isFile()) fail("NOT_FILE", "Source must be a regular file");
  if (stat.size > MAX_SOURCE_BYTES) fail("SOURCE_TOO_LARGE", `Source exceeds ${MAX_SOURCE_BYTES} bytes`);
  if (path.extname(real).toLowerCase() !== expectedExtension) {
    fail("WRONG_EXTENSION", `Expected a ${expectedExtension} source file`);
  }
  const bytes = await fs.readFile(real);
  if (bytes.includes(0)) fail("BINARY_SOURCE", "Source contains a NUL byte");
  return { absolute: real, bytes, text: bytes.toString("utf8") };
}

export function validateMermaid(source) {
  if (Buffer.byteLength(source, "utf8") > MAX_SOURCE_BYTES) fail("SOURCE_TOO_LARGE", "Mermaid source is too large");
  if (/\0|\r/.test(source)) fail("INVALID_MERMAID", "Mermaid must be UTF-8 text with LF line endings");
  if (/%%\{|<|&|;|`|\b(?:click|style|classDef|class|subgraph|end|linkStyle|accTitle|accDescr)\b/i.test(source)) {
    fail("UNSAFE_MERMAID", "Mermaid contains a forbidden directive, token, or markup character");
  }
  const lines = source.split("\n").map((line) => line.trim()).filter(Boolean);
  if (!/^flowchart (?:TD|LR)$/.test(lines[0] ?? "")) {
    fail("INVALID_MERMAID", "First line must be exactly 'flowchart TD' or 'flowchart LR'");
  }
  if (lines.length < 2) fail("INVALID_MERMAID", "Diagram must contain at least one node or edge");
  const declared = new Set();
  const referenced = new Set();
  for (const line of lines.slice(1)) {
    const node = line.match(MERMAID_NODE_RE);
    if (node) {
      if (declared.has(node[1])) fail("DUPLICATE_NODE", `Duplicate node declaration: ${node[1]}`);
      declared.add(node[1]);
      continue;
    }
    const edge = line.match(MERMAID_EDGE_RE);
    if (edge) {
      referenced.add(edge[1]);
      referenced.add(edge[2]);
      continue;
    }
    fail("INVALID_MERMAID", `Unsupported Mermaid line: ${line}`);
  }
  for (const id of referenced) {
    if (!declared.has(id)) fail("UNDECLARED_NODE", `Edge references undeclared node: ${id}`);
  }
  return { nodeCount: declared.size, edgeCount: lines.slice(1).filter((line) => MERMAID_EDGE_RE.test(line)).length };
}

function parseXmlAttributes(raw, element) {
  let rest = raw.trim();
  const attrs = new Map();
  while (rest) {
    const match = rest.match(/^([A-Za-z_:][A-Za-z0-9_.:-]*)\s*=\s*(["'])(.*?)\2\s*/s);
    if (!match) fail("INVALID_SVG", `Malformed attribute on <${element}>`);
    const original = match[1];
    const key = original.toLowerCase();
    const value = match[3];
    if (key.startsWith("on") || key === "style" || key === "href" || key === "xlink:href") {
      fail("UNSAFE_SVG", `Forbidden SVG attribute: ${original}`);
    }
    if (!SVG_ATTRS.has(key)) fail("UNSAFE_SVG", `SVG attribute is not allowlisted: ${original}`);
    if (attrs.has(key)) fail("INVALID_SVG", `Duplicate SVG attribute: ${original}`);
    if ((key !== "xmlns" && /url\s*\(|(?:https?|file|data|javascript):/i.test(value)) || /\\|[\u0000-\u001f]/.test(value)) {
      fail("UNSAFE_SVG", `Unsafe SVG attribute value on ${original}`);
    }
    if (["fill", "stroke", "stop-color"].includes(key) && !SAFE_COLOR.test(value)) {
      fail("UNSAFE_SVG", `Color value is not allowlisted: ${value}`);
    }
    attrs.set(key, value);
    rest = rest.slice(match[0].length);
  }
  return attrs;
}

export function validateSvg(source) {
  if (Buffer.byteLength(source, "utf8") > MAX_SOURCE_BYTES) fail("SOURCE_TOO_LARGE", "SVG source is too large");
  if (/<!DOCTYPE|<!ENTITY|<\?xml-stylesheet|<!--|<\!\[CDATA\[|\0/i.test(source)) {
    fail("UNSAFE_SVG", "SVG contains a doctype, entity, stylesheet, comment, CDATA, or NUL byte");
  }
  if (/&(?!amp;|lt;|gt;|quot;|apos;)/.test(source)) fail("UNSAFE_SVG", "SVG contains a non-allowlisted entity");
  let cursor = 0;
  const stack = [];
  let rootAttrs;
  const tagRe = /<([^<>]+)>/g;
  for (const match of source.matchAll(tagRe)) {
    const text = source.slice(cursor, match.index);
    if (stack.at(-1) !== "text" && stack.at(-1) !== "tspan" && stack.at(-1) !== "title" && stack.at(-1) !== "desc" && text.trim()) {
      fail("INVALID_SVG", "Text is only allowed inside text, tspan, title, or desc elements");
    }
    cursor = match.index + match[0].length;
    const body = match[1].trim();
    if (body.startsWith("?")) {
      if (stack.length || !/^\?xml\s+version=["']1\.0["']\s*\?$/.test(body)) fail("INVALID_SVG", "Only a minimal XML declaration is allowed");
      continue;
    }
    if (body.startsWith("/")) {
      const closeName = body.slice(1).trim().toLowerCase();
      if (!SVG_ELEMENTS.has(closeName) || stack.pop() !== closeName) fail("INVALID_SVG", `Mismatched closing tag: ${closeName}`);
      continue;
    }
    const selfClosing = body.endsWith("/");
    const openBody = selfClosing ? body.slice(0, -1).trim() : body;
    const nameMatch = openBody.match(/^([A-Za-z][A-Za-z0-9]*)(?=\s|$)/);
    if (!nameMatch) fail("INVALID_SVG", "Malformed SVG element");
    const originalName = nameMatch[1];
    const name = originalName.toLowerCase();
    if (!SVG_ELEMENTS.has(name)) fail("UNSAFE_SVG", `SVG element is not allowlisted: ${originalName}`);
    const attrs = parseXmlAttributes(openBody.slice(originalName.length), originalName);
    if (stack.length === 0) {
      if (name !== "svg" || rootAttrs) fail("INVALID_SVG", "SVG must have exactly one svg root");
      rootAttrs = attrs;
    }
    if (!selfClosing) stack.push(name);
  }
  if (source.slice(cursor).trim()) fail("INVALID_SVG", "Unparsed content follows the SVG document");
  if (stack.length) fail("INVALID_SVG", `Unclosed SVG element: ${stack.at(-1)}`);
  if (!rootAttrs) fail("INVALID_SVG", "Missing svg root element");
  if (rootAttrs.get("xmlns") !== "http://www.w3.org/2000/svg") fail("INVALID_SVG", "SVG root must declare the SVG namespace");
  const viewBox = rootAttrs.get("viewbox");
  if (!viewBox || !/^\s*-?(?:\d+(?:\.\d+)?|\.\d+)\s+-?(?:\d+(?:\.\d+)?|\.\d+)\s+(?:\d+(?:\.\d+)?|\.\d+)\s+(?:\d+(?:\.\d+)?|\.\d+)\s*$/.test(viewBox)) {
    fail("INVALID_SVG", "SVG root requires a numeric viewBox with positive width and height");
  }
  const [, , width, height] = viewBox.trim().split(/\s+/).map(Number);
  if (!(width > 0 && height > 0 && width <= 10_000 && height <= 10_000)) fail("INVALID_SVG", "SVG viewBox dimensions are outside the safe range");
  return { viewBox, width, height };
}

function pngDimensions(bytes) {
  if (bytes.length < 24 || bytes.subarray(1, 4).toString("ascii") !== "PNG") fail("INVALID_RENDER", "Renderer did not produce a PNG");
  const width = bytes.readUInt32BE(16);
  const height = bytes.readUInt32BE(20);
  if (!width || !height || width > 10_000 || height > 10_000) fail("INVALID_RENDER", "PNG dimensions are invalid or unsafe");
  return { width, height };
}

async function withTimeout(operation, milliseconds, onTimeout) {
  let timeout;
  try {
    return await Promise.race([
      operation,
      new Promise((_, reject) => {
        timeout = setTimeout(async () => {
          await onTimeout?.().catch(() => {});
          reject(new PipelineError("RENDER_TIMEOUT", `Rendering exceeded ${milliseconds} ms`));
        }, milliseconds);
      }),
    ]);
  } finally {
    clearTimeout(timeout);
  }
}

async function renderMermaidPng(source) {
  let browser;
  try {
    // Puppeteer installs both Chrome products independently. This pipeline uses
    // the smaller headless shell, so asking Puppeteer for its default Chrome
    // path can point at a binary that was intentionally not installed.
    const platform = detectBrowserPlatform();
    if (!platform) fail("MERMAID_RENDER_FAILED", "This platform has no supported local Chromium build");
    const executablePath = computeExecutablePath({
      // Resolve from the skill, not process.cwd(); the documented command is
      // normally launched from the vault root while installation runs here.
      cacheDir: path.join(SKILL_DIR, ".cache", "puppeteer"),
      browser: PuppeteerBrowser.CHROMEHEADLESSSHELL,
      buildId: PUPPETEER_REVISIONS["chrome-headless-shell"],
      platform,
    });
    browser = await puppeteer.launch({
      executablePath,
      headless: "shell",
      args: ["--disable-background-networking", "--disable-default-apps", "--disable-extensions", "--disable-sync", "--no-first-run"],
    });
    const rendered = await withTimeout(
      renderMermaid(browser, source, "png", {
        viewport: { width: 1200, height: 900, deviceScaleFactor: 1 },
        backgroundColor: "white",
        mermaidConfig: {
          securityLevel: "strict",
          htmlLabels: false,
          maxTextSize: 50_000,
          suppressErrorRendering: true,
          theme: "default",
        },
        iconPacks: [],
        iconPacksNamesAndUrls: [],
      }),
      RENDER_TIMEOUT_MS,
      async () => browser?.close(),
    );
    return Buffer.from(rendered.data);
  } catch (error) {
    if (error instanceof PipelineError) throw error;
    fail("MERMAID_RENDER_FAILED", `Local Mermaid render failed: ${error.message}`);
  } finally {
    await browser?.close().catch(() => {});
  }
}

async function renderSvgPng(source) {
  try {
    return await withTimeout(
      Promise.resolve().then(() => {
        const renderer = new Resvg(source, {
          background: "white",
          fitTo: { mode: "width", value: 1200 },
          font: { loadSystemFonts: false, defaultFontFamily: "sans-serif" },
        });
        return Buffer.from(renderer.render().asPng());
      }),
      RENDER_TIMEOUT_MS,
    );
  } catch (error) {
    if (error instanceof PipelineError) throw error;
    fail("SVG_RENDER_FAILED", `Local SVG render failed: ${error.message}`);
  }
}

function validateName(name) {
  if (!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(name ?? "")) fail("INVALID_NAME", "Name must match ^[a-z0-9][a-z0-9_-]{0,63}$");
  return name;
}

async function atomicWrite(file, bytes, mode = 0o600, { createOnly = false } = {}) {
  const temporary = `${file}.tmp-${process.pid}-${crypto.randomUUID()}`;
  let linkedDestination = false;
  const handle = await fs.open(temporary, "wx", mode);
  try {
    await handle.writeFile(bytes);
    await handle.sync();
  } finally {
    await handle.close();
  }
  try {
    if (createOnly) {
      // link() is an atomic no-clobber publication on the same filesystem.
      // rename() would overwrite a file created after refuseExisting().
      await fs.link(temporary, file);
      linkedDestination = true;
      await fs.unlink(temporary);
    } else {
      await fs.rename(temporary, file);
    }
  } catch (error) {
    if (linkedDestination) await fs.unlink(file).catch(() => {});
    await fs.unlink(temporary).catch(() => {});
    throw error;
  }
}

async function resolveRoots(workspaceArg, cacheArg) {
  const workspace = await fs.realpath(path.resolve(workspaceArg ?? DEFAULT_WORKSPACE));
  await assertNoSymlinkPath(workspace, workspace);
  const cache = path.resolve(cacheArg ?? DEFAULT_CACHE);
  if (!inside(cache, workspace)) fail("PATH_ESCAPE", "Cache must be inside the workspace");
  await mkdirSafe(cache, workspace);
  return { workspace, cache };
}

export async function stageVisual({ kind, source, name, workspace: workspaceArg, cacheDir }) {
  if (!new Set(["mermaid", "svg"]).has(kind)) fail("INVALID_KIND", "Kind must be 'mermaid' or 'svg'");
  validateName(name);
  const { workspace, cache } = await resolveRoots(workspaceArg, cacheDir);
  const extension = kind === "mermaid" ? ".mmd" : ".svg";
  const input = await readSafeSource(source, workspace, extension);
  const validation = kind === "mermaid" ? validateMermaid(input.text) : validateSvg(input.text);
  const png = kind === "mermaid" ? await renderMermaidPng(input.text) : await renderSvgPng(input.text);
  const dimensions = pngDimensions(png);
  const id = crypto.randomUUID();
  const stageDir = path.join(cache, id);
  await fs.mkdir(stageDir, { mode: 0o700 });
  const stagedSource = path.join(stageDir, `source${extension}`);
  const preview = path.join(stageDir, "preview.png");
  await atomicWrite(stagedSource, input.bytes);
  await atomicWrite(preview, png);
  const receipt = {
    schemaVersion: SCHEMA_VERSION,
    pipelineVersion: PIPELINE_VERSION,
    status: "staged",
    id,
    kind,
    name,
    createdAt: new Date().toISOString(),
    workspace,
    cache,
    validation,
    source: { path: stagedSource, sha256: sha256(input.bytes), byteLength: input.bytes.length },
    preview: { path: preview, sha256: sha256(png), byteLength: png.length, ...dimensions },
    renderer: {
      mermaidCli: packageVersion("@mermaid-js/mermaid-cli"),
      puppeteer: packageVersion("puppeteer"),
      resvg: packageVersion("@resvg/resvg-js"),
      node: process.version,
      security: kind === "mermaid" ? "mermaid-strict" : "svg-hostile-allowlist",
    },
    publish: {
      directory: path.join(workspace, "Attachments", "Learning Visuals"),
      pngFilename: `${name}.png`,
      sourceFilename: `${name}${extension}`,
      receiptFilename: `${name}.visual-receipt.json`,
    },
  };
  const receiptPath = path.join(stageDir, "receipt.json");
  await atomicWrite(receiptPath, Buffer.from(`${JSON.stringify(receipt, null, 2)}\n`));
  return { ok: true, command: "stage", receiptPath, previewPath: preview, previewSha256: receipt.preview.sha256, receipt };
}

async function refuseExisting(files, workspace) {
  for (const file of files) {
    await assertNoSymlinkPath(file, workspace, true);
    const stat = await fs.lstat(file).catch((error) => error.code === "ENOENT" ? null : Promise.reject(error));
    if (stat) fail("OVERWRITE_REFUSED", `Refusing to overwrite existing path: ${file}`);
  }
}

export async function publishVisual({ receipt: receiptArg, approvedPreviewSha256, workspace: workspaceArg }) {
  if (!/^[0-9a-f]{64}$/.test(approvedPreviewSha256 ?? "")) fail("BAD_APPROVAL", "approved-preview-sha256 must be a lowercase SHA-256 digest");
  const workspace = await fs.realpath(path.resolve(workspaceArg ?? DEFAULT_WORKSPACE));
  const receiptPath = path.resolve(receiptArg ?? "");
  await assertNoSymlinkPath(receiptPath, workspace);
  const receipt = JSON.parse(await fs.readFile(receiptPath, "utf8"));
  if (receipt.schemaVersion !== SCHEMA_VERSION || receipt.pipelineVersion !== PIPELINE_VERSION || receipt.status !== "staged") {
    fail("INVALID_RECEIPT", "Receipt is not a staged receipt for this pipeline version");
  }
  validateName(receipt.name);
  if (receipt.workspace !== workspace) fail("WORKSPACE_MISMATCH", "Receipt belongs to a different workspace");
  const expectedStageDir = path.join(path.resolve(receipt.cache), receipt.id);
  if (path.dirname(receiptPath) !== expectedStageDir || path.basename(receiptPath) !== "receipt.json" || !inside(expectedStageDir, workspace)) {
    fail("INVALID_RECEIPT_PATH", "Receipt is not in its declared staging directory");
  }
  await assertNoSymlinkPath(expectedStageDir, workspace);
  const extension = receipt.kind === "mermaid" ? ".mmd" : receipt.kind === "svg" ? ".svg" : fail("INVALID_KIND", "Receipt kind is invalid");
  const stagedSource = path.join(expectedStageDir, `source${extension}`);
  const stagedPreview = path.join(expectedStageDir, "preview.png");
  if (receipt.source.path !== stagedSource || receipt.preview.path !== stagedPreview) fail("RECEIPT_TAMPERED", "Receipt staging paths do not match canonical paths");
  const [sourceBytes, previewBytes] = await Promise.all([fs.readFile(stagedSource), fs.readFile(stagedPreview)]);
  if (sha256(sourceBytes) !== receipt.source.sha256 || sha256(previewBytes) !== receipt.preview.sha256) fail("STAGED_BYTES_CHANGED", "Staged source or preview changed after staging");
  if (approvedPreviewSha256 !== receipt.preview.sha256) fail("APPROVAL_MISMATCH", "Approval does not match the staged preview bytes");
  pngDimensions(previewBytes);
  const sourceText = sourceBytes.toString("utf8");
  const validation = receipt.kind === "mermaid" ? validateMermaid(sourceText) : validateSvg(sourceText);
  if (JSON.stringify(validation) !== JSON.stringify(receipt.validation)) {
    fail("RECEIPT_TAMPERED", "Receipt validation does not match the staged source");
  }
  const reproducedPreview = receipt.kind === "mermaid"
    ? await renderMermaidPng(sourceText)
    : await renderSvgPng(sourceText);
  if (!reproducedPreview.equals(previewBytes)) {
    fail("SOURCE_PREVIEW_MISMATCH", "Staged source does not reproduce the inspected preview bytes");
  }
  const outputDir = path.join(workspace, "Attachments", "Learning Visuals");
  if (receipt.publish.directory !== outputDir) fail("RECEIPT_TAMPERED", "Publish directory was changed");
  await mkdirSafe(outputDir, workspace);
  const pngPath = path.join(outputDir, receipt.publish.pngFilename);
  const sourcePath = path.join(outputDir, receipt.publish.sourceFilename);
  const publishedReceiptPath = path.join(outputDir, receipt.publish.receiptFilename);
  const expectedNames = [`${receipt.name}.png`, `${receipt.name}${extension}`, `${receipt.name}.visual-receipt.json`];
  if ([path.basename(pngPath), path.basename(sourcePath), path.basename(publishedReceiptPath)].some((value, index) => value !== expectedNames[index])) {
    fail("RECEIPT_TAMPERED", "Published filenames were changed");
  }
  const targets = [pngPath, sourcePath, publishedReceiptPath];
  await refuseExisting(targets, workspace);
  const published = {
    ...receipt,
    status: "published",
    publishedAt: new Date().toISOString(),
    inspection: {
      requiredTool: "view_image",
      approvedPreviewSha256,
      assertion: "Caller inspected previewPath and approved these exact PNG bytes",
    },
    publishedFiles: {
      png: { path: pngPath, sha256: sha256(previewBytes), byteLength: previewBytes.length },
      source: { path: sourcePath, sha256: sha256(sourceBytes), byteLength: sourceBytes.length },
      receipt: { path: publishedReceiptPath },
    },
  };
  const publishedReceiptBytes = Buffer.from(`${JSON.stringify(published, null, 2)}\n`);
  const created = [];
  try {
    await atomicWrite(pngPath, previewBytes, 0o600, { createOnly: true }); created.push(pngPath);
    await atomicWrite(sourcePath, sourceBytes, 0o600, { createOnly: true }); created.push(sourcePath);
    await atomicWrite(publishedReceiptPath, publishedReceiptBytes, 0o600, { createOnly: true }); created.push(publishedReceiptPath);
    const finalPng = await fs.readFile(pngPath);
    if (!finalPng.equals(previewBytes)) fail("BYTE_MISMATCH", "Published PNG is not byte-identical to inspected preview");
    await atomicWrite(receiptPath, publishedReceiptBytes);
  } catch (error) {
    await Promise.all(created.map((file) => fs.unlink(file).catch(() => {})));
    throw error;
  }
  return { ok: true, command: "publish", pngPath, sourcePath, publishedReceiptPath, pngSha256: sha256(previewBytes), receipt: published };
}

function parseArgs(argv) {
  const command = argv[0];
  const options = {};
  for (let index = 1; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!flag?.startsWith("--") || value === undefined) fail("BAD_ARGUMENTS", `Expected --flag value, got ${flag ?? "end of input"}`);
    const key = flag.slice(2).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    if (Object.hasOwn(options, key)) fail("BAD_ARGUMENTS", `Duplicate argument: ${flag}`);
    options[key] = value;
  }
  return { command, options };
}

export async function main(argv = process.argv.slice(2)) {
  const { command, options } = parseArgs(argv);
  if (command === "stage") return stageVisual(options);
  if (command === "publish") return publishVisual(options);
  fail("BAD_COMMAND", "Usage: visual_pipeline.mjs stage|publish [--flag value ...]");
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().then(
    (result) => process.stdout.write(`${JSON.stringify(result)}\n`),
    (error) => {
      const code = error instanceof PipelineError ? error.code : "UNEXPECTED_ERROR";
      process.stderr.write(`${JSON.stringify({ ok: false, error: { code, message: error.message } })}\n`);
      process.exitCode = 1;
    },
  );
}
