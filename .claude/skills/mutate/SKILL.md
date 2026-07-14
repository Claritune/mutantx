---
name: mutate
description: AI-powered mutation testing — generate code mutants, run tests against them, and report a mutation score that reveals gaps in test coverage.
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

## Workflow Overview

```
Phase 1: Detect project setup (language, test command, source files)
Phase 2: Generate mutants (or load from cache)
Phase 3: Test each mutant (apply patch → run tests → revert)
Phase 4: Report results (mutation score + survived mutant analysis)
```

---

## Phase 1: Project Detection

If arguments are not provided, auto-detect the project configuration.

### Language & Test Command Detection

Check for these files in order and use the first match:

| Indicator File     | Language     | Default Test Command       | Default Source Pattern            |
|--------------------|--------------|----------------------------|----------------------------------|
| `package.json`     | JavaScript/TypeScript | Read `scripts.test` from package.json; fall back to `npx jest` or `npx vitest run` | `src/**/*.{ts,tsx,js,jsx}` minus `**/*.{test,spec}.*` and `**/__tests__/**` |
| `pyproject.toml`   | Python       | `pytest`                   | `src/**/*.py` or `**/*.py` minus `**/test_*` and `**/*_test.py` and `**/tests/**` |
| `Cargo.toml`       | Rust         | `cargo test`               | `src/**/*.rs` minus test modules |
| `go.mod`           | Go           | `go test ./...`            | `**/*.go` minus `*_test.go`      |
| `pom.xml`          | Java (Maven) | `mvn test`                 | `src/main/**/*.java`             |
| `build.gradle`     | Java (Gradle)| `./gradlew test`           | `src/main/**/*.java`             |
| `*.sln` or `*.csproj` | C#        | `dotnet test`              | `**/*.cs` minus `**/Tests/**` and `**/*.Tests/**` |
| `mix.exs`          | Elixir       | `mix test`                 | `lib/**/*.ex`                    |
| `Gemfile`          | Ruby         | `bundle exec rspec` or `rake test` | `lib/**/*.rb` or `app/**/*.rb` |

If no indicator is found, ask the user for the language, test command, and source file patterns.

### Source File Selection

After identifying source files:
1. **Exclude test files** — files matching test patterns for the detected language.
2. **Exclude generated/vendored code** — `node_modules/`, `vendor/`, `dist/`, `build/`, `.git/`, `target/`, `__pycache__/`.
3. **Exclude config files** — `*.config.*`, `*.json`, `*.yaml`, `*.yml`, `*.toml`, `*.xml` (unless they contain business logic).
4. **Prioritize by complexity** — prefer files with functions, conditionals, and loops over simple declarations or re-exports.

If the user provides `files`, use that pattern instead of auto-detection, but still apply exclusions for test and generated files.

List the detected configuration to the user before proceeding:
```
Detected: TypeScript project
Test command: npm test
Source files: 12 files in src/ (excluding tests)
```

---

## Phase 2: Mutant Generation

### Check for Cached Mutants

Look for `.mutants/manifest.json` in the project root.

If `.mutants/` does not exist or `regen` is `"true"`, proceed with full generation.

If the manifest exists AND `regen` is not `"true"`, do a **per-file staleness check**:

1. Read the manifest. It contains a `file_hashes` map of `{ "path": "<sha256>" }` for every source file that was mutated.
2. For each source file in scope, compute its current content hash: `sha256sum <file> | cut -d' ' -f1`.
3. Compare against the stored hash:
   - **Hash matches** → the file hasn't changed. Keep its existing mutants and skip regeneration for this file.
   - **Hash differs** → the file has changed. Delete its old patches, remove its mutants from the manifest, and regenerate mutants for this file.
   - **File is new** (not in `file_hashes`) → generate mutants for it.
   - **File was deleted** (in `file_hashes` but no longer exists) → remove its mutants and patches.
4. Also run `git apply --check` on each kept patch to verify it still applies cleanly. If a patch no longer applies (e.g., due to upstream changes not reflected in the hash, or manual edits), discard that mutant and regenerate.

Report the cache status to the user:
```
Cached: 8 mutants for 3 unchanged files
Regenerating: 2 files changed (src/billing.ts, src/auth.ts)
New: 1 file added (src/payments.ts)
Removed: 1 file deleted (src/legacy.ts)
```

This per-file approach avoids re-running expensive LLM generation for unchanged files while ensuring mutants stay valid.

### Generating Mutants

For each selected source file, read the full file and generate up to `count` (default 5) mutants. Each mutant must:
- Change exactly ONE thing (single fault).
- Be syntactically valid (the code must still compile/parse).
- Be semantically different from the original (NOT an equivalent mutant).
- Represent a realistic bug.

#### Mutation Categories

Apply a MIX of these categories across the file. Don't generate all mutants from the same category.

| Category | Description | Example |
|----------|-------------|---------|
| **Arithmetic Operator** | Change `+` to `-`, `*` to `/`, etc. | `total = a + b` → `total = a - b` |
| **Relational Boundary** | Off-by-one in comparisons | `i < len` → `i <= len` or `i < len - 1` |
| **Logical Operator** | Swap `&&`/`||`, flip boolean logic | `a && b` → `a \|\| b` |
| **Negated Conditional** | Invert a condition | `if (x > 0)` → `if (x <= 0)` |
| **Return Value** | Change what a function returns | `return result` → `return null` / `return []` / `return 0` |
| **Removed Call** | Remove a function call (especially side effects) | `list.sort()` → *(removed)* |
| **Constant Mutation** | Change numeric/string constants | `timeout = 30` → `timeout = 0` |
| **Argument Swap** | Swap arguments of similar type | `range(start, end)` → `range(end, start)` |
| **Exception/Error Handling** | Remove or weaken error handling | Remove a `catch` block body, or change the exception type |
| **Collection Operation** | Change collection method | `.filter(...)` → `.map(...)` or `.find(...)` |
| **Early Return** | Add or remove an early return | Insert `return` before main logic, or remove a guard clause |
| **Null/Undefined Injection** | Return or assign null/nil/None/undefined | `getUser()` → `null` |

#### What NOT to Mutate

- **Type declarations, interfaces, or type annotations** — these are compile-time only and produce trivially caught or equivalent mutants.
- **Import/export statements** — mutations here typically cause parse/compile errors, not behavioral bugs.
- **Comments or documentation.**
- **Logging or debug statements** — unless they affect control flow.
- **Configuration constants** that are only used at startup — hard to test meaningfully.
- **Dead code** that is never reached by any execution path.

#### Quality Checks

Before finalizing a mutant, verify:
1. **Not equivalent**: Does this mutation actually change observable behavior? If a variable is overwritten immediately after, mutating its assignment is equivalent.
2. **Not trivially caught**: Will this mutation cause a compile/type error rather than a behavioral change? If so, it's not a useful mutant.
3. **Testable**: Is there a plausible test that COULD catch this? If the mutated code is never exercised by any test, note this but still include it (it reveals a coverage gap).

### Saving Mutants

Create the following directory structure:

```
.mutants/
├── manifest.json
└── patches/
    ├── 001.patch
    ├── 002.patch
    └── ...
```

#### Patch Files

Each patch file is a unified diff that can be applied with `git apply`. Generate it using this format:

```diff
--- a/src/utils.ts
+++ b/src/utils.ts
@@ -40,7 +40,7 @@
 function calculateTotal(items: Item[]): number {
   let total = 0;
   for (const item of items) {
-    total += item.price * item.quantity;
+    total += item.price + item.quantity;
   }
   return total;
 }
```

To create the patch: after deciding on the mutation, produce the unified diff yourself directly. You understand the file content and can write the diff accurately. Use correct line numbers and context lines (3 lines of context above and below the change).

Verify each patch applies cleanly by running `git apply --check .mutants/patches/NNN.patch` before saving it. If it doesn't apply cleanly, fix the patch.

#### Manifest File

Write `.mutants/manifest.json` with this schema:

```json
{
  "version": 1,
  "generated_at": "<ISO 8601 timestamp>",
  "config": {
    "language": "<detected language>",
    "test_command": "<test command>",
    "source_patterns": ["<glob patterns used>"],
    "count_per_file": 5
  },
  "file_hashes": {
    "src/utils.ts": "<sha256 of file content at generation time>",
    "src/billing.ts": "<sha256>"
  },
  "mutants": [
    {
      "id": "001",
      "file": "src/utils.ts",
      "line": 42,
      "category": "arithmetic_operator",
      "description": "Changed * to + in price calculation within calculateTotal",
      "patch_file": "patches/001.patch",
      "status": "pending"
    }
  ],
  "summary": null
}
```

The `file_hashes` map stores the SHA-256 content hash of each source file at the time its mutants were generated. This is used for per-file cache invalidation — only files whose content actually changed need mutant regeneration. See "Check for Cached Mutants" above.

After saving all patches and the manifest, tell the user how many mutants were generated and in which files.

---

## Phase 3: Mutant Testing

### Pre-flight Checks

1. **Clean working tree**: Run `git status --porcelain`. If there are uncommitted changes, warn the user and ask whether to proceed. Applying patches on a dirty tree risks merge conflicts and lost work.

2. **Baseline test run**: Run the test command once on the unmodified code. If any tests fail, STOP and report: "Baseline tests are failing. Fix your tests before running mutation testing." Do not proceed — testing mutants against a failing baseline produces meaningless results.

### Test Loop

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

After each mutant, update the manifest on disk so progress is saved even if the process is interrupted.

### Resuming Interrupted Runs

If the manifest has some mutants with `status: "pending"` and others already tested, only test the pending ones. This allows resuming after an interruption without re-running already-tested mutants.

---

## Phase 4: Reporting

### Calculate the Mutation Score

```
mutation_score = killed / (killed + survived)
```

Exclude `skipped` and `error` mutants from the score. `timeout` counts as killed.

### Generate the Report

Write `.mutants/report.md` with the following structure:

```markdown
# MutantX — Mutation Testing Report

**Project:** <project name>
**Date:** <timestamp>
**Commit:** <short hash>

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

```diff
<the patch content>
```

**Why this matters:** <brief explanation of what kind of bug this represents and what could go wrong in production>

**Suggested test:** <concrete suggestion for a test that would catch this mutant>

(Repeat for each survived mutant)

## Killed Mutants ✓

<Brief table listing killed mutants — id, file, category, one-line description. No detailed patches needed.>

## Recommendations

<2-5 bullet points summarizing the most important test gaps found and what areas of the code need better test coverage. Be specific — reference file names and functionality.>
```

### Update the Manifest Summary

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

### Present Results to User

After writing the report, display a concise summary to the user:

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

- **No test files found**: Stop and tell the user. Mutation testing requires existing tests.
- **Very large projects**: If more than 30 source files are detected, ask the user to narrow scope with the `files` argument, or select the 10 most complex files automatically.
- **Compiled languages**: For Rust, Go, Java, C# — after applying a patch, the project must compile. If a mutant causes a compilation error, mark it as `"killed (compile error)"` and count it as killed (the compiler caught it, even if no test did). But try to avoid generating mutants that don't compile.
- **Monorepos**: If a `files` pattern is provided, only run tests relevant to the mutated package/module if possible.
- **Tests with side effects**: Warn the user if the test command appears to involve deployment, database modifications, or external API calls.

## .gitignore

After creating the `.mutants/` directory, check if `.mutants/` is in `.gitignore`. If not, ask the user whether they want to add it. The patches and reports are typically local development artifacts, but some teams may want to track them.
