# MutantX

AI-powered mutation testing for Claude Code. Language-agnostic.

## Workflow

Commit after each change. Do not batch multiple changes into one commit.

## Project Structure

```
src/skills/          — Distributable Claude Code skills
src/scripts/         — Deterministic Python scripts (zero tokens)
src/agents/          — Distributable Claude Code agents
demos/python/        — Python demo project with intentional test gaps
demos/cpp/           — C++ demo project with intentional test gaps
```

## Architecture

Phases 1-2 (detect, generate) use AI. Phases 3-4 (test, report) are deterministic Python scripts that consume zero tokens. Once mutants are generated, repeated testing is free.

| Phase | Component | AI? |
|-------|-----------|-----|
| Detect | `/mx-detect` skill | Yes |
| Generate | `/mx-generate` skill | Yes |
| Validate | `mx-validate.py` + `/mx-validate` skill | Deterministic + optional AI |
| Test | `mx-test.py` script | No |
| Report | `mx-report.py` script + `/mx-report` skill | Partial |

Validation runs automatically before testing. If source files changed since generation, mutants are classified as valid, stale, or needs-review. The AI skill reviews ambiguous cases only.

## Skills

| Skill | Purpose |
|-------|---------|
| `/mutate` | Full mutation testing run (orchestrates all phases) |
| `/mx-detect` | Phase 1: detect project language, test command, source files |
| `/mx-generate` | Phase 2: generate mutant patches with per-file caching |
| `/mx-validate` | Review mutants flagged as needs-review after file changes |
| `/mx-test` | Phase 3: invokes `mx-test.py` |
| `/mx-report` | Phase 4: invokes `mx-report.py` then adds AI analysis |

## Agent

`mx-agent` runs the full mutation testing cycle autonomously without user interaction.

## Installing for use

```bash
# Skills
cp -r src/skills/* ~/.claude/skills/

# Scripts (required for testing and reporting)
mkdir -p ~/.claude/scripts
cp src/scripts/*.py ~/.claude/scripts/

# Agent (optional)
mkdir -p ~/.claude/agents
cp src/agents/mx-agent.md ~/.claude/agents/
```

## Testing changes

Run `/mutate` on the demo projects to verify skill changes work correctly:

```bash
cd demos/python && pytest      # baseline should pass
cd demos/cpp && make test      # baseline should pass
```

## Output

All mutation testing artifacts go to `.mutants/` in the target project:
- `detect.json` — project detection results
- `manifest.json` — mutant metadata, file hashes, test results
- `report.md` — human-readable report
- `patches/*.patch` — individual unified diffs
