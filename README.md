# MutantX

**AI-powered mutation testing for [Claude Code](https://docs.anthropic.com/en/docs/claude-code)**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-skill-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)

MutantX evaluates how good your tests really are. It injects realistic bugs into your code, runs your test suite against each one, and reports exactly which bugs your tests miss.

Unlike AST-based tools (Stryker, PIT, mutmut) that apply blind syntactic transformations, MutantX understands your code semantically. It generates mutations that represent real bugs — off-by-one errors, swapped arguments, forgotten null checks — and avoids the equivalent mutants that plague traditional tools.

<!-- Screenshot placeholder: add a terminal recording showing /mutate in action -->
<!-- ![MutantX in action](docs/demo.gif) -->

---

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [Python 3.10+](https://www.python.org/) (for the deterministic test runner and report generator — no additional packages needed)
- [Git](https://git-scm.com/)

## Quick Start

```bash
# 1. Install (copy skills and scripts to your Claude Code config)
cp -r src/skills/* ~/.claude/skills/
mkdir -p ~/.claude/scripts
cp src/scripts/*.py ~/.claude/scripts/

# 2. Open any project in Claude Code
cd your-project

# 3. Run mutation testing
/mutate
```

That's it. MutantX auto-detects your language, test command, and source files.

---

## What Is Mutation Testing?

Code coverage tells you which lines run during tests — not whether the tests would actually catch a bug on those lines. Mutation testing answers that directly:

1. **Inject a bug** (a "mutant") into your source code
2. **Run your tests** against the mutated code
3. **Tests fail** → mutant is "killed" (your tests caught it) ✓
4. **Tests pass** → mutant "survived" (your tests missed it) ✗

The **mutation score** — the percentage of mutants killed — is a much stronger quality signal than code coverage alone.

---

## Installation

### User-level (all projects)

Copy the skills so `/mutate` is available in every project:

```bash
# Clone the repo
git clone https://github.com/user/mutantx.git
cd mutantx

# Install skills globally
cp -r src/skills/* ~/.claude/skills/

# Install scripts (deterministic test runner + report generator)
mkdir -p ~/.claude/scripts
cp src/scripts/*.py ~/.claude/scripts/

# Optional: install the autonomous agent
mkdir -p ~/.claude/agents
cp src/agents/mx-agent.md ~/.claude/agents/
```

### Project-level (single project)

Copy into your project's `.claude/` directory:

```bash
cp -r src/skills/* your-project/.claude/skills/
mkdir -p your-project/.claude/scripts
cp src/scripts/*.py your-project/.claude/scripts/
```

### Verify installation

Open Claude Code and type `/mutate` — you should see it in the skill autocomplete.

---

## Usage

### Full mutation testing run

```
/mutate
```

Runs all four phases: detect → generate → test → report.

### With arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `files` | Glob pattern(s) for source files. Comma-separated for multiple. | `files="src/**/*.ts"` |
| `test-cmd` | Command to run the test suite. | `test-cmd="pytest -x"` |
| `count` | Max mutants per source file. Default: 5. | `count="10"` |
| `regen` | Force regeneration, ignoring cache. | `regen="true"` |

```
# Target specific files with more mutants
/mutate files="src/billing/**/*.ts" count="10"

# Custom test command
/mutate test-cmd="npm run test:unit"

# Force regeneration after refactoring
/mutate regen="true"

# Combine arguments
/mutate files="lib/**/*.py" test-cmd="pytest tests/ -x" count="8"
```

### Individual phases

Each phase is also available as a standalone skill:

| Skill | What it does | Uses AI? |
|-------|-------------|----------|
| `/mx-detect` | Detect project language, test command, source files | Yes |
| `/mx-generate` | Generate mutant patches (with caching) | Yes |
| `/mx-validate` | Review mutants flagged after source file changes | Yes (only for ambiguous cases) |
| `/mx-test` | Apply patches, run tests, record results | **No** — runs `mx-test.py` |
| `/mx-report` | Calculate score and generate the report | Partial — `mx-report.py` for stats, AI for analysis |

### Standalone scripts (zero tokens)

The test runner, validator, and report generator are plain Python scripts that can run without Claude Code:

```bash
# Validate mutants against current source files
python3 ~/.claude/scripts/mx-validate.py

# Run tests against generated mutants (validates automatically)
python3 ~/.claude/scripts/mx-test.py

# Generate the report
python3 ~/.claude/scripts/mx-report.py
```

### Autonomous agent

The MutantX agent runs the full cycle without interaction:

```
# From Claude Code, trigger the agent
@mx-agent
```

---

## How It Works

### Phase 1: Project Detection

Scans for indicator files to identify your project:

| File | Language | Default Test Command |
|------|----------|---------------------|
| `package.json` | JavaScript / TypeScript | reads `scripts.test`, falls back to `npx jest` or `npx vitest run` |
| `pyproject.toml` | Python | `pytest` |
| `Cargo.toml` | Rust | `cargo test` |
| `go.mod` | Go | `go test ./...` |
| `pom.xml` | Java (Maven) | `mvn test` |
| `build.gradle` | Java (Gradle) | `./gradlew test` |
| `*.sln` / `*.csproj` | C# | `dotnet test` |
| `CMakeLists.txt` / `Makefile` | C / C++ | `cmake --build . && ctest` or `make test` |
| `mix.exs` | Elixir | `mix test` |
| `Gemfile` | Ruby | `bundle exec rspec` |

Source files are selected automatically, excluding tests, generated code, vendored dependencies, and config files. For other languages, pass `files` and `test-cmd` explicitly.

### Phase 2: Mutant Generation

The AI reads each source file and generates mutations across 12 categories:

| Category | Example |
|----------|---------|
| Arithmetic Operator | `a + b` → `a - b` |
| Relational Boundary | `i < len` → `i <= len` |
| Logical Operator | `a && b` → `a \|\| b` |
| Negated Conditional | `if (x > 0)` → `if (x <= 0)` |
| Return Value | `return result` → `return null` |
| Removed Call | `list.sort()` → *(removed)* |
| Constant Mutation | `timeout = 30` → `timeout = 0` |
| Argument Swap | `range(start, end)` → `range(end, start)` |
| Exception Handling | Empties a `catch` block |
| Collection Operation | `.filter(...)` → `.map(...)` |
| Early Return | Removes a guard clause |
| Null Injection | `getUser()` → `null` |

Each mutant changes exactly one thing and is verified to be syntactically valid and semantically different from the original.

**What it skips:** type declarations, imports, comments, logging, dead code, config-only constants.

### Validation (automatic, deterministic + optional AI)

Before testing, `mx-validate.py` checks whether source files have changed since mutants were generated. Each mutant gets one of three verdicts:

| Verdict | Meaning | Action |
|---------|---------|--------|
| **valid** | File unchanged, patch applies | Ready to test |
| **stale** | Patch no longer applies | Needs regeneration via `/mx-generate` |
| **needs-review** | File changed but patch applies | Semantically ambiguous — AI review recommended |

For `needs-review` mutants, you have three options:
1. `/mx-validate` — AI reviews whether each mutation is still semantically meaningful
2. `mx-validate.py --promote` — trust the patches, test them as-is (zero tokens)
3. `/mx-generate regen="true"` — regenerate everything

### Phase 3: Testing (deterministic — zero tokens)

Handled entirely by `mx-test.py`, a Python script that runs without AI:

1. Automatically validates mutants first (runs `mx-validate.py`)
2. Verifies your working tree is clean and baseline tests pass
3. For each pending mutant: applies the patch → runs tests → records result → reverts
4. Progress is saved after each mutant — interrupted runs resume where they left off

Once mutants are generated, you can re-test as many times as you want without spending any tokens.

### Phase 4: Reporting (deterministic + AI)

`mx-report.py` generates `.mutants/report.md` with the mechanical parts (zero tokens):

- **Mutation score** — percentage of mutants killed
- **Survived mutants** — full diff included
- **Killed mutants** — summary table

The AI skill (`/mx-report`) then adds value on top:
- **"Why this matters"** — explanation of the bug and production risk
- **"Suggested test"** — concrete test case to catch the mutant
- **Recommendations** — prioritized list of areas needing better coverage

Score interpretation:

| Score | Meaning |
|-------|---------|
| **> 80%** | Strong test suite |
| **60–80%** | Moderate — meaningful gaps exist |
| **< 60%** | Weak — many realistic bugs would go undetected |

---

## Caching

Generated mutants are saved to `.mutants/` and reused on subsequent runs:

```
.mutants/
├── detect.json            # Project detection results
├── manifest.json          # Mutant metadata, file hashes, test results
├── report.md              # Human-readable report
└── patches/
    ├── 001.patch          # Individual unified diffs
    ├── 002.patch
    └── ...
```

### Per-File Cache Invalidation

MutantX tracks a SHA-256 content hash for each mutated source file:

- **File unchanged** → mutants are kept (no regeneration needed)
- **File changed** → only that file's mutants are regenerated
- **File added** → new mutants are generated
- **File deleted** → its mutants are cleaned up

Editing one file in a 20-file project only regenerates mutants for that one file. Use `regen="true"` to force full regeneration.

---

## Why AI-Powered?

| Problem | Traditional Tools | MutantX |
|---------|------------------|---------|
| **Equivalent mutants** | 4–39% don't change behavior, wasting time | AI understands semantics and avoids them |
| **Trivial mutants** | Many cause compile errors | AI generates mutations that compile and represent real bugs |
| **Blind targeting** | Mutates everything including boilerplate | AI focuses on business logic and high-value paths |
| **No context** | Mechanical substitution | Domain-aware bugs (swapping lat/long, off-by-one in pagination) |
| **Volume** | Thousands of mutants, most uninteresting | Fewer, higher-quality mutants that reveal real gaps |
| **Actionable output** | "Mutant survived at line 42" | "This bypasses the auth check — here's a test to add" |

---

## Demos

Try MutantX on the included demo projects with intentional test gaps:

### Python

```bash
cd demos/python
pip install pytest
pytest                    # all tests pass
# Now run /mutate in Claude Code to find the gaps
```

### C++

```bash
cd demos/cpp
make test                 # all tests pass
# Now run /mutate test-cmd="make test" in Claude Code
```

See each demo's `README.md` for details on what gaps to expect.

---

## Project Structure

```
src/
├── skills/                # Claude Code skills — copy to ~/.claude/skills/
│   ├── mutate/            # Main orchestrator (runs all 4 phases)
│   ├── mx-detect/         # Phase 1: project detection (AI)
│   ├── mx-generate/       # Phase 2: mutant generation (AI)
│   ├── mx-validate/       # Validation: AI review of ambiguous mutants
│   ├── mx-test/           # Phase 3: invokes mx-test.py
│   └── mx-report/         # Phase 4: invokes mx-report.py + AI analysis
├── scripts/               # Deterministic Python scripts — copy to ~/.claude/scripts/
│   ├── mx-validate.py     # Mutation validator (zero tokens)
│   ├── mx-test.py         # Test runner (zero tokens)
│   └── mx-report.py       # Report generator (zero tokens)
└── agents/                # Claude Code agents — copy to ~/.claude/agents/
    └── mx-agent.md        # Autonomous mutation testing agent
demos/
├── python/                # Python demo with intentional test gaps
└── cpp/                   # C++ demo with intentional test gaps
```

---

## Limitations

- **LLM token cost**: Mutant generation (Phase 2) uses LLM calls. Cached patches avoid repeat costs, and testing/reporting are token-free Python scripts. Use `files` to scope down initial generation.
- **Sequential testing**: Mutants are tested one at a time (apply → test → revert). This is inherently serial to avoid interference.
- **Test suite speed**: If your tests take minutes, testing 50 mutants takes hours. Target specific modules and keep `count` low.
- **Git dependency**: Requires a git repository for clean patch application and reversion.
- **Python 3.10+**: Required for the deterministic test runner and report generator (stdlib only, no pip packages).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
