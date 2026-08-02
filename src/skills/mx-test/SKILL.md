---
name: mx-test
description: "MutantX Phase 3 — Test each mutant by applying patches, running the test suite, and recording results."
user_invocable: true
arguments: []
---

# MutantX — Phase 3: Mutant Testing

You are the testing phase of a mutation testing engine. Your job is to apply each generated mutant patch, run the project's test suite, record whether the tests caught the bug, and revert the patch.

---

## Input

Read `.mutants/manifest.json` for the list of mutants and test command. If the manifest doesn't exist, tell the user to run `/mx-generate` first.

Read `.mutants/detect.json` for the test command if not present in the manifest config.

## Pre-flight Checks

1. **Clean working tree**: Run `git status --porcelain`. If there are uncommitted changes, warn the user and ask whether to proceed. Applying patches on a dirty tree risks merge conflicts and lost work.

2. **Baseline test run**: Run the test command once on the unmodified code. If any tests fail, STOP and report: "Baseline tests are failing. Fix your tests before running mutation testing." Do not proceed — testing mutants against a failing baseline produces meaningless results.

## Test Loop

For each mutant in the manifest with `status: "pending"`:

1. **Apply the patch:**
   ```bash
   git apply .mutants/patches/NNN.patch
   ```
   If this fails (e.g., code changed since generation), set status to `"skipped"` with a note and continue to the next mutant.

2. **Run the test command** using the Bash tool with a timeout of 120000ms (2 minutes). If the project's tests normally run much faster or slower, adjust proportionally (e.g., 3× the baseline test duration).

3. **Record the result:**
   - Tests **FAILED** (non-zero exit code) → mutant is **killed** ✓ (tests caught the bug)
   - Tests **PASSED** (zero exit code) → mutant **survived** ✗ (tests missed the bug)
   - **Timeout** → mutant is **killed (timeout)** ✓ (mutation likely caused an infinite loop)
   - **Patch failed to apply** → mutant is **skipped**

4. **Revert the patch:**
   ```bash
   git apply -R .mutants/patches/NNN.patch
   ```
   If revert fails, use `git checkout -- <file>` as a fallback. Verify the file is restored before continuing.

5. **Update the manifest** — set the mutant's `status` field and add `test_output` (last 20 lines of test output, for debugging).

After each mutant, write the updated manifest to disk so progress is saved even if the process is interrupted.

## Resuming Interrupted Runs

If the manifest has some mutants with `status: "pending"` and others already tested, only test the pending ones. This allows resuming after an interruption without re-running already-tested mutants.

## Compiled Languages

For Rust, Go, Java, C#, C/C++ — after applying a patch, the project must compile. If a mutant causes a compilation error, mark it as `"killed (compile error)"` and count it as killed (the compiler caught it, even if no test did). But the generation phase should have tried to avoid these.

## Progress Display

Show progress to the user as testing proceeds:

```
Testing mutant 3/15: arithmetic_operator in src/utils.ts:42 ... killed ✓
Testing mutant 4/15: return_value in src/auth.ts:87 ... survived ✗
```

After all mutants are tested, display a brief summary:

```
Testing complete: 12 killed, 2 survived, 1 skipped out of 15 mutants
Run /mx-report to generate the full report.
```
