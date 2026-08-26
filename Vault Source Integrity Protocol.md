---
type: guide
status: active
updated: 2026-08-13
---

# Vault source integrity protocol

## Aim

Keep durable vault claims traceable to the best accessible evidence even when
the public web is incomplete, AI crawlers are blocked, search results are
noisy, or an AI system supplies an unreliable summary.

## What is known about the web-access concern

- Cloudflare reported that, across the HTML requests it measured in 2025,
  non-AI bots began the year at about half of requests—seven percentage points
  above human-generated traffic. This is a network-and-request measurement,
  not a census of all Internet use or all website visitors.
- Automated bot traffic accounted for 51% of web traffic in Imperva's 2024
  dataset. It includes many types of automation, not only web crawlers.
- Site operators can restrict crawlers, which can create coverage and selection
  gaps for search engines and AI systems.

Therefore: use “locked” as an operational label for **a source inaccessible to
the current research method**, not as a claim that it is absent, false, or
unavailable to every reader. Do not infer the composition of any model's
training data or search index from crawler traffic alone.

Sources: [Cloudflare 2025 Year in Review](https://blog.cloudflare.com/radar-2025-year-in-review/), [Imperva 2025 Bad Bot Report](https://www.imperva.com/resources/wp-content/uploads/sites/6/reports/2025-Bad-Bot-Report.pdf).

## Required workflow for durable factual claims

1. **State the claim precisely.** Include who/what, date range, denominator,
   definition, and decision it is meant to support.
2. **Find the primary or authoritative artifact.** Prefer original code, data,
   ticket, paper, official documentation, filing, job posting, course source,
   or direct record. Search snippets, dashboards, AI answers, and summaries
   are discovery leads only.
3. **Read the source itself.** Do not cite a title, snippet, or secondary
   account as though it proves an uninspected claim. Record a durable direct
   link near material claims.
4. **Check scope before writing.** Verify dates, units, population, baseline,
   method, and whether the source actually supports the wording.
5. **Label the evidence state.** Use `Verified`, `Reported`, `Inference`, or
   `Unknown`. For consequential uncertainty, write: `Known: … / Inference: …
   / Unknown: … / To verify: …`.
6. **Preserve the boundary.** Do not complete an attractive narrative when the
   evidence does not support it.

## Handling a locked or inaccessible source

1. Log the source's title/URL, access date, and barrier (`robots`, login,
   paywall, unavailable page, missing primary artifact, or unclear provenance).
2. Seek a legitimate first-party alternative: official PDF, repository,
   dataset, filing, documentation, author copy, or an archived version where
   permitted.
3. If access remains unavailable, leave the claim **unverified**. A credible
   secondary source may describe the claim, but must be labelled secondary and
   cannot silently become primary evidence.
4. Ask the vault owner to provide an authorized copy only when the claim is
   important enough to justify the effort. Never bypass access controls or
   upload private/employer material without permission.
5. Record the absence as a coverage limitation. Never convert “the crawler or
   AI could not reach it” into “it does not exist” or “the opposite is true.”

## AI and search rules

- Treat AI output and search-result snippets as leads, never as vault evidence.
- Require an opened, inspected source for a factual claim, citation, quote,
  number, or recommendation presented as evidence-based.
- For technical claims, prefer official documentation plus a reproducible test
  or source code path. For personal/recruiting claims, prefer original work
  artifacts. For research claims, prefer original studies, reviews, and
  authoritative guidance.
- Use more than one independent source when a claim is consequential or the
  sources share an incentive, dataset, or reporting chain.
- Date-stamp mutable web claims and save the source link at the point of use.
  Do not claim a source was read if only a summary was seen.

## Minimal provenance footer

For a consequential note, add this when useful:

```markdown
## Evidence status

- Verified: [direct source](URL), accessed YYYY-MM-DD
- Inference: …
- Unknown / to verify: …
```

## Related

- [[AI Learning Contract]]
- [[Learning System]]
- [[Learning Research Sources]]
- [[CURRENT-STATE]]
