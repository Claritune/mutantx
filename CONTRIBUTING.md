# Contributing to MutantX

Thanks for your interest in contributing to MutantX! This project is an AI-powered mutation testing skill for Claude Code.

## How MutantX Works

MutantX is a set of Claude Code skills (markdown instruction files) that guide the AI through mutation testing. There is no traditional runtime code — the "source" is the skill specifications in `src/skills/` and `src/agents/`.

## Project Structure

```
src/
├── skills/           # Claude Code skills (copy to ~/.claude/skills/)
│   ├── mutate/       # Main orchestrator — runs all phases
│   ├── mx-detect/    # Phase 1: project detection
│   ├── mx-generate/  # Phase 2: mutant generation
│   ├── mx-test/      # Phase 3: mutant testing
│   └── mx-report/    # Phase 4: reporting
└── agents/           # Claude Code agents (copy to ~/.claude/agents/)
    └── mx-agent.md   # Autonomous mutation testing agent
demos/
├── python/           # Python demo project
└── cpp/              # C++ demo project
```

## What to Contribute

### Skill Improvements

The skill files in `src/skills/` define how Claude performs mutation testing. Good contributions include:

- **New mutation categories** — adding realistic bug patterns that the AI should generate
- **Better language support** — improving detection for specific languages or build systems
- **Edge case handling** — improving behavior for monorepos, large projects, or unusual setups
- **Report quality** — better explanations, suggestions, or formatting in the output report

### Demo Projects

Demo projects in `demos/` should be small, self-contained projects that:

- Have a clear `README.md` with setup instructions
- Include source code with enough logic to generate interesting mutations
- Have tests that deliberately miss some edge cases (so mutation testing has something to find)
- Work without external services or complex setup

### Documentation

README improvements, usage examples, and guides are always welcome.

## Guidelines

1. **Keep skills focused.** Each `mx-*` skill handles one phase. Don't mix concerns.
2. **Test with demos.** Run `/mutate` on the demo projects to verify changes work.
3. **Be specific in instructions.** The skills are prompts for an AI — clarity matters more than brevity.
4. **Document mutation categories.** If adding a new category, include the category name, description, and a concrete example.

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test by installing the skills locally and running `/mutate` on a demo project
5. Open a pull request with a clear description of what changed and why

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
