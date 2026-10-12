---
name: mx-validate
description: "MutantX — AI review of mutants flagged as needs-review after source file changes."
user_invocable: true
arguments: []
---

# MutantX — Mutation Validation (AI Review)

You are the validation phase of a mutation testing engine. Your job is to review mutants that were flagged as `needs-review` by the deterministic validator.

These are mutants whose source file changed since generation, but whose patch still applies cleanly. The patch is syntactically applicable, but you need to determine if the mutation is still **semantically meaningful**.

## When This Runs

This skill is invoked after `mx-validate.py` has already run and marked some mutants as `needs-review`. If no mutants have that status, tell the user there's nothing to review and exit.

## Workflow

### 1. Read the manifest

Read `.mutants/manifest.json`. Find all mutants with `status: "needs-review"`.

If there are none, tell the user: "No mutants need review. All are either valid or stale."

### 2. For each needs-review mutant

Read the mutant's patch file from `.mutants/patches/NNN.patch`.

Read the **current version** of the source file the mutant targets.

Evaluate:

1. **Does the mutation still target the same logical code?** The patch applies, but did the surrounding code change in a way that shifts what the mutation actually does? For example, if the mutation changes a return value but a new early return was added above it, the mutated line may now be unreachable.

2. **Is the mutation still semantically different from the original?** Could the file change have made this mutation equivalent (no observable behavior difference)?

3. **Is the mutation still a realistic bug?** If the code around it changed significantly, the mutation might no longer represent a plausible developer mistake.

### 3. Decide: promote or discard

For each mutant, set the status:

- **`pending`** — the mutation is still valid. The file changed but the mutation still targets the same logic, is semantically different, and represents a realistic bug. Update `validation_note` to briefly explain why it's still valid.

- **`stale`** — the mutation is no longer meaningful. Update `validation_note` to explain why (e.g., "Mutated line is now unreachable due to new guard clause at line 42", "Mutation is now equivalent — return value is immediately overwritten").

### 4. Update file hashes

After reviewing all mutants for a file, update the `file_hashes` entry to the current SHA-256 so future validations don't re-flag these mutants.

Compute with: `sha256sum <file> | cut -d' ' -f1`

### 5. Save and report

Write the updated manifest to disk.

Report to the user:

```
Validation review complete:
  Promoted: 4 mutants (still valid)
  Discarded: 2 mutants (now stale)

Promoted mutants are ready to test. Run mx-test.py or /mx-test.
Stale mutants can be regenerated with /mx-generate.
```
