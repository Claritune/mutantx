---
name: mx-test
description: "MutantX Phase 3 — Test each mutant by applying patches, running the test suite, and recording results."
user_invocable: true
arguments: []
---

# MutantX — Phase 3: Mutant Testing

This phase is handled by the deterministic Python script `mx-test.py`. It applies each mutant patch, runs the test suite, records results, and reverts — all without consuming AI tokens.

## How to Run

Locate `mx-test.py` from the MutantX installation. It is in the `scripts/` directory alongside the skills:

```bash
python3 ~/.claude/scripts/mx-test.py
```

Or if MutantX is installed at a known path:

```bash
python3 /path/to/mutantx/src/scripts/mx-test.py
```

### Options

| Flag | Description |
|------|-------------|
| `--mutants-dir PATH` | Path to the `.mutants/` directory (default: `.mutants`) |
| `--timeout N` | Test command timeout in seconds (default: 120) |
| `--skip-baseline` | Skip the baseline test run |
| `--no-clean-check` | Skip the clean working tree check |

## What the Script Does

1. **Pre-flight checks:**
   - Verifies the working tree is clean (no uncommitted changes)
   - Runs baseline tests to confirm they pass on unmodified code

2. **For each pending mutant:**
   - Applies the patch: `git apply .mutants/patches/NNN.patch`
   - Runs the test command with a timeout
   - Records the result: killed, survived, timeout, or skipped
   - Reverts the patch: `git apply -R .mutants/patches/NNN.patch`
   - Saves progress to `manifest.json` after each mutant

3. **Supports resuming** — only tests mutants with `status: "pending"`

## When Invoked as a Skill

If the user runs `/mx-test`, execute the script using the Bash tool:

```bash
python3 <path-to-mx-test.py> --mutants-dir .mutants
```

Find `mx-test.py` by checking these locations in order:
1. `./src/scripts/mx-test.py` (if inside the MutantX repo)
2. `~/.claude/scripts/mx-test.py` (global install)

Display the script output to the user as it runs.
