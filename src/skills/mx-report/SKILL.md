---
name: mx-report
description: "MutantX Phase 4 — Calculate mutation score and generate a detailed report with test gap analysis."
user_invocable: true
arguments: []
---

# MutantX — Phase 4: Reporting

This phase has two layers:

1. **Deterministic** (Python script) — calculates scores, generates summary tables, includes patch diffs for survived mutants
2. **AI analysis** (this skill) — reads the report and adds "why this matters" explanations, suggested tests, and prioritized recommendations

## Step 1: Run the Deterministic Report Script

Locate and execute `mx-report.py`:

```bash
python3 <path-to-mx-report.py> --mutants-dir .mutants
```

Find `mx-report.py` by checking these locations in order:
1. `./src/scripts/mx-report.py` (if inside the MutantX repo)
2. `~/.claude/scripts/mx-report.py` (global install)

This generates `.mutants/report.md` with summary statistics, survived mutant patches, killed mutant table, and updates the manifest summary. Display the script's output to the user.

## Step 2: AI Analysis of Survived Mutants

After the script runs, read `.mutants/report.md`. For each survived mutant section (marked with `<!-- AI analysis -->` comments), replace the comment with:

### For each survived mutant:

1. Read the patch diff shown in the report.
2. Read the relevant source file to understand the surrounding code context.
3. Add these two sections after the diff block:

**Why this matters:** A brief explanation of what kind of bug this mutation represents and what could go wrong in production if this bug existed. Be specific to the actual code, not generic.

**Suggested test:** A concrete, copy-pasteable test case (in the project's language and test framework) that would catch this mutant. Use realistic test names and assertions.

### After all survived mutants:

Add a `## Recommendations` section at the end of the report with 2-5 bullet points summarizing the most important test gaps found. Be specific — reference file names and functionality, not generic advice.

## Step 3: Present Results

Display a concise summary to the user:

```
Mutation Testing Complete!

Score: 84% (16 killed / 19 testable)
Survived: 3 mutants — see .mutants/report.md for details

Top gaps:
  - src/billing.ts: price rounding logic has no edge case tests
  - src/auth.ts: token expiry check can be bypassed
```
