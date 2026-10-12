---
name: mx-detect
description: "MutantX Phase 1 — Detect project language, test command, and source files for mutation testing."
user_invocable: true
arguments:
  - name: files
    description: "Glob pattern(s) for source files to mutate (e.g., \"src/**/*.ts\"). Comma-separated for multiple patterns. Auto-detected if omitted."
    required: false
  - name: test-cmd
    description: "Command to run the test suite (e.g., \"npm test\", \"pytest\"). Auto-detected if omitted."
    required: false
---

# MutantX — Phase 1: Project Detection

You are the detection phase of a mutation testing engine. Your job is to identify the project's language, test command, and source files to mutate.

Write the detection results as JSON to `.mutants/detect.json` so downstream phases can consume them.

---

## Language & Test Command Detection

If `test-cmd` is provided, use it directly. Otherwise, check for these indicator files in order and use the first match:

| Indicator File     | Language     | Default Test Command       | Default Source Pattern            |
|--------------------|--------------|----------------------------|----------------------------------|
| `package.json`     | JavaScript/TypeScript | Read `scripts.test` from package.json; fall back to `npx jest` or `npx vitest run` | `src/**/*.{ts,tsx,js,jsx}` minus `**/*.{test,spec}.*` and `**/__tests__/**` |
| `pyproject.toml` or `setup.py` or `requirements.txt` | Python | `pytest` | `src/**/*.py` or `**/*.py` minus `**/test_*` and `**/*_test.py` and `**/tests/**` |
| `Cargo.toml`       | Rust         | `cargo test`               | `src/**/*.rs` minus test modules |
| `go.mod`           | Go           | `go test ./...`            | `**/*.go` minus `*_test.go`      |
| `pom.xml`          | Java (Maven) | `mvn test`                 | `src/main/**/*.java`             |
| `build.gradle`     | Java (Gradle)| `./gradlew test`           | `src/main/**/*.java`             |
| `*.sln` or `*.csproj` | C#        | `dotnet test`              | `**/*.cs` minus `**/Tests/**` and `**/*.Tests/**` |
| `mix.exs`          | Elixir       | `mix test`                 | `lib/**/*.ex`                    |
| `Gemfile`          | Ruby         | `bundle exec rspec` or `rake test` | `lib/**/*.rb` or `app/**/*.rb` |
| `CMakeLists.txt` or `Makefile` (with C/C++ sources) | C/C++ | Auto-detect: `cmake --build . && ctest` or `make test` | `src/**/*.{c,cpp,cc,cxx,h,hpp}` minus test files |

If no indicator is found, ask the user for the language, test command, and source file patterns.

## Source File Selection

If the user provides `files`, use that pattern instead of auto-detection, but still apply the exclusions below.

After identifying candidate source files:

1. **Exclude test files** — files matching test patterns for the detected language (e.g., `test_*.py`, `*.test.ts`, `*_test.go`).
2. **Exclude generated/vendored code** — `node_modules/`, `vendor/`, `dist/`, `build/`, `.git/`, `target/`, `__pycache__/`, `cmake-build*/`.
3. **Exclude config files** — `*.config.*`, `*.json`, `*.yaml`, `*.yml`, `*.toml`, `*.xml` (unless they contain business logic).
4. **Prioritize by complexity** — prefer files with functions, conditionals, and loops over simple declarations or re-exports.

## Large Project Handling

If more than 30 source files are detected, ask the user to narrow scope with the `files` argument, or select the 10 most complex files automatically.

## Output

Write `.mutants/detect.json`:

```json
{
  "language": "<detected language>",
  "test_command": "<test command>",
  "source_files": ["path/to/file1.py", "path/to/file2.py"],
  "source_patterns": ["<glob patterns used>"],
  "detected_at": "<ISO 8601 timestamp>"
}
```

Create the `.mutants/` directory if it doesn't exist.

Display the detection results to the user before finishing:

```
Detected: Python project
Test command: pytest
Source files: 12 files in src/ (excluding tests)
```
