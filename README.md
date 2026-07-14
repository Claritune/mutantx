# MutantX

AI-powered mutation testing skill for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Uses LLM intelligence to generate semantically meaningful code mutations, run your test suite against each one, and report exactly where your tests have gaps.

Unlike traditional AST-based mutation tools (Stryker, PIT, mutmut), MutantX understands your code. It generates mutations that represent realistic bugs — off-by-one errors, swapped arguments, forgotten null checks — rather than applying blind syntactic transformations. It also avoids equivalent mutants (mutations that don't change behavior) which plague traditional tools.

## What Is Mutation Testing?

Mutation testing measures how good your tests actually are. Code coverage tells you which lines run during tests, but not whether the tests would catch a bug on those lines. Mutation testing answers that question directly:

1. **Inject a bug** (a "mutant") into your source code
2. **Run your tests** against the mutated code
3. **If the tests fail** → the mutant is "killed" (your tests caught the bug)
4. **If the tests pass** → the mutant "survived" (your tests missed it)

The **mutation score** — the percentage of mutants killed — is a much stronger indicator of test suite quality than code coverage alone.

## Installation

### Project-level (single project)

Copy the skill into your project's Claude Code configuration:

```bash
mkdir -p .claude/skills
cp -r path/to/mutantx/.claude/skills/mutate .claude/skills/mutate
```

### User-level (all projects)

Install globally so `/mutate` is available in every project:

```bash
cp -r path/to/mutantx/.claude/skills/mutate ~/.claude/skills/mutate
```

## Usage

Inside Claude Code, invoke the skill with:

```
/mutate
```

That's it. MutantX auto-detects your language, test command, and source files.

### Arguments

All arguments are optional:

| Argument | Description | Example |
|----------|-------------|---------|
| `files` | Glob pattern(s) for source files to mutate. Comma-separated for multiple. | `files="src/**/*.ts"` |
| `test-cmd` | Command to run the test suite. | `test-cmd="pytest -x"` |
| `count` | Max mutants to generate per source file. Default: 5. | `count="10"` |
| `regen` | Force regeneration of mutants, ignoring cache. | `regen="true"` |

### Examples

```
# Auto-detect everything
/mutate

# Target specific files with more mutants
/mutate files="src/billing/**/*.ts" count="10"

# Use a custom test command
/mutate test-cmd="npm run test:unit"

# Regenerate mutants after refactoring
/mutate regen="true"

# Combine arguments
/mutate files="lib/**/*.py" test-cmd="pytest tests/ -x" count="8"
```

## How It Works

MutantX runs in four phases:

### Phase 1: Project Detection

Automatically identifies your project by scanning for indicator files:

| File | Language | Default Test Command |
|------|----------|---------------------|
| `package.json` | JavaScript / TypeScript | reads `scripts.test`, falls back to `npx jest` or `npx vitest run` |
| `pyproject.toml` | Python | `pytest` |
| `Cargo.toml` | Rust | `cargo test` |
| `go.mod` | Go | `go test ./...` |
| `pom.xml` | Java (Maven) | `mvn test` |
| `build.gradle` | Java (Gradle) | `./gradlew test` |
| `*.sln` / `*.csproj` | C# | `dotnet test` |
| `mix.exs` | Elixir | `mix test` |
| `Gemfile` | Ruby | `bundle exec rspec` |

Source files are selected automatically, excluding tests, generated code, vendored dependencies, and config files.

### Phase 2: Mutant Generation

The AI reads each source file and generates mutations across 12 categories:

| Category | What It Does | Example |
|----------|-------------|---------|
| Arithmetic Operator | Changes `+` to `-`, `*` to `/`, etc. | `a + b` → `a - b` |
| Relational Boundary | Introduces off-by-one errors | `i < len` → `i <= len` |
| Logical Operator | Swaps `&&`/`||` | `a && b` → `a \|\| b` |
| Negated Conditional | Inverts conditions | `if (x > 0)` → `if (x <= 0)` |
| Return Value | Changes function returns | `return result` → `return null` |
| Removed Call | Removes function calls | `list.sort()` → *(removed)* |
| Constant Mutation | Changes literals | `timeout = 30` → `timeout = 0` |
| Argument Swap | Swaps arguments | `range(start, end)` → `range(end, start)` |
| Exception Handling | Weakens error handling | Empties a `catch` block |
| Collection Operation | Changes collection methods | `.filter(...)` → `.map(...)` |
| Early Return | Adds/removes early returns | Removes a guard clause |
| Null Injection | Injects null/nil/None | `getUser()` → `null` |

Each mutant changes exactly one thing and is verified to be syntactically valid and semantically different from the original (not an equivalent mutant).

**What it skips:** type declarations, imports, comments, logging statements, dead code, and config-only constants.

### Phase 3: Testing

1. **Pre-flight** — verifies your working tree is clean and baseline tests pass
2. **For each mutant:**
   - Applies the patch with `git apply`
   - Runs the test command (with a timeout to catch infinite loops)
   - Records the result: killed, survived, timeout, or skipped
   - Reverts the patch with `git apply -R`
3. **Progress is saved** after each mutant — interrupted runs resume where they left off

### Phase 4: Reporting

Generates `.mutants/report.md` with:

- **Mutation score** — percentage of mutants killed
- **Survived mutants** — full diff, explanation of what kind of bug it represents, and a concrete test suggestion to close the gap
- **Killed mutants** — summary table
- **Recommendations** — prioritized list of areas needing better test coverage

Score interpretation:
- **> 80%** — Strong test suite
- **60–80%** — Moderate, meaningful gaps exist
- **< 60%** — Weak, many realistic bugs would go undetected

## Caching

Generated mutants are saved to `.mutants/` and reused on subsequent runs:

```
.mutants/
├── manifest.json          # Metadata, config, per-file hashes, and test results
├── report.md              # Human-readable report
└── patches/
    ├── 001.patch          # Individual unified diffs
    ├── 002.patch
    └── ...
```

### Per-File Cache Invalidation

MutantX tracks a SHA-256 content hash for each mutated source file. On subsequent runs, it compares the stored hash against the current file content:

- **File unchanged** — its mutants are kept as-is (no LLM call needed)
- **File changed** — only that file's mutants are discarded and regenerated
- **File added** — new mutants are generated
- **File deleted** — its mutants are cleaned up

This means editing one file in a 20-file project only regenerates mutants for that one file. Each kept patch is also verified with `git apply --check` to catch edge cases where the diff context no longer matches.

Use `regen="true"` to force full regeneration regardless of hashes.

## Why AI-Powered?

Traditional mutation testing tools (Stryker, PIT, mutmut) work by applying mechanical AST transformations — every `+` becomes `-`, every `<` becomes `<=`, etc. This creates problems:

| Problem | Traditional Tools | MutantX |
|---------|------------------|---------|
| **Equivalent mutants** | 4–39% of mutants don't change behavior, wasting test runs and requiring manual review | AI understands semantics and avoids generating mutations with identical behavior |
| **Trivial mutants** | Many mutations cause compile errors or are obviously caught | AI generates mutations that compile and represent realistic bugs |
| **Blind targeting** | Mutates everything including boilerplate, config, and dead code | AI focuses on business logic, control flow, and high-value code paths |
| **No context** | Each mutation is a mechanical substitution | AI generates domain-aware bugs (e.g., swapping latitude/longitude, off-by-one in pagination) |
| **Volume** | Thousands of mutants, most uninteresting | Fewer, higher-quality mutants that reveal real test gaps |
| **Actionable output** | "Mutant survived at line 42" | "This mutation bypasses the auth check — here's a test to add" |

## Supported Languages

MutantX is language-agnostic. It works with any language that has:
1. A file-based project indicator (package.json, pyproject.toml, etc.)
2. A test command that returns exit code 0 on success

Out-of-the-box auto-detection covers JavaScript, TypeScript, Python, Rust, Go, Java, C#, Elixir, and Ruby. For other languages, pass `files` and `test-cmd` explicitly.

## Limitations

- **LLM token cost**: Mutant generation uses LLM calls. Cached patches avoid repeat costs, but the initial generation on a large codebase can be significant. Use the `files` argument to scope down.
- **Sequential testing**: Mutants are tested one at a time (apply → test → revert). This is inherently serial to avoid interference between mutations.
- **Test suite speed**: If your tests take minutes to run, testing 50 mutants takes hours. Target specific modules and keep `count` low for slow test suites.
- **Git dependency**: Requires a git repository for clean patch application and reversion.

## License

MIT
