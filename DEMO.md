# MutantX Demo Scenario — C++

A walkthrough for a live demo using the C++ calculator project. Covers all MutantX features. Estimated time: 15–20 minutes.

---

## Setup (before the demo)

```bash
# Install skills and scripts
cp -r src/skills/* ~/.claude/skills/
mkdir -p ~/.claude/scripts && cp src/scripts/*.py ~/.claude/scripts/

# Clean any prior run
rm -rf demos/cpp/.mutants

# Verify baseline tests pass
cd demos/cpp && make test
# => All tests passed!
```

Make sure you're in `demos/cpp/` with a clean git state.

---

## Act 1 — The Problem (2 min)

**Talking point:** "Our tests pass. Code coverage tools would show us lines are hit. But would our tests actually catch a bug?"

Show the code briefly:

- `calculator.cpp` — 9 functions: basic math, clamp, factorial, fibonacci, gcd, is_prime
- `test_calculator.cpp` — 7 test functions, but note the gaps in comments:
  - `clamp()` and `factorial()` have **zero** test coverage
  - `divide()` doesn't test the exception path
  - `fibonacci()` doesn't test fib(0) or fib(1)
  - `gcd()` doesn't test when an argument is 0
  - `is_prime()` doesn't test boundaries: 0, 1, 2, negatives

**Talking point:** "Let's find out exactly how good these tests are."

---

## Act 2 — Full Mutation Test Run (5 min)

Run the full pipeline with one command:

```
/mutate test-cmd="make test"
```

**What to narrate as each phase runs:**

1. **Detect** — "MutantX identifies this as C++, finds `calculator.cpp` as the source file, and uses `make test` as the test command."

2. **Generate** — "The AI reads the code and generates ~5 realistic bugs per file — not random AST transforms, but the kind of mistakes a developer would actually make. Off-by-one errors, swapped arguments, removed checks."

3. **Test** — "Now we apply each bug, run the tests, and revert. This is a deterministic Python script — no AI tokens. We can re-run this as many times as we want for free."

4. **Report** — "We get a mutation score and a detailed report with suggested tests for every bug we missed."

**Key moment:** Point out the mutation score. It should be well below 80%, confirming the test suite has real gaps.

**Show the report:**

```bash
cat .mutants/report.md
```

Walk through 2–3 survived mutants. For each one, show:
- The diff (what bug was injected)
- Why it matters (what could go wrong in production)
- The suggested test (copy-pasteable)

---

## Act 3 — Caching (2 min)

**Talking point:** "Mutants are cached as patch files. If we run again without changing code, generation is skipped entirely."

```
/mutate test-cmd="make test"
```

**Point out:** "It says 'Cached: N mutants for 1 unchanged file' — zero AI tokens spent on generation. Only testing runs again."

---

## Act 4 — Incremental Regeneration (3 min)

**Talking point:** "Now let's see what happens when we change code. Only the changed file gets new mutants."

Make a small edit to `calculator.cpp` — for example, add a helper function or modify a comment in a function body. Then run:

```
/mutate test-cmd="make test"
```

**Point out:** The output shows the file hash changed, so mutants are regenerated for that file only. Other files (if there were multiple) would keep their cached mutants.

---

## Act 5 — Manual Mutation Capture (3 min)

**Talking point:** "What if you want to test a specific 'what if' scenario? You can manually inject a bug and capture it."

Edit `calculator.cpp` to introduce a specific bug. For example, change the off-by-one in `is_prime`:

```cpp
// Change line 83:
//   if (n <= 1) return false;
// to:
//   if (n < 1) return false;
```

Now capture it:

```bash
python3 ~/.claude/scripts/mx-capture.py -d "is_prime returns true for n=1"
```

**Point out:**
- The script shows the diff, saves it as a patch, and reverts the file
- The mutant appears in `manifest.json` with `category: "manual"`
- It coexists with AI-generated mutants

Test the manual mutant:

```bash
python3 ~/.claude/scripts/mx-test.py --skip-validation
```

**Key moment:** If this manual mutant survives, it proves the tests don't cover `is_prime(1)` — which is a real boundary bug.

---

## Act 6 — Zero-Token Re-testing (2 min)

**Talking point:** "Once mutants exist as patches, testing is free. No AI needed. Let's add a test and re-run."

Add a test to `test_calculator.cpp` that catches one of the survived mutants. For example, if a `factorial` mutant survived, add:

```cpp
void test_factorial() {
    assert(factorial(0) == 1);
    assert(factorial(1) == 1);
    assert(factorial(5) == 120);
}
```

Don't forget to call it from `main()`.

Reset mutant statuses and re-test directly from the terminal:

```bash
python3 ~/.claude/scripts/mx-test.py
```

**Point out:** "Zero tokens. We just re-ran the entire mutation test suite using only the cached patches. The score should improve."

Regenerate the report:

```bash
python3 ~/.claude/scripts/mx-report.py
```

**Show the improved score.** The factorial mutant should now be killed.

---

## Act 7 — Running Individual Phases (2 min)

**Talking point:** "Each phase is independently invocable. You can run just detection, just generation, or just reporting."

Show a few examples:

```
# Just detect — useful to verify MutantX understands your project
/mx-detect test-cmd="make test"

# Generate more mutants per file
/mx-generate count="8"

# Just the report with AI analysis
/mx-report
```

**Talking point:** "You can also run the scripts directly from the terminal without Claude Code at all — validation, testing, and reporting are all plain Python with zero dependencies."

```bash
python3 ~/.claude/scripts/mx-validate.py
python3 ~/.claude/scripts/mx-test.py
python3 ~/.claude/scripts/mx-report.py
```

---

## Closing (1 min)

**Key takeaways to summarize:**

1. **Mutation testing > code coverage** — it tests whether your tests actually catch bugs, not just whether lines execute
2. **AI-generated mutants are realistic** — they represent bugs developers actually make, not mechanical AST transforms
3. **Zero-token re-testing** — generate once, test unlimited times from the terminal
4. **Per-file caching** — change one file, only that file's mutants regenerate
5. **Manual mutations** — capture your own "what if" scenarios alongside AI-generated ones
6. **Modular design** — each phase works independently; scripts need no external packages
7. **Language-agnostic** — works with C++, Python, JS/TS, Rust, Go, Java, C#, Ruby, Elixir

---

## Quick Reference — Commands Used

| Command | What It Does | Tokens? |
|---|---|---|
| `/mutate test-cmd="make test"` | Full pipeline | Yes |
| `/mx-detect test-cmd="make test"` | Detect project setup | Yes |
| `/mx-generate count="8"` | Generate mutants | Yes |
| `/mx-validate` | AI review of changed mutants | Yes |
| `/mx-report` | Report with AI analysis | Partial |
| `python3 mx-capture.py -d "desc"` | Capture manual mutation | No |
| `python3 mx-validate.py` | Check mutant validity | No |
| `python3 mx-validate.py --promote` | Trust changed patches | No |
| `python3 mx-test.py` | Test all pending mutants | No |
| `python3 mx-report.py` | Generate stats report | No |
