# MutantX Tutorial

A complete guide to installing, using, and extending MutantX — AI-powered mutation testing for Claude Code.

---

## Table of Contents

- [What Is Mutation Testing?](#what-is-mutation-testing)
- [How MutantX Is Different](#how-mutantx-is-different)
- [Architecture Overview](#architecture-overview)
- [Installation](#installation)
- [Your First Mutation Test](#your-first-mutation-test)
- [Understanding the Output](#understanding-the-output)
- [The Four Phases in Detail](#the-four-phases-in-detail)
  - [Phase 1: Detection](#phase-1-detection)
  - [Phase 2: Generation](#phase-2-generation)
  - [Validation](#validation)
  - [Phase 3: Testing](#phase-3-testing)
  - [Phase 4: Reporting](#phase-4-reporting)
- [Manual Mutations](#manual-mutations)
- [Caching and Incremental Runs](#caching-and-incremental-runs)
- [Standalone Scripts Reference](#standalone-scripts-reference)
- [Skills Reference](#skills-reference)
- [Common Workflows](#common-workflows)
- [Interpreting Your Score](#interpreting-your-score)
- [Working with the Demo Projects](#working-with-the-demo-projects)
- [Troubleshooting](#troubleshooting)
- [Extending MutantX](#extending-mutantx)

---

## What Is Mutation Testing?

Code coverage tells you which lines of code execute during tests. But it doesn't tell you whether your tests would actually *catch a bug* on those lines. You can have 100% coverage and still miss critical bugs — if your assertions are weak or your edge cases are untested.

Mutation testing answers a harder question: **if a bug existed in your code, would your tests catch it?**

Here's how it works:

1. **Inject a bug** (called a "mutant") into your source code — for example, change `+` to `-` or `<` to `<=`
2. **Run your tests** against the mutated code
3. **If tests fail** → the mutant is "killed" — your tests caught the bug ✓
4. **If tests pass** → the mutant "survived" — your tests missed it ✗

The **mutation score** is the percentage of mutants killed. A score of 85% means your tests catch 85% of injected bugs. The surviving 15% represent real gaps in your test coverage — places where a bug could hide and your tests wouldn't notice.

---

## How MutantX Is Different

Traditional mutation tools (Stryker, PIT, mutmut) use AST-based transformations — they mechanically replace every `+` with `-`, every `<` with `<=`, every `true` with `false`. This creates problems:

- **Equivalent mutants** (4–39% of all mutants) don't change behavior but waste your time
- **Trivial mutants** cause compile errors rather than behavioral bugs
- **No prioritization** — they mutate boilerplate and config alongside business logic
- **Thousands of mutants**, most uninteresting

MutantX uses AI to understand your code semantically. It generates mutations that represent realistic bugs a developer might actually introduce:

- Off-by-one errors in boundary conditions
- Swapped arguments of the same type (latitude/longitude, start/end)
- Forgotten null checks
- Removed side-effect calls (forgetting to save, sort, or validate)
- Weakened error handling

The result is fewer, higher-quality mutants that reveal real test gaps, with actionable suggestions for closing them.

---

## Architecture Overview

MutantX is built on a key design principle: **only spend AI tokens when intelligence is needed**.

```
Phase 1: Detect    ─── AI ──── identify language, test command, source files
Phase 2: Generate  ─── AI ──── read code, create mutation patches
     Validate      ─── hybrid ─ deterministic check + optional AI review
Phase 3: Test      ─── script ─ apply patch → run tests → record → revert
Phase 4: Report    ─── hybrid ─ deterministic stats + AI analysis of survivors
```

Once mutants are generated and cached as patch files, **repeated testing costs zero tokens**. The test runner and report generator are plain Python scripts (stdlib only, no pip packages) that work on Mac, Linux, and Windows.

### What Gets Created

All artifacts live in a `.mutants/` directory in the target project:

```
.mutants/
├── detect.json          # Project detection results
├── manifest.json        # Mutant metadata, file hashes, test results
├── report.md            # Human-readable report
└── patches/
    ├── 001.patch        # Unified diff — one per mutant
    ├── 002.patch
    └── ...
```

---

## Installation

### Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (for AI-powered phases)
- [Python 3.10+](https://www.python.org/) (for deterministic scripts — stdlib only, no packages to install)
- [Git](https://git-scm.com/) (for patch application and reversion)

### User-Level Install (All Projects)

```bash
git clone https://github.com/user/mutantx.git
cd mutantx

# Install skills (AI-powered phases)
cp -r src/skills/* ~/.claude/skills/

# Install scripts (deterministic phases)
mkdir -p ~/.claude/scripts
cp src/scripts/*.py ~/.claude/scripts/

# Optional: install the autonomous agent
mkdir -p ~/.claude/agents
cp src/agents/mx-agent.md ~/.claude/agents/
```

### Project-Level Install (Single Project)

```bash
cp -r src/skills/* your-project/.claude/skills/
mkdir -p your-project/.claude/scripts
cp src/scripts/*.py your-project/.claude/scripts/
```

### Verify

Open Claude Code in any project and type `/mutate` — it should appear in the skill autocomplete.

---

## Your First Mutation Test

The fastest way to see MutantX in action is with one of the included demo projects.

### Using the Python Demo

```bash
cd mutantx/demos/python

# Verify tests pass
pytest
# => 7 passed

# Open Claude Code and run mutation testing
# Type: /mutate
```

MutantX will:
1. Detect Python, `pytest` as the test command, and `calculator.py` as the source file
2. Generate ~5 mutants (realistic bugs) as patch files
3. Apply each patch, run `pytest`, record if tests catch it, revert
4. Produce a report showing which bugs survived and what tests to add

### Using the C++ Demo

```bash
cd mutantx/demos/cpp

# Verify tests pass
make test
# => All tests passed!

# In Claude Code, type:
# /mutate test-cmd="make test"
```

### Using Your Own Project

```bash
cd your-project

# In Claude Code:
# /mutate
```

MutantX auto-detects the language, test command, and source files. No configuration needed for supported languages.

To target specific files or use a custom test command:

```
/mutate files="src/billing/**/*.py" test-cmd="pytest tests/unit -x" count="8"
```

---

## Understanding the Output

After a run, MutantX displays a summary like this:

```
Mutation Testing Complete!

Score: 71% (5 killed / 7 testable)
Survived: 2 mutants — see .mutants/report.md for details

Top gaps:
  - calculator.py: percentage() has zero test coverage
  - calculator.py: divide() exception path is not tested
```

### The Report

Open `.mutants/report.md` for the full report. It contains:

**Summary table** — total mutants, killed, survived, timeout, skipped, and the mutation score.

**Survived mutants** — the most important section. For each bug your tests missed:
- The exact diff showing what was changed
- Why this matters (what kind of bug it represents)
- A suggested test to catch it (concrete, copy-pasteable)

**Killed mutants** — a compact table confirming which bugs your tests caught.

**Recommendations** — prioritized list of areas needing better coverage.

### The Manifest

`.mutants/manifest.json` contains machine-readable metadata: every mutant's ID, file, line, category, description, status, and test output. This is what the scripts read and write.

---

## The Four Phases in Detail

### Phase 1: Detection

**Skill:** `/mx-detect`
**Uses AI:** Yes
**What it does:** Identifies your project's language, test command, and source files.

MutantX scans for indicator files in this order:

| Indicator File | Language | Default Test Command |
|---|---|---|
| `package.json` | JavaScript / TypeScript | reads `scripts.test`, falls back to `npx jest` or `npx vitest run` |
| `pyproject.toml` / `setup.py` / `requirements.txt` | Python | `pytest` |
| `Cargo.toml` | Rust | `cargo test` |
| `go.mod` | Go | `go test ./...` |
| `pom.xml` | Java (Maven) | `mvn test` |
| `build.gradle` | Java (Gradle) | `./gradlew test` |
| `*.sln` / `*.csproj` | C# | `dotnet test` |
| `CMakeLists.txt` / `Makefile` | C / C++ | `cmake --build . && ctest` or `make test` |
| `mix.exs` | Elixir | `mix test` |
| `Gemfile` | Ruby | `bundle exec rspec` |

**Source file selection** excludes:
- Test files (e.g., `test_*.py`, `*.test.ts`, `*_test.go`)
- Generated/vendored code (`node_modules/`, `vendor/`, `dist/`, `build/`, `target/`, `__pycache__/`)
- Config files (`*.json`, `*.yaml`, `*.toml`, `*.xml`)
- Files prioritized by complexity — functions with conditionals and loops are preferred over simple declarations

**For large projects** (>30 source files), MutantX asks you to narrow scope with the `files` argument or auto-selects the 10 most complex files.

**Output:** Writes `.mutants/detect.json` and displays the detected configuration.

**Overriding detection:** Pass `files` and/or `test-cmd` arguments to skip auto-detection:

```
/mutate files="lib/**/*.rb" test-cmd="bundle exec rspec spec/unit"
```

---

### Phase 2: Generation

**Skill:** `/mx-generate`
**Uses AI:** Yes
**What it does:** Reads source files and generates mutation patches.

For each source file, the AI generates up to `count` (default: 5) mutants across 12 categories:

| Category | What It Does | Example |
|---|---|---|
| Arithmetic Operator | Changes `+` to `-`, `*` to `/` | `a + b` → `a - b` |
| Relational Boundary | Off-by-one in comparisons | `i < len` → `i <= len` |
| Logical Operator | Swaps `&&`/`||` | `a && b` → `a \|\| b` |
| Negated Conditional | Inverts a condition | `if (x > 0)` → `if (x <= 0)` |
| Return Value | Changes function returns | `return result` → `return null` |
| Removed Call | Removes a function call | `list.sort()` → *(removed)* |
| Constant Mutation | Changes numeric/string constants | `timeout = 30` → `timeout = 0` |
| Argument Swap | Swaps same-type arguments | `range(start, end)` → `range(end, start)` |
| Exception Handling | Weakens error handling | Empties a `catch` block |
| Collection Operation | Changes collection methods | `.filter(...)` → `.map(...)` |
| Early Return | Adds/removes early returns | Removes a guard clause |
| Null Injection | Injects null/nil/None | `getUser()` → `null` |

**What it skips:** Type declarations, imports, comments, logging statements, dead code, and startup-only configuration constants.

**Quality checks for each mutant:**
1. Is it semantically different from the original? (not equivalent)
2. Does it compile/parse? (syntactically valid)
3. Does it represent a realistic bug? (not trivially caught)

Each mutant is saved as a unified diff patch in `.mutants/patches/NNN.patch` and verified with `git apply --check`.

**Patch format:**

```diff
--- a/src/calculator.py
+++ b/src/calculator.py
@@ -5,7 +5,7 @@
 
 def add(a: float, b: float) -> float:
     """Return the sum of two numbers."""
-    return a + b
+    return a - b
 
 
 def subtract(a: float, b: float) -> float:
```

---

### Validation

**Script:** `mx-validate.py` (deterministic, zero tokens)
**Skill:** `/mx-validate` (AI review for ambiguous cases)

Validation answers the question: **are the cached mutants still valid after source files changed?**

It runs automatically before testing (called by `mx-test.py`). Each mutant gets one of three verdicts:

| Verdict | When | What Happens |
|---|---|---|
| **valid** | File unchanged and patch applies | Status set to `pending` — ready to test |
| **stale** | Patch no longer applies, or file was deleted | Status set to `stale` — needs regeneration |
| **needs-review** | File changed but patch still applies | Status set to `needs-review` — semantically ambiguous |

**The "needs-review" case** is the interesting one. The patch applies cleanly (the code around the mutation didn't change enough to break context), but the file *did* change. Maybe a new early return was added above the mutation site, making it unreachable. Maybe the function's purpose changed entirely.

You have three options for handling needs-review mutants:

**Option 1: AI review (recommended)**
```
/mx-validate
```
The AI reads each flagged patch and the current source file, then decides if the mutation is still meaningful. Tokens are spent only for changed files.

**Option 2: Trust the patches (zero tokens)**
```bash
python3 ~/.claude/scripts/mx-validate.py --promote
```
Promotes all needs-review mutants to pending and updates file hashes. Use this when you know the changes are minor (formatting, comments, unrelated code).

**Option 3: Regenerate**
```
/mx-generate regen="true"
```
Full regeneration, ignoring cache entirely. Most expensive but guaranteed fresh.

---

### Phase 3: Testing

**Script:** `mx-test.py` (deterministic, zero tokens)
**What it does:** Applies each patch, runs the test suite, records results, reverts.

This is the core of the zero-token promise. Once mutants are generated as patch files, testing is purely mechanical:

1. **Pre-flight checks:**
   - Verifies the working tree is clean (no uncommitted changes)
   - Runs the test suite on unmodified code — if baseline tests fail, stops immediately

2. **For each pending mutant:**
   ```
   git apply .mutants/patches/001.patch    # inject the bug
   pytest                                  # run tests
   git apply -R .mutants/patches/001.patch # revert the bug
   ```

3. **Records the result:**
   - Tests **failed** → mutant is **killed** ✓ (your tests caught the bug)
   - Tests **passed** → mutant **survived** ✗ (your tests missed it)
   - Tests **timed out** → mutant is **killed (timeout)** ✓ (likely an infinite loop)
   - Patch **failed to apply** → mutant is **skipped**

4. **Saves progress** to `manifest.json` after each mutant. If interrupted (Ctrl+C, crash, timeout), re-running picks up where it left off.

**Progress display:**
```
[1/15] Mutant 001: arithmetic_operator in calculator.py:6 ... killed ✓
[2/15] Mutant 002: return_value in calculator.py:18 ... survived ✗
[3/15] Mutant 003: negated_conditional in calculator.py:30 ... killed ✓
...
```

**You can re-run testing as many times as you want** — after fixing tests, after refactoring, after adding new tests — without spending any AI tokens. Just run:

```bash
python3 ~/.claude/scripts/mx-test.py
```

---

### Phase 4: Reporting

**Script:** `mx-report.py` (deterministic stats, zero tokens)
**Skill:** `/mx-report` (AI analysis of survived mutants)

Reporting has two layers:

**Layer 1: Deterministic (zero tokens)**

`mx-report.py` generates `.mutants/report.md` with:
- Summary table (total, killed, survived, timeout, skipped, score)
- Full patch diffs for each survived mutant
- Killed mutants table
- Manifest summary update

**Layer 2: AI analysis (tokens, but high value)**

The `/mx-report` skill reads the generated report and adds to each survived mutant:

- **"Why this matters"** — what kind of bug this represents and what could go wrong in production
- **"Suggested test"** — a concrete, copy-pasteable test case in your language and framework
- **Recommendations** — 2-5 prioritized bullet points about what to test next

The AI layer is optional. You can run just `mx-report.py` to get the mechanical report and review survived patches yourself.

---

## Manual Mutations

You can add your own mutations alongside AI-generated ones. This is useful when you want to test a specific "what if" scenario.

### Workflow

```bash
# 1. Edit a file to introduce the bug you want to test
#    For example, change a < to <= in a boundary check
vim src/billing.py

# 2. Capture it — the script saves the diff and reverts the file
python3 ~/.claude/scripts/mx-capture.py -d "Off-by-one in invoice threshold"

# 3. The file is now back to its original state, but the patch is saved
#    You can verify:
cat .mutants/patches/001.patch

# 4. Test it alongside any AI-generated mutants
python3 ~/.claude/scripts/mx-test.py
```

### Multiple Edits

If you change multiple files before running `mx-capture.py`, each file gets its own mutation. The script prompts for a description of each one:

```
Found changes in 2 file(s):
  src/billing.py
  src/auth.py

Mutation in src/billing.py (line 42):
    -    if total > threshold:
    +    if total >= threshold:
  Description: Off-by-one in threshold check
  Captured mutant 001: Off-by-one in threshold check

Mutation in src/auth.py (line 18):
    -    if token.expires_at > now:
    +    if token.expires_at >= now:
  Description: Token boundary check
  Captured mutant 002: Token boundary check

2 mutation(s) captured.
File(s) reverted to original state.
```

### Keeping the Edit

Use `--keep` to leave the file modified after capture:

```bash
python3 ~/.claude/scripts/mx-capture.py --keep -d "Testing with the edit still applied"
```

Remember to revert before running `mx-test.py` — the test runner checks for a clean working tree.

### Mixing Manual and AI Mutations

Manual and AI-generated mutations coexist in the same manifest. Manual ones have `category: "manual"`. You can:

1. Generate AI mutations: `/mx-generate`
2. Add manual ones: `mx-capture.py`
3. Test everything together: `mx-test.py`

---

## Caching and Incremental Runs

MutantX uses per-file caching to avoid regenerating mutants unnecessarily.

### How It Works

When mutants are generated, the SHA-256 hash of each source file is stored in `manifest.json`:

```json
"file_hashes": {
  "src/billing.py": "a1b2c3d4e5f6...",
  "src/auth.py": "f6e5d4c3b2a1..."
}
```

On subsequent runs, MutantX compares stored hashes against current file content:

| Scenario | Action | Tokens? |
|---|---|---|
| File unchanged | Reuse existing mutants | No |
| File changed | Regenerate only that file's mutants | Yes (proportional to file) |
| New file added | Generate new mutants | Yes |
| File deleted | Remove its mutants and patches | No |

This means editing one file in a 20-file project only regenerates mutants for that one file.

### Cache Report

When running with cached mutants, you'll see:

```
Cached: 15 mutants for 6 unchanged files
Regenerating: 1 file changed (src/billing.py)
New: 1 file added (src/payments.py)
Removed: 1 file deleted (src/legacy.py)
```

### When to Force Regeneration

Use `regen="true"` when:
- You've refactored heavily and want fresh mutants
- You increased `count` and want more mutants per file
- You suspect cached mutants aren't covering the right areas

```
/mutate regen="true"
```

### Re-testing After Adding Tests

This is where caching shines. After adding tests to catch survived mutants:

```bash
# Reset test results (set all statuses back to pending)
# Then re-test with zero tokens:
python3 ~/.claude/scripts/mx-test.py
```

Note: `mx-test.py` only tests mutants with `status: "pending"`. If you want to re-test killed/survived mutants, you'll need to reset their status in `manifest.json` (or run `/mx-generate regen="true"` to start fresh).

---

## Standalone Scripts Reference

All scripts are in `src/scripts/` and use only Python's standard library. No `pip install` needed.

### mx-capture.py

Captures uncommitted file changes as mutation patches.

```
Usage: python3 mx-capture.py [OPTIONS]

Options:
  --mutants-dir PATH    Mutants directory (default: .mutants)
  -d, --description TEXT  Mutation description (prompted if omitted)
  --keep                Don't revert files after capture
```

**Reads:** Git working tree diff
**Writes:** `.mutants/patches/NNN.patch`, updates `manifest.json`
**Exit codes:** 0 (success or no changes found), 1 (git error)

### mx-validate.py

Checks whether mutants are still valid against current source files.

```
Usage: python3 mx-validate.py [OPTIONS]

Options:
  --mutants-dir PATH    Mutants directory (default: .mutants)
  --json                Output as JSON
  --promote             Promote needs-review to pending without AI
```

**Reads:** `manifest.json`, source files, patch files
**Writes:** Updates `manifest.json` statuses
**Exit codes:** 0 (complete), 1 (manifest not found)

### mx-test.py

Applies patches, runs tests, records results. Zero AI tokens.

```
Usage: python3 mx-test.py [OPTIONS]

Options:
  --mutants-dir PATH    Mutants directory (default: .mutants)
  --timeout N           Test timeout in seconds (default: 120)
  --skip-baseline       Skip baseline test run
  --no-clean-check      Skip working tree check
  --skip-validation     Skip pre-test validation
```

**Reads:** `manifest.json`, `detect.json`, patch files
**Writes:** Updates `manifest.json` with test results
**Exit codes:** 0 (testing complete), 1 (manifest missing, baseline fails, dirty tree)

### mx-report.py

Calculates mutation score and generates the report. Zero AI tokens.

```
Usage: python3 mx-report.py [OPTIONS]

Options:
  --mutants-dir PATH    Mutants directory (default: .mutants)
```

**Reads:** `manifest.json`, patch files
**Writes:** `.mutants/report.md`, updates `manifest.json` summary
**Exit codes:** 0 (report generated), 1 (manifest not found)

---

## Skills Reference

Skills are Claude Code instruction files that guide the AI through each phase. They live in `src/skills/` and are installed to `~/.claude/skills/`.

| Skill | Purpose | Uses AI? | Arguments |
|---|---|---|---|
| `/mutate` | Full run — all phases in sequence | Yes | `files`, `test-cmd`, `count`, `regen` |
| `/mx-detect` | Phase 1: detect project setup | Yes | `files`, `test-cmd` |
| `/mx-generate` | Phase 2: generate mutation patches | Yes | `files`, `count`, `regen` |
| `/mx-validate` | Review needs-review mutants | Yes | (none) |
| `/mx-test` | Phase 3: invoke `mx-test.py` | No | (none) |
| `/mx-report` | Phase 4: invoke `mx-report.py` + AI analysis | Partial | (none) |

### Autonomous Agent

The `mx-agent` runs the full cycle without user interaction:

```
@mx-agent
```

It uses Sonnet for cost efficiency and handles all four phases plus validation autonomously.

---

## Common Workflows

### One-Shot Full Test

```
/mutate
```

Runs everything: detect → generate → validate → test → report.

### Target Specific Files

```
/mutate files="src/billing/**/*.py" count="10"
```

Generates up to 10 mutants per file in the billing module.

### Custom Test Command

```
/mutate test-cmd="npm run test:unit -- --bail"
```

### Re-test After Adding Tests

```bash
# Your mutants are already generated and cached
# Just re-run the test script (zero tokens):
python3 ~/.claude/scripts/mx-test.py
```

### Resume Interrupted Run

```bash
# Picks up where it left off — only tests pending mutants
python3 ~/.claude/scripts/mx-test.py
```

### Force Regeneration

```
/mutate regen="true"
```

### Add a Manual Mutation

```bash
vim src/billing.py                    # make your edit
python3 ~/.claude/scripts/mx-capture.py -d "Removed discount cap"
python3 ~/.claude/scripts/mx-test.py  # test everything
```

### Just Validate (No Testing)

```bash
python3 ~/.claude/scripts/mx-validate.py
# or for AI review:
/mx-validate
```

### Get a Report Without AI

```bash
python3 ~/.claude/scripts/mx-report.py
# Report is at .mutants/report.md — review manually
```

### Full Pipeline Without Claude Code

After initial generation (which requires Claude Code), you can run the rest from the terminal:

```bash
python3 ~/.claude/scripts/mx-validate.py          # check validity
python3 ~/.claude/scripts/mx-validate.py --promote # promote if needed
python3 ~/.claude/scripts/mx-test.py               # test
python3 ~/.claude/scripts/mx-report.py             # report
```

---

## Interpreting Your Score

### Score Ranges

| Score | Assessment | What It Means |
|---|---|---|
| **> 80%** | Strong | Your tests catch most realistic bugs. Focus on the surviving mutants — they're the highest-value test gaps. |
| **60–80%** | Moderate | Meaningful gaps exist. Look for patterns: are survivors clustered in one file? One category? |
| **< 60%** | Weak | Many realistic bugs would go undetected. Start with the files that have the most survivors. |

### What Survived Mutants Tell You

Each surviving mutant is a specific, concrete test gap. The report tells you:
- **What was changed** (the exact diff)
- **Where** (file and line number)
- **Category** (what kind of bug it represents)

Common patterns:

- **Many "return value" survivors** → your tests don't assert on return values, or they only check the happy path
- **Many "boundary" survivors** → you're not testing edge cases (off-by-one, empty inputs, zero values)
- **Many "exception handling" survivors** → you're not testing error paths
- **A file with all survivors** → that file has little or no test coverage

### When 100% Is Suspicious

A 100% mutation score might mean:
- Your tests are genuinely thorough (great!)
- The `count` is too low — increase it for more challenging mutants
- The mutants aren't diverse enough — try `regen="true"` for fresh ones

### When 0% Is Expected

A 0% score usually means:
- Baseline tests are failing (fix them first)
- The test command isn't running the right tests
- Source files have no testable logic (only config, types, or re-exports)

---

## Working with the Demo Projects

### Python Demo

**Location:** `demos/python/`
**Files:** `calculator.py` (8 functions), `test_calculator.py` (7 tests)
**Setup:** `pip install pytest`

The demo has these intentional gaps:

| Function | What's Tested | What's Missing |
|---|---|---|
| `add(a, b)` | Basic sum | — |
| `subtract(a, b)` | Basic difference | — |
| `multiply(a, b)` | Basic product | — |
| `divide(a, b)` | Normal division | Division by zero exception |
| `percentage(value, total)` | *Nothing* | Zero test coverage |
| `apply_discount(price, pct)` | Normal discount | Boundaries: 0%, 100%, negative, >100% |
| `compound_interest(...)` | Normal case | Zero principal, zero rate |
| `split_bill(total, people, tip)` | Normal split | Zero tip, edge cases |

Running MutantX on this demo will produce a mutation score well below 80%, with survived mutants pointing exactly to these gaps.

```bash
cd demos/python
/mutate
```

### C++ Demo

**Location:** `demos/cpp/`
**Files:** `calculator.h`, `calculator.cpp` (9 functions), `test_calculator.cpp`
**Setup:** `make` (requires g++ with C++17)

Intentional gaps:

| Function | What's Tested | What's Missing |
|---|---|---|
| `Calculator::add` | Basic sum | — |
| `Calculator::subtract` | Basic difference | — |
| `Calculator::multiply` | Basic product | — |
| `Calculator::divide` | Normal division | Divide-by-zero exception |
| `clamp(val, min, max)` | *Nothing* | Zero test coverage |
| `factorial(n)` | *Nothing* | Zero test coverage |
| `fibonacci(n)` | Small values | Edge cases: fib(0), fib(1) |
| `gcd(a, b)` | Normal case | When one argument is 0 |
| `is_prime(n)` | A few primes | Boundaries: 0, 1, 2, negatives |

```bash
cd demos/cpp
/mutate test-cmd="make test"
```

---

## Troubleshooting

### "Baseline tests are failing"

MutantX refuses to test mutants if your existing tests don't pass. Fix your tests first:

```bash
# Run your test command manually and fix failures
pytest
# Then re-run
python3 ~/.claude/scripts/mx-test.py
```

### "Working tree has uncommitted changes"

The test runner won't apply patches on a dirty tree. Commit or stash your changes:

```bash
git stash
python3 ~/.claude/scripts/mx-test.py
git stash pop
```

Or bypass the check (at your own risk):

```bash
python3 ~/.claude/scripts/mx-test.py --no-clean-check
```

### Patches fail to apply

This happens when source files changed after mutants were generated. Run validation:

```bash
python3 ~/.claude/scripts/mx-validate.py
```

If mutants are stale, regenerate:

```
/mx-generate regen="true"
```

### Tests are slow

If each test run takes minutes, testing 50 mutants takes hours. Solutions:

- **Reduce `count`:** `/mutate count="3"` generates fewer mutants per file
- **Target specific files:** `/mutate files="src/critical-module/**/*.py"`
- **Use a faster test command:** `/mutate test-cmd="pytest tests/unit -x"` (the `-x` flag stops at first failure)
- **Lower the timeout:** `python3 mx-test.py --timeout 30`

### "No test command found"

MutantX couldn't detect your test setup. Provide it explicitly:

```
/mutate test-cmd="make test" files="src/**/*.cpp"
```

### Needs-review mutants blocking testing

When source files changed but patches still apply:

```bash
# Quick fix — trust the patches:
python3 ~/.claude/scripts/mx-validate.py --promote

# Or let AI review:
/mx-validate
```

---

## Extending MutantX

### Adding a New Mutation Category

Edit `src/skills/mx-generate/SKILL.md` and add to the Mutation Categories table:

```markdown
| **Your Category** | Description of what to change | `original` → `mutated` |
```

Include the category name, a clear description, and a concrete before/after example.

### Supporting a New Language

Edit `src/skills/mx-detect/SKILL.md` and add to the detection table:

```markdown
| `your-indicator-file` | Your Language | `your-test-command` | `your-source-pattern` |
```

### Adding a Demo Project

Create a new directory under `demos/` with:

1. Source code with enough logic to generate interesting mutations
2. Tests that deliberately miss some edge cases
3. A `README.md` explaining setup and expected gaps
4. A build/test command that exits 0 on success

See `demos/python/` and `demos/cpp/` for reference.

### Modifying Skills

Skills are markdown files that instruct the AI. Edit them directly:

```
src/skills/
├── mutate/SKILL.md       # Main orchestrator
├── mx-detect/SKILL.md    # Phase 1
├── mx-generate/SKILL.md  # Phase 2
├── mx-validate/SKILL.md  # Validation
├── mx-test/SKILL.md      # Phase 3
└── mx-report/SKILL.md    # Phase 4
```

After editing, copy to `~/.claude/skills/` to apply globally, or to your project's `.claude/skills/` for project-level changes.

### Modifying Scripts

Scripts are standard Python. Edit them in `src/scripts/` and copy to `~/.claude/scripts/`:

```
src/scripts/
├── mx-capture.py     # Manual mutation capture
├── mx-validate.py    # Mutation validation
├── mx-test.py        # Test runner
└── mx-report.py      # Report generator
```

No external packages are used — everything runs on Python's standard library.
