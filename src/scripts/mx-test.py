#!/usr/bin/env python3
"""MutantX deterministic test runner.

Reads .mutants/manifest.json, applies each patch, runs the test suite,
records whether tests caught the mutation, and reverts. Zero AI tokens.

Usage:
    python mx-test.py [--mutants-dir .mutants] [--timeout 120]
"""

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path


def find_sibling_script(name: str) -> Path | None:
    """Find a script in the same directory as this script."""
    here = Path(__file__).resolve().parent
    candidate = here / name
    if candidate.exists():
        return candidate
    return None


def run_cmd(cmd: str, timeout: int, cwd: Path | None = None) -> tuple[int, str]:
    """Run a shell command and return (exit_code, output)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


def last_n_lines(text: str, n: int = 20) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-n:])


def check_clean_tree(files: list[str] | None = None) -> bool:
    """Check for uncommitted changes, limited to `files` when given.

    Only the files the patches rewrite need to be clean; unrelated edits and
    untracked files elsewhere in the repo cannot be harmed by a mutation run.
    """
    cmd = "git status --porcelain"
    if files:
        cmd += " -- " + " ".join(shlex.quote(f) for f in files)
    code, output = run_cmd(cmd, timeout=30)
    if code != 0:
        print(f"ERROR: git status failed: {output}", file=sys.stderr)
        return False
    if output.strip():
        scope = "Files to be mutated have" if files else "Working tree has"
        print(f"WARNING: {scope} uncommitted changes.", file=sys.stderr)
        print(output, file=sys.stderr)
        return False
    return True


def patched_files(patch_path: Path) -> list[str]:
    """Paths a unified diff writes to, from its `+++ b/...` headers."""
    files = []
    for line in patch_path.read_text().splitlines():
        if line.startswith("+++ ") and not line.startswith("+++ /dev/null"):
            path = line[4:].split("\t")[0].strip()
            files.append(path[2:] if path.startswith("b/") else path)
    return files


def run_baseline(test_command: str, timeout: int) -> tuple[bool, float]:
    """Run baseline tests. Returns (passed, duration_seconds)."""
    print("Running baseline tests...")
    start = time.time()
    code, output = run_cmd(test_command, timeout=timeout)
    duration = time.time() - start

    if code == 0:
        print(f"  Baseline PASSED in {duration:.1f}s")
        return True, duration
    else:
        print(f"  Baseline FAILED (exit code {code})", file=sys.stderr)
        print(last_n_lines(output, 10), file=sys.stderr)
        return False, duration


def wait_for_next_second(after: float) -> None:
    """Block until the wall clock is in a later whole second than `after`.

    Make (3.81 on macOS) and Python's .pyc cache compare source mtimes to the
    second. A source file rewritten in the same second as the last build keeps
    the stale object or bytecode, silently polluting later results. Waiting here
    before every patch apply and revert makes each source write strictly newer
    than anything the previous test run produced.
    """
    while int(time.time()) <= int(after):
        time.sleep(1 - (time.time() % 1) + 0.01)


def apply_patch(patch_path: Path) -> bool:
    code, _ = run_cmd(f"git apply {patch_path}", timeout=30)
    return code == 0


def backup_files(paths: list[str]) -> dict[str, bytes]:
    return {p: Path(p).read_bytes() for p in paths if Path(p).exists()}


def revert_patch(patch_path: Path, backup: dict[str, bytes]) -> bool:
    """Revert a mutant, then make sure every file matches its pre-patch bytes.

    Restoring from the in-memory backup (rather than `git checkout`) means a
    failed `git apply -R` can never discard the user's uncommitted edits.
    """
    run_cmd(f"git apply -R {patch_path}", timeout=30)
    ok = True
    for path, content in backup.items():
        p = Path(path)
        if not p.exists() or p.read_bytes() != content:
            try:
                p.write_bytes(content)
            except OSError as e:
                print(f"  ERROR: could not restore {path}: {e}", file=sys.stderr)
                ok = False
    return ok


def test_mutant(
    mutant: dict,
    mutants_dir: Path,
    test_command: str,
    timeout: int,
    last_run_end: float,
) -> tuple[dict, float]:
    """Test a single mutant. Returns the updated mutant dict and the time its
    test run finished.

    `last_run_end` is when the previous test command finished; the patch is
    not applied until the clock has moved past that second.
    """
    patch_path = mutants_dir / mutant["patch_file"]
    mutant_id = mutant["id"]
    category = mutant.get("category", "unknown")
    target_file = mutant.get("file", "unknown")
    line = mutant.get("line", "?")

    label = f"{category} in {target_file}:{line}"

    if not patch_path.exists():
        print(f"  Mutant {mutant_id}: {label} ... skipped (patch file missing)")
        mutant["status"] = "skipped"
        mutant["test_output"] = "Patch file not found"
        return mutant, last_run_end

    backup = backup_files(patched_files(patch_path))
    wait_for_next_second(last_run_end)
    if not apply_patch(patch_path):
        print(f"  Mutant {mutant_id}: {label} ... skipped (patch failed to apply)")
        mutant["status"] = "skipped"
        mutant["test_output"] = "Patch failed to apply"
        return mutant, last_run_end

    code, output = run_cmd(test_command, timeout=timeout)
    run_end = time.time()

    wait_for_next_second(run_end)
    revert_ok = revert_patch(patch_path, backup)
    if not revert_ok:
        print(f"  WARNING: Failed to revert patch for mutant {mutant_id}", file=sys.stderr)

    if code == -1:
        status = "timeout"
        symbol = "✓ (timeout)"
    elif code != 0:
        status = "killed"
        symbol = "✓"
    else:
        status = "survived"
        symbol = "✗"

    print(f"  Mutant {mutant_id}: {label} ... {status} {symbol}")
    mutant["status"] = status
    mutant["test_output"] = last_n_lines(output)
    return mutant, run_end


def main():
    parser = argparse.ArgumentParser(description="MutantX deterministic test runner")
    parser.add_argument(
        "--mutants-dir",
        type=Path,
        default=Path(".mutants"),
        help="Path to the mutants directory (default: .mutants)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Test command timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip the baseline test run",
    )
    parser.add_argument(
        "--no-clean-check",
        action="store_true",
        help="Skip the clean-tree check on the files to be mutated",
    )
    parser.add_argument(
        "--strict-clean",
        action="store_true",
        help="Require the whole working tree to be clean, not just the mutated files",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip the pre-test mutation validation step",
    )
    parser.add_argument(
        "--skip-final-check",
        action="store_true",
        help="Skip re-running the tests on unmutated code after the last mutant",
    )
    args = parser.parse_args()

    manifest_path = args.mutants_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found. Run /mx-generate first.", file=sys.stderr)
        sys.exit(1)

    # Run validation before testing
    if not args.skip_validation:
        validate_script = find_sibling_script("mx-validate.py")
        if validate_script:
            print("Validating mutants against current source files...")
            code, output = run_cmd(
                f"python3 {validate_script} --mutants-dir {args.mutants_dir}",
                timeout=60,
            )
            print(output)
            print()

            # Re-read manifest after validation may have changed statuses
            with open(manifest_path) as f:
                manifest = json.load(f)

            needs_review = sum(
                1 for m in manifest.get("mutants", [])
                if m.get("status") == "needs-review"
            )
            if needs_review > 0:
                print(
                    f"WARNING: {needs_review} mutants need AI review (file changed but patch applies).",
                    file=sys.stderr,
                )
                print("  These will be skipped. To include them:", file=sys.stderr)
                print("    - Run /mx-validate in Claude Code (AI review)", file=sys.stderr)
                print("    - Or: python3 mx-validate.py --promote (trust patches)", file=sys.stderr)
                print()
        else:
            print("Note: mx-validate.py not found, skipping validation.", file=sys.stderr)

    with open(manifest_path) as f:
        manifest = json.load(f)

    test_command = manifest.get("config", {}).get("test_command")
    if not test_command:
        detect_path = args.mutants_dir / "detect.json"
        if detect_path.exists():
            with open(detect_path) as f:
                detect = json.load(f)
            test_command = detect.get("test_command")

    if not test_command:
        print("ERROR: No test command found in manifest or detect.json.", file=sys.stderr)
        sys.exit(1)

    # Find pending mutants before any pre-flight work: with nothing to test,
    # the clean-tree check guards nothing and the baseline is wasted effort.
    mutants = manifest.get("mutants", [])
    pending = [(i, m) for i, m in enumerate(mutants) if m.get("status") == "pending"]

    if not pending:
        print("No pending mutants to test.")
        sys.exit(0)

    # Pre-flight checks
    if not args.no_clean_check:
        scope = None if args.strict_clean else sorted(
            {m["file"] for _, m in pending if m.get("file")}
        )
        if not check_clean_tree(scope):
            print("Aborting. Use --no-clean-check to skip this check.", file=sys.stderr)
            sys.exit(1)

    if not args.skip_baseline:
        passed, baseline_duration = run_baseline(test_command, args.timeout)
        if not passed:
            print("ERROR: Baseline tests are failing. Fix your tests before running mutation testing.", file=sys.stderr)
            sys.exit(1)
        effective_timeout = max(args.timeout, int(baseline_duration * 3))
    else:
        effective_timeout = args.timeout
    last_run_end = time.time()

    total = len(mutants)
    tested_before = total - len(pending)
    print(f"\nTesting {len(pending)} mutants ({tested_before} already tested, {total} total)\n")

    killed = survived = timeout = skipped = 0

    for seq, (idx, mutant) in enumerate(pending, 1):
        print(f"[{tested_before + seq}/{total}]", end="")
        updated, last_run_end = test_mutant(
            mutant, args.mutants_dir, test_command, effective_timeout, last_run_end
        )
        mutants[idx] = updated

        match updated["status"]:
            case "killed": killed += 1
            case "survived": survived += 1
            case "timeout": timeout += 1
            case "skipped": skipped += 1

        # Save progress after each mutant
        manifest["mutants"] = mutants
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    # All patches are reverted, so the suite must pass again. If it does not,
    # a revert failed or the build reused mutated artifacts, and every result
    # from this run is suspect.
    if not args.skip_final_check:
        print("\nRe-running tests on unmutated code...")
        wait_for_next_second(last_run_end)
        code, output = run_cmd(test_command, timeout=effective_timeout)
        if code != 0:
            print("ERROR: Tests fail on unmutated code after the run.", file=sys.stderr)
            print(last_n_lines(output, 10), file=sys.stderr)
            print(
                "  A patch may not have been reverted, or the build reused mutated "
                "objects.\n  Check `git status`, then reset tested mutants to "
                "pending and re-run with a test command that forces a rebuild.",
                file=sys.stderr,
            )
            sys.exit(1)
        print("  Unmutated code still passes.")

    # Count totals including previously tested
    total_killed = sum(1 for m in mutants if m["status"] == "killed")
    total_survived = sum(1 for m in mutants if m["status"] == "survived")
    total_timeout = sum(1 for m in mutants if m["status"] == "timeout")
    total_skipped = sum(1 for m in mutants if m["status"] == "skipped")

    print(f"\n{'='*50}")
    print(f"Testing complete!")
    print(f"  Killed:   {total_killed}")
    print(f"  Survived: {total_survived}")
    print(f"  Timeout:  {total_timeout}")
    print(f"  Skipped:  {total_skipped}")

    testable = total_killed + total_survived + total_timeout
    if testable > 0:
        score = (total_killed + total_timeout) / testable
        print(f"  Score:    {score:.0%} ({total_killed + total_timeout}/{testable})")
    print(f"\nRun mx-report.py to generate the full report.")


if __name__ == "__main__":
    main()
