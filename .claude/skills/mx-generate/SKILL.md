---
name: mx-generate
description: "MutantX Phase 2 — Generate realistic code mutants as unified diff patches."
user_invocable: true
arguments:
  - name: files
    description: "Glob pattern(s) for source files to mutate. If omitted, reads from .mutants/detect.json."
    required: false
  - name: count
    description: "Maximum number of mutants to generate per source file. Default: 5."
    required: false
  - name: regen
    description: "Set to \"true\" to force regeneration of mutants, ignoring cached patches."
    required: false
---

# MutantX — Phase 2: Mutant Generation

You are the mutant generation phase of a mutation testing engine. Your job is to read source files and generate realistic code mutations as unified diff patches.

**Key principle:** You are NOT an AST-based tool applying blind syntactic transformations. You understand the code semantically. Generate mutations that represent realistic bugs a developer might actually introduce — off-by-one errors, wrong operator choices, forgotten edge cases, swapped arguments, missing null checks. Avoid trivial or equivalent mutations.

---

## Input

Read `.mutants/detect.json` for project configuration (language, test command, source files). If the file doesn't exist and `files` is not provided, tell the user to run `/mx-detect` first.

## Check for Cached Mutants

Look for `.mutants/manifest.json` in the project root.

If `.mutants/manifest.json` does not exist or `regen` is `"true"`, proceed with full generation.

If the manifest exists AND `regen` is not `"true"`, do a **per-file staleness check**:

1. Read the manifest. It contains a `file_hashes` map of `{ "path": "<sha256>" }` for every source file that was mutated.
2. For each source file in scope, compute its current content hash: `sha256sum <file> | cut -d' ' -f1`.
3. Compare against the stored hash:
   - **Hash matches** → the file hasn't changed. Keep its existing mutants and skip regeneration for this file.
   - **Hash differs** → the file has changed. Delete its old patches, remove its mutants from the manifest, and regenerate mutants for this file.
   - **File is new** (not in `file_hashes`) → generate mutants for it.
   - **File was deleted** (in `file_hashes` but no longer exists) → remove its mutants and patches.
4. Also run `git apply --check` on each kept patch to verify it still applies cleanly. If a patch no longer applies, discard that mutant and regenerate.

Report the cache status to the user:
```
Cached: 8 mutants for 3 unchanged files
Regenerating: 2 files changed (src/billing.ts, src/auth.ts)
New: 1 file added (src/payments.ts)
Removed: 1 file deleted (src/legacy.ts)
```

## Generating Mutants

For each source file, read the full file and generate up to `count` (default 5) mutants. Each mutant must:
- Change exactly ONE thing (single fault).
- Be syntactically valid (the code must still compile/parse).
- Be semantically different from the original (NOT an equivalent mutant).
- Represent a realistic bug.

### Mutation Categories

Apply a MIX of these categories across the file. Don't generate all mutants from the same category.

| Category | Description | Example |
|----------|-------------|---------|
| **Arithmetic Operator** | Change `+` to `-`, `*` to `/`, etc. | `total = a + b` → `total = a - b` |
| **Relational Boundary** | Off-by-one in comparisons | `i < len` → `i <= len` or `i < len - 1` |
| **Logical Operator** | Swap `&&`/`\|\|`, flip boolean logic | `a && b` → `a \|\| b` |
| **Negated Conditional** | Invert a condition | `if (x > 0)` → `if (x <= 0)` |
| **Return Value** | Change what a function returns | `return result` → `return null` / `return []` / `return 0` |
| **Removed Call** | Remove a function call (especially side effects) | `list.sort()` → *(removed)* |
| **Constant Mutation** | Change numeric/string constants | `timeout = 30` → `timeout = 0` |
| **Argument Swap** | Swap arguments of similar type | `range(start, end)` → `range(end, start)` |
| **Exception/Error Handling** | Remove or weaken error handling | Remove a `catch` block body, or change the exception type |
| **Collection Operation** | Change collection method | `.filter(...)` → `.map(...)` or `.find(...)` |
| **Early Return** | Add or remove an early return | Insert `return` before main logic, or remove a guard clause |
| **Null/Undefined Injection** | Return or assign null/nil/None/undefined | `getUser()` → `null` |

### What NOT to Mutate

- **Type declarations, interfaces, or type annotations** — compile-time only.
- **Import/export statements** — cause parse/compile errors, not behavioral bugs.
- **Comments or documentation.**
- **Logging or debug statements** — unless they affect control flow.
- **Configuration constants** only used at startup.
- **Dead code** never reached by any execution path.

### Quality Checks

Before finalizing a mutant, verify:
1. **Not equivalent**: Does this mutation actually change observable behavior?
2. **Not trivially caught**: Will this cause a compile/type error rather than a behavioral change?
3. **Testable**: Is there a plausible test that COULD catch this? If the mutated code is never exercised by any test, note this but still include it (it reveals a coverage gap).

## Saving Mutants

Create or update the following directory structure:

```
.mutants/
├── manifest.json
└── patches/
    ├── 001.patch
    ├── 002.patch
    └── ...
```

### Patch Files

Each patch file is a unified diff that can be applied with `git apply`:

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

Produce the unified diff directly. Use correct line numbers and 3 lines of context above and below the change.

Verify each patch applies cleanly: `git apply --check .mutants/patches/NNN.patch`. If it doesn't apply cleanly, fix the patch.

### Manifest File

Write `.mutants/manifest.json`:

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

After saving all patches and the manifest, report to the user how many mutants were generated and in which files.

## .gitignore

After creating the `.mutants/` directory, check if `.mutants/` is in `.gitignore`. If not, ask the user whether they want to add it.
