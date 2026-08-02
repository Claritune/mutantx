# MutantX

AI-powered mutation testing for Claude Code. Language-agnostic.

## Project Structure

```
src/skills/          — Distributable Claude Code skills
src/agents/          — Distributable Claude Code agents
demos/python/        — Python demo project with intentional test gaps
demos/cpp/           — C++ demo project with intentional test gaps
```

## Skills

| Skill | Purpose |
|-------|---------|
| `/mutate` | Full mutation testing run (orchestrates all phases) |
| `/mx-detect` | Phase 1: detect project language, test command, source files |
| `/mx-generate` | Phase 2: generate mutant patches with per-file caching |
| `/mx-test` | Phase 3: apply patches, run tests, record results |
| `/mx-report` | Phase 4: calculate score and generate report |

## Agent

`mx-agent` runs the full mutation testing cycle autonomously without user interaction.

## Installing for use

```bash
# Skills
cp -r src/skills/* ~/.claude/skills/

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
