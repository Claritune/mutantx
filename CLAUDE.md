# MutantX

AI-powered mutation testing skill for Claude Code. Language-agnostic.

## What it does

`/mutate` generates realistic code mutations (bugs), runs the project's test suite against each one, and reports a mutation score showing how well the tests catch injected faults.

## Usage

```
/mutate                              # auto-detect everything
/mutate files="src/**/*.ts"          # target specific files
/mutate test-cmd="pytest -x"        # override test command
/mutate regen="true"                 # force regenerate cached mutants
/mutate count="10"                   # more mutants per file
```

## How it works

1. Detects the project language, test command, and source files
2. Generates mutants as unified diff patches in `.mutants/patches/`
3. Applies each patch, runs tests, reverts — recording killed/survived
4. Produces a mutation score report at `.mutants/report.md`

Cached mutants in `.mutants/` are reused across runs until code changes or `regen="true"` is passed.

## Installing globally

Copy `.claude/skills/mutate/` to `~/.claude/skills/mutate/` to make `/mutate` available in all projects.
