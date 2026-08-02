# MutantX Python Demo

A small calculator project with intentional test gaps, designed to
demonstrate what AI-powered mutation testing uncovers.

## Setup

```bash
pip install pytest
```

## Run tests

```bash
cd demos/python
pytest
```

All tests pass -- the code is correct. But the test suite has blind spots.

## Run MutantX

From the project root in Claude Code:

```
/mutate files="demos/python/calculator.py" test-cmd="pytest demos/python"
```

## What MutantX will find

The tests have deliberate gaps that mutation testing exposes:

- **percentage()** -- zero test coverage, every mutant survives
- **divide()** -- no test for the division-by-zero guard
- **apply_discount()** -- boundaries (0%, 100%, negative) are untested
- **compound_interest()** -- zero principal and zero rate are untested
- **split_bill()** -- zero tip and single-person edge cases are untested

A well-tested project should kill >90% of mutants. This demo scores
significantly lower, showing exactly where to add tests.
