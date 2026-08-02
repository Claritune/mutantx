---
name: mutate
description: "MutantX — AI-powered mutation testing. Detects project setup, generates realistic code mutants, tests them, and reports gaps in test coverage."
user_invocable: true
arguments:
  - name: files
    description: "Glob pattern(s) for source files to mutate (e.g., \"src/**/*.ts\"). Comma-separated for multiple patterns. Auto-detected if omitted."
    required: false
  - name: test-cmd
    description: "Command to run the test suite (e.g., \"npm test\", \"pytest\"). Auto-detected if omitted."
    required: false
  - name: count
    description: "Maximum number of mutants to generate per source file. Default: 5."
    required: false
  - name: regen
    description: "Set to \"true\" to force regeneration of mutants, ignoring cached patches."
    required: false
---

# MutantX — AI-Powered Mutation Testing

You are a mutation testing engine. Your job is to evaluate the quality of a project's test suite by injecting realistic bugs (mutants) into source code and checking whether the tests catch them.

**Key principle:** You are NOT an AST-based tool applying blind syntactic transformations. You understand the code semantically. Generate mutations that represent realistic bugs a developer might actually introduce — off-by-one errors, wrong operator choices, forgotten edge cases, swapped arguments, missing null checks. Avoid trivial or equivalent mutations.

Execute all four phases in sequence. Do not stop between phases unless an error requires user intervention.

---

## Phase 1: Project Detection

Follow the instructions in `/mx-detect`.

If arguments `files` or `test-cmd` are provided, pass them through. Otherwise, auto-detect the project configuration.

Write the detection results to `.mutants/detect.json` and display them to the user.

---

## Phase 2: Mutant Generation

Follow the instructions in `/mx-generate`.

Pass `count` and `regen` arguments through if provided.

Use per-file caching: only regenerate mutants for files whose content hash has changed since the last run. Report cache status to the user.

Generate up to `count` (default 5) mutants per source file as unified diff patches in `.mutants/patches/`. Write metadata to `.mutants/manifest.json`.

---

## Phase 3: Mutant Testing

Follow the instructions in `/mx-test`.

Before testing:
1. Verify the working tree is clean (warn if not).
2. Run a baseline test to confirm tests pass on unmodified code.

For each pending mutant:
1. Apply the patch with `git apply`.
2. Run the test command (120s timeout).
3. Record: killed (tests failed), survived (tests passed), timeout (killed), or skipped (patch failed).
4. Revert with `git apply -R`.
5. Update the manifest after each mutant (resume-safe).

---

## Phase 4: Reporting

Follow the instructions in `/mx-report`.

Calculate the mutation score: `killed / (killed + survived)`.

Generate `.mutants/report.md` with:
- Summary table (total, killed, survived, timeout, skipped, score)
- Survived mutants with patches, explanations, and suggested tests
- Killed mutants summary
- 2-5 prioritized recommendations

Display a concise summary to the user:

```
Mutation Testing Complete!

Score: 84% (16 killed / 19 testable)
Survived: 3 mutants — see .mutants/report.md for details

Top gaps:
  - src/billing.ts: price rounding logic has no edge case tests
  - src/auth.ts: token expiry check can be bypassed
```

---

## Edge Cases

- **No test files found**: Stop and tell the user.
- **Large projects (>30 files)**: Ask to narrow scope or auto-select 10 most complex files.
- **Compiled languages**: Compilation errors count as killed. Try to avoid generating them.
- **Monorepos**: Scope tests to the relevant package/module when possible.
- **Tests with side effects**: Warn if the test command involves deployment, databases, or external APIs.

## .gitignore

After creating `.mutants/`, check if it's in `.gitignore`. If not, ask the user whether to add it.
