import assert from "node:assert/strict";
import test from "node:test";
import {
  PipelineError,
  validateMermaid,
  validateSvg,
} from "../scripts/visual_pipeline.mjs";

function rejectsCode(operation, code) {
  assert.throws(operation, (error) => error instanceof PipelineError && error.code === code);
}

test("strict Mermaid subset accepts declared nodes and directed edges", () => {
  assert.deepEqual(validateMermaid(`flowchart TD
n_a["A"]
n_b["B"]
n_a -->|"requires"| n_b
`), { nodeCount: 2, edgeCount: 1 });
});

test("Mermaid rejects directives, markup, undeclared nodes, and unsupported forms", () => {
  rejectsCode(() => validateMermaid("flowchart TD\n%%{init: {}}%%\nn_a[\"A\"]"), "UNSAFE_MERMAID");
  rejectsCode(() => validateMermaid("flowchart TD\nn_a[\"<b>A</b>\"]"), "UNSAFE_MERMAID");
  rejectsCode(() => validateMermaid("flowchart TD\nn_a[\"A\"]\nn_a --> n_b"), "UNDECLARED_NODE");
  rejectsCode(() => validateMermaid("sequenceDiagram\nAlice->>Bob: Hi"), "INVALID_MERMAID");
  rejectsCode(() => validateMermaid("flowchart TD\nn_a[\"A\"]\nclick n_a callback"), "UNSAFE_MERMAID");
});

const SAFE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80">
<title>Safe</title><rect x="5" y="5" width="90" height="70" fill="#fff" stroke="#111"/>
<text x="50" y="40" text-anchor="middle" font-size="12">A &amp; B</text></svg>`;

test("SVG allowlist accepts a small self-contained visual", () => {
  assert.deepEqual(validateSvg(SAFE_SVG), { viewBox: "0 0 100 80", width: 100, height: 80 });
});

test("SVG rejects active content and external or embedded references", () => {
  const hostile = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><script>alert(1)</script></svg>`,
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" onload="alert(1)"/>`,
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><foreignObject/></svg>`,
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><image href="data:image/png;base64,AA=="/></svg>`,
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><use href="https://example.com/x.svg#x"/></svg>`,
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect style="fill:red"/></svg>`,
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect fill="url(#paint)"/></svg>`,
    `<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text>&xxe;</text></svg>`,
  ];
  for (const value of hostile) assert.throws(() => validateSvg(value), PipelineError);
});

test("SVG rejects malformed structure and unsafe dimensions", () => {
  rejectsCode(() => validateSvg(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><g></svg>`), "INVALID_SVG");
  rejectsCode(() => validateSvg(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 0 10"/>`), "INVALID_SVG");
  rejectsCode(() => validateSvg(`<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>`), "INVALID_SVG");
});
