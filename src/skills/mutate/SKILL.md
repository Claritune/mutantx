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

## Phase 2.5: Validation (Deterministic + Optional AI)

The test script automatically validates mutants before testing, but if it reports `needs-review` mutants (source file changed, patch still applies), handle them:

1. **Run `mx-validate.py`** (already done automatically by mx-test.py) — classifies mutants as valid, stale, or needs-review.
2. **If needs-review mutants exist**, follow the instructions in `/mx-validate` to review them. This is the only step that uses AI tokens in the validation flow.
3. **Alternative**: run `mx-validate.py --promote` to trust the patches and skip AI review.

---

## Phase 3: Mutant Testing (Deterministic — Zero Tokens)

This phase is handled by the `mx-test.py` Python script. It does not use AI.

Find and run the script:

```bash
python3 <path-to-mx-test.py> --mutants-dir .mutants
```

Check these locations in order:
1. `./src/scripts/mx-test.py` (if inside the MutantX repo)
2. `~/.claude/scripts/mx-test.py` (global install)

The script automatically runs `mx-validate.py` first, then tests only `pending` mutants. Mutants marked `needs-review` or `stale` are skipped.

---

## Phase 4: Reporting (Deterministic + AI Analysis)

### Step 1: Run the deterministic report script (zero tokens)

```bash
python3 <path-to-mx-report.py> --mutants-dir .mutants
```

Check same locations as mx-test.py. This generates `.mutants/report.md` with summary statistics, patch diffs for survived mutants, and killed mutant table.

### Step 2: AI analysis of survived mutants

Follow the instructions in `/mx-report` to add "why this matters" explanations, suggested tests, and prioritized recommendations to the report.

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
