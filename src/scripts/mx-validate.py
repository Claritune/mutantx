#!/usr/bin/env python3
"""MutantX deterministic mutation validator.

Checks whether generated mutants are still valid against the current state
of the source files. Three possible outcomes per mutant:

  - valid:        file unchanged, patch applies — ready to test
  - stale:        patch no longer applies cleanly — needs regeneration
  - needs-review: file changed but patch still applies — semantically
                  ambiguous, flag for AI review via /mx-validate

It also fingerprints the test suite (test files + test command). Cached
killed/survived results were measured against that suite, so when it changes
every tested mutant is reset to pending and re-tested.

Usage:
    python mx-validate.py [--mutants-dir .mutants]
    python mx-validate.py --promote          # trust patches, skip AI review
    python mx-validate.py --retest           # re-test all cached results
    python mx-validate.py --json             # machine-readable output
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


TESTED_STATUSES = ("killed", "killed-crash", "killed-build", "survived", "timeout")

# Fallback when detect.json has no `test_patterns`: common test file and
# directory names across languages.
TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs)/"
    r"|(^|/)test_[^/]*$"
    r"|_test\.[^/]+$"
    r"|\.(test|spec)\.[^/]+$"
    r"|(Test|Tests|_spec)\.[^/.]+$"
)
# Build and cache output that lands in test directories without being
# gitignored. It changes on every run and must not count as a test change.
ARTIFACT_RE = re.compile(
    r"(^|/)(__pycache__|\.pytest_cache|node_modules|build|dist|target|cmake-build[^/]*)/"
    r"|\.(pyc|pyo|o|obj|class|so|dylib|dll|a|exe)$"
)


def find_test_files(mutants_dir: Path) -> list[str]:
    """Test files from detect.json `test_patterns`, else by naming convention."""
    detect_path = mutants_dir / "detect.json"
    patterns = []
    if detect_path.exists():
        with open(detect_path) as f:
            patterns = json.load(f).get("test_patterns") or []
    if patterns:
        found = {str(p) for pat in patterns for p in Path(".").glob(pat) if p.is_file()}
        return sorted(found)

    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return []
    return sorted(
        f for f in result.stdout.splitlines()
        if TEST_PATH_RE.search(f)
        and not ARTIFACT_RE.search(f)
        and not f.startswith(".mutants/")
        and Path(f).is_file()
    )


def tests_fingerprint(test_files: list[str], test_command: str) -> str:
    h = hashlib.sha256(test_command.encode())
    for f in test_files:
        h.update(f"\0{f}\0{sha256_file(Path(f))}".encode())
    return h.hexdigest()


def resolve_test_command(manifest: dict, mutants_dir: Path) -> str:
    cmd = manifest.get("config", {}).get("test_command")
    detect_path = mutants_dir / "detect.json"
    if not cmd and detect_path.exists():
        with open(detect_path) as f:
            cmd = json.load(f).get("test_command")
    return cmd or ""


def patch_applies(patch_path: Path) -> bool:
    result = subprocess.run(
        ["git", "apply", "--check", str(patch_path)],
        capture_output=True,
        timeout=30,
    )
    return result.returncode == 0


def load_manifest(mutants_dir: Path) -> dict:
    manifest_path = mutants_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found.", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path) as f:
        return json.load(f)


def save_manifest(manifest: dict, mutants_dir: Path):
    manifest_path = mutants_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def validate(mutants_dir: Path, retest: bool = False) -> dict:
    """Validate all mutants. Returns a summary dict."""
    manifest = load_manifest(mutants_dir)
    stored_hashes = manifest.get("file_hashes", {})
    mutants = manifest.get("mutants", [])

    # Re-test cached results if the test suite changed since they were recorded
    test_files = find_test_files(mutants_dir)
    current_tests = tests_fingerprint(test_files, resolve_test_command(manifest, mutants_dir))
    stored_tests = manifest.get("tests_hash")
    tested = [m for m in mutants if m.get("status") in TESTED_STATUSES]
    retest_reason = None
    if retest:
        retest_reason = "--retest requested"
    elif stored_tests and stored_tests != current_tests:
        retest_reason = "tests changed since last run"
    if retest_reason:
        for m in tested:
            m["status"] = "pending"
            m["validation_note"] = f"Re-testing: {retest_reason}"
    manifest["tests_hash"] = current_tests

    # Classify files
    referenced_files = {m["file"] for m in mutants if m.get("file")}
    current_hashes: dict[str, str] = {}
    deleted_files: set[str] = set()
    changed_files: set[str] = set()
    unchanged_files: set[str] = set()

    for filepath in referenced_files:
        p = Path(filepath)
        if not p.exists():
            deleted_files.add(filepath)
            continue
        current_hash = sha256_file(p)
        current_hashes[filepath] = current_hash
        if stored_hashes.get(filepath) == current_hash:
            unchanged_files.add(filepath)
        else:
            changed_files.add(filepath)

    # Validate each mutant
    counts = {"valid": 0, "stale": 0, "needs_review": 0, "skipped": 0}
    already_tested = 0

    for m in mutants:
        if m.get("status") in TESTED_STATUSES:
            already_tested += 1
            continue
        if m.get("status") in ("stale", "skipped"):
            counts["skipped"] += 1
            continue

        filepath = m.get("file", "")
        patch_path = mutants_dir / m.get("patch_file", "")

        if filepath in deleted_files:
            m["status"] = "stale"
            m["validation_note"] = "Source file deleted"
            counts["stale"] += 1
            continue

        if not patch_path.exists():
            m["status"] = "stale"
            m["validation_note"] = "Patch file missing"
            counts["stale"] += 1
            continue

        applies = patch_applies(patch_path)

        if filepath in unchanged_files:
            if applies:
                m["status"] = "pending"
                counts["valid"] += 1
            else:
                m["status"] = "stale"
                m["validation_note"] = "Patch no longer applies despite file unchanged"
                counts["stale"] += 1
        elif filepath in changed_files:
            if applies:
                m["status"] = "needs-review"
                m["validation_note"] = (
                    f"File changed (hash mismatch) but patch applies cleanly. "
                    f"Stored: {stored_hashes.get(filepath, 'none')[:12]}... "
                    f"Current: {current_hashes.get(filepath, 'none')[:12]}..."
                )
                counts["needs_review"] += 1
            else:
                m["status"] = "stale"
                m["validation_note"] = "File changed and patch no longer applies"
                counts["stale"] += 1

    manifest["mutants"] = mutants
    save_manifest(manifest, mutants_dir)

    return {
        "retest_reason": retest_reason,
        "retested": len(tested) if retest_reason else 0,
        "untracked_results": len(tested) if not stored_tests and not retest_reason else 0,
        "test_files": len(test_files),
        "total_mutants": len(mutants),
        "already_tested": already_tested,
        "valid": counts["valid"],
        "stale": counts["stale"],
        "needs_review": counts["needs_review"],
        "previously_skipped": counts["skipped"],
        "unchanged_files": len(unchanged_files),
        "changed_files": sorted(changed_files),
        "deleted_files": sorted(deleted_files),
    }


def promote(mutants_dir: Path):
    """Promote needs-review mutants to pending (trust the patches)."""
    manifest = load_manifest(mutants_dir)

    promoted = 0
    for m in manifest.get("mutants", []):
        if m.get("status") == "needs-review":
            m["status"] = "pending"
            m["validation_note"] = "Promoted without AI review"
            promoted += 1

    # Update file hashes to current values so future validations are clean
    for m in manifest.get("mutants", []):
        filepath = m.get("file", "")
        if filepath and Path(filepath).exists():
            manifest.setdefault("file_hashes", {})[filepath] = sha256_file(Path(filepath))

    save_manifest(manifest, mutants_dir)
    print(f"Promoted {promoted} mutants from needs-review to pending.")


def print_report(result: dict):
    print(f"Validation complete ({result['total_mutants']} mutants)\n")

    if result["retest_reason"]:
        print(
            f"  {result['retest_reason'].capitalize()}: "
            f"re-testing {result['retested']} cached mutants."
        )
    elif result["untracked_results"]:
        print(
            f"  Recorded the test-suite fingerprint ({result['test_files']} test files) for "
            f"the first time.\n  {result['untracked_results']} cached results predate it; "
            f"use --retest to re-verify them."
        )
    if result["test_files"] == 0:
        print(
            "  WARNING: no test files found, so test changes cannot invalidate cached "
            "results.\n  Add `test_patterns` to .mutants/detect.json."
        )

    if result["already_tested"]:
        print(f"  Already tested:     {result['already_tested']}")
    print(f"  Valid (ready):      {result['valid']}")

    if result["needs_review"]:
        print(f"  Needs AI review:    {result['needs_review']}")
        print(f"    Changed files: {', '.join(result['changed_files'])}")

    if result["stale"]:
        print(f"  Stale (need regen): {result['stale']}")
        if result["deleted_files"]:
            print(f"    Deleted files: {', '.join(result['deleted_files'])}")

    if result["previously_skipped"]:
        print(f"  Previously skipped: {result['previously_skipped']}")

    print()

    if result["needs_review"] > 0:
        print(f"{result['needs_review']} mutants need review:")
        print("  1. /mx-validate      — AI reviews semantic validity (recommended)")
        print("  2. mx-validate.py --promote — trust patches, test as-is")
        print("  3. /mx-generate regen=\"true\" — regenerate everything")
    elif result["stale"] > 0:
        print(f"{result['stale']} stale mutants. Run /mx-generate to regenerate.")
    elif result["valid"] > 0:
        print("All mutants valid. Ready to test.")
    else:
        print("No pending mutants.")


def main():
    parser = argparse.ArgumentParser(description="MutantX mutation validator")
    parser.add_argument(
        "--mutants-dir", type=Path, default=Path(".mutants"),
        help="Path to the mutants directory (default: .mutants)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--promote", action="store_true",
        help="Promote needs-review mutants to pending without AI review",
    )
    parser.add_argument(
        "--retest", action="store_true",
        help="Reset all tested mutants to pending so they are re-tested",
    )
    args = parser.parse_args()

    if args.promote:
        promote(args.mutants_dir)
    else:
        result = validate(args.mutants_dir, retest=args.retest)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_report(result)


if __name__ == "__main__":
    main()
