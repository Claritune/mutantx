# C++ Demo for MutantX

A small calculator library with intentional test gaps, designed to
demonstrate AI-powered mutation testing with MutantX.

## Build and test

```bash
make        # compile
make test   # compile and run tests
make clean  # remove build artifacts
```

## Run MutantX

From this directory inside Claude Code:

```
/mutate test-cmd="make test"
```

## Intentional test gaps

The test suite passes, but it has deliberate blind spots that mutation
testing should catch:

- **clamp** -- not tested at all
- **factorial** -- not tested at all
- **divide-by-zero** -- exception path never exercised
- **fibonacci edge cases** -- fib(0) and fib(1) not checked
- **gcd with zero** -- gcd(n, 0) and gcd(0, n) not tested
- **is_prime boundaries** -- 0, 1, 2, and negative inputs not tested

A good mutation score target after filling these gaps is > 90%.
