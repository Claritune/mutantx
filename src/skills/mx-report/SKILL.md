---
name: mx-report
description: "MutantX Phase 4 — Calculate mutation score and generate a detailed report with test gap analysis."
user_invocable: true
arguments: []
---

# MutantX — Phase 4: Reporting

You are the reporting phase of a mutation testing engine. Your job is to analyze the test results from Phase 3, calculate the mutation score, and generate a detailed human-readable report.

---

## Input

Read `.mutants/manifest.json` for test results. If no mutants have been tested (all `status: "pending"`), tell the user to run `/mx-test` first.

## Calculate the Mutation Score

```
mutation_score = killed / (killed + survived)
```

Exclude `skipped` and `error` mutants from the score. `timeout` counts as killed.

## Generate the Report

Write `.mutants/report.md` with the following structure:

```markdown
# MutantX — Mutation Testing Report

**Project:** <project name from directory>
**Date:** <timestamp>
**Commit:** <short hash from git rev-parse --short HEAD>

## Summary

| Metric | Value |
|--------|-------|
| Total mutants | N |
| Killed | N (N%) |
| Survived | N (N%) |
| Timeout | N |
| Skipped | N |
| **Mutation Score** | **N%** |

## Score Interpretation

- **> 80%**: Strong test suite — tests catch most injected bugs.
- **60–80%**: Moderate — there are meaningful gaps in test coverage.
- **< 60%**: Weak — many realistic bugs would go undetected.

## Survived Mutants ⚠️

These mutants were NOT caught by your tests. Each one represents a potential gap in your test coverage.

### Mutant NNN — <category> in `<file>`

**Line N:** <description of what was changed>

\```diff
<the patch content>
\```

**Why this matters:** <brief explanation of what kind of bug this represents and what could go wrong in production>

**Suggested test:** <concrete suggestion for a test that would catch this mutant>

(Repeat for each survived mutant)

## Killed Mutants ✓

| ID | File | Line | Category | Description |
|----|------|------|----------|-------------|
| 001 | src/utils.ts | 42 | arithmetic_operator | Changed * to + in price calc |
| ... | ... | ... | ... | ... |

## Recommendations

<2-5 bullet points summarizing the most important test gaps found and what areas of the code need better test coverage. Be specific — reference file names and functionality.>
```

For the survived mutants section, read the actual patch content from `.mutants/patches/NNN.patch` and include it. Also read the relevant source file to provide context in the "Why this matters" and "Suggested test" sections.

## Update the Manifest Summary

Update the `summary` field in `manifest.json`:

```json
"summary": {
  "total": 20,
  "killed": 16,
  "survived": 3,
  "timeout": 1,
  "skipped": 0,
  "score": 0.84,
  "tested_at": "<ISO 8601 timestamp>"
}
```

## Present Results to User

After writing the report, display a concise summary:

```
Mutation Testing Complete!

Score: 84% (16 killed / 19 testable)
Survived: 3 mutants — see .mutants/report.md for details

Top gaps:
  - src/billing.ts: price rounding logic has no edge case tests
  - src/auth.ts: token expiry check can be bypassed
```
