# Roadmap

Open work on MutantX. Most items come from field notes on a C++20 project
(Cats vs Mutants: 4 source files, 121 GoogleTest tests, 52 mutants across two
runs, plus 31 hand-written mutants). Item numbers (#N) refer to those notes.

## Done (2026-10-29)

- **#15** `mx-test.py` checks for pending mutants before the clean-tree check and baseline.
- **#7** The clean-tree check covers only the files being mutated (`--strict-clean` for the
  whole tree). Reverts restore from a byte-for-byte backup instead of `git checkout`.
- **#8** `mx-test.py` waits for a new wall-clock second before every apply and revert
  (Make and `.pyc` compare mtimes to the second), and re-runs the tests on unmutated
  code at the end. This changed a recorded result in `demos/cpp` (mutant 004).
- **#14** `mx-validate.py` fingerprints the test files and test command (`tests_hash`),
  and re-tests cached results when they change. `--retest` forces it.
- **#3** New statuses `killed-crash` and `killed-build` (via optional `build_command`).
  A timeout no longer shares exit code `-1` with SIGHUP. C `assert()` aborts count as
  ordinary kills.

## Follow-ups to the fixes above

- [ ] **Reinstall.** `~/.claude/scripts` and the cvm project's `.claude/` still hold the
      old scripts and skills.
- [ ] **Re-run cvm with `--retest`.** Its 34 cached results predate the fingerprint and the
      stale-build fix.
- [ ] **Recover kills hidden by a crash (#3).** When a run is `killed-crash`, re-run the tests
      one at a time (or one suite at a time) to get the full failure list. In cvm, a crash
      hid 26 of 32 failing tests. Needs the per-framework test listing from #2.
- [ ] **Name the crashing test (#3)** when the framework reports it.
- [ ] **Regression tests for the scripts.** The checks used for these fixes were throwaway.
      Add a fixture repo and pytest cases covering: stale `.pyc`, scoped clean check,
      backup restore, test-fingerprint invalidation, and crash/assert/timeout/SIGHUP
      classification.
- [ ] **`mx-generate` should record `tests_hash`** when it writes a new manifest, so the
      first test run is not reported as "fingerprint recorded for the first time".

## Kill data (the base for most of the analysis features)

- [ ] **#2 Record which tests killed each mutant.** Parse failing test names while
      `mx-test.py` runs (GoogleTest `[  FAILED  ]`, pytest, JUnit XML, Jest JSON,
      `go test -json`) and store them as `killed_by: [...]`. The report gets a Kill Analysis
      table and a **single-test kills** section (fragile spots). Detect should avoid
      fail-fast flags (`pytest -x`), which would cut the list short.
      Reference format: `kills.json` / `test_kills.json` built by hand in the cvm run.
- [ ] **#9 Test contribution report** (needs #2). Write `test_kills.json`
      (test → mutants it kills) and list sole killers, zero-kill tests and identical kill
      sets. Label zero-kill tests "not exercised by this mutant set", **never**
      "redundant": in cvm, 19 of 24 zero-kill tests caught a hand mutant aimed at them.
      Show the sample size next to every redundancy claim.

## Generator quality (`mx-generate/SKILL.md`)

- [ ] **#6 `statement_reorder` category**: swap two adjacent calls whose order matters.
- [ ] **#11 Config bypass category**: replace a config or injected value with its default
      literal. Reword the "configuration constants only used at startup" exclusion,
      which currently contradicts it.
- [ ] **#12 Generation rules from missed mutants.** Fold into the existing categories as
      sharper examples rather than 12 new rows: remove/weaken each guard clause, drop one
      conjunct of a multi-part filter, mutate range starts, `<=`/`>=` → `==`,
      empty-case return values, common-case constant substitution, success-flag lies,
      deferred instead of immediate effects, reordered validation, over-eager validation,
      branch cross-contamination. Add **coverage rules** the cap cannot override: every
      guard clause gets one mutant, every bool/status-returning function gets a
      "success lie", every multi-part filter gets a "drop one conjunct". These rules come
      from a single project, so validate on `demos/python` before relying on them.
- [ ] **#4 Cap per function, not per file.** Add `count-per-function`, keep `count` as an
      overall limit. Store mutants dropped by a cap as `status: "deferred"` and report how
      many. (In cvm, the deferred mutants were exactly the ones that later mattered.)
- [ ] **#5 Blind mode.** `blind=true` generates in a fresh subagent that may not read the
      test directories or earlier reports. Record `blind` and the generator model in the
      manifest and the report header.

## Honest scores

- [ ] **Show the sample size on the score line** (cheap, first step of #1):
      "100% of 18 tested". Soften the "> 80% = strong" interpretation when few mutants
      were tested.
- [ ] **List functions with no tested mutant** (cheap, first step of #1). Have the generator
      record the function per mutant and the list of functions with logic per file.
- [ ] **#1 Mutation-space inventory.** `mx-enumerate.py` lists every candidate site
      (token scanner first, tree-sitter later), optionally pruned by line coverage.
      An AI pass classifies each site as relevant / likely-equivalent / compile-error /
      trivial, then a selection strategy picks what to test (`--strategy all`,
      N per function, stratified). Report candidates, relevant and tested next to the
      score. Keep "likely equivalent" marks across runs.

## Test-quality signals

- [ ] **#10 Test-directed generation** (needs #2). For each zero-kill test, show the generator
      only the test's *name* and ask for one realistic mutant that breaks that rule. Tag
      results `origin: test-directed` and score them separately.
- [ ] **#13 Weak-test detection** (needs #10). If a test-directed mutant is killed by other
      tests but survives its target test, report the target as a **suspected weak test**,
      with an AI note on why. Classify tests no single mutant can break as
      `unkillable: double-guarded | sanity | design-intent | equivalent-only`.

## Performance (compiled languages)

- [ ] Run only the tests that cover the mutated line (needs coverage data).
- [ ] Run mutants in parallel git worktrees.
- [ ] Mutant schemata: compile all mutants once, switch them on at run time.
